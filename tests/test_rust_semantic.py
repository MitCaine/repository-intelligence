"""One optional rust-analyzer definition question, separate from structural scans."""

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repository_intelligence import rust_semantic
from repository_intelligence.rust_semantic import resolve_definition


class RustSemanticTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("rust-analyzer") and shutil.which("rustc"),
                         "rust-analyzer and rustc required for optional semantic proof")
    def test_reference_definition_is_source_and_configuration_bound(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-") as raw:
            root = Path(raw)
            (root / "src").mkdir()
            (root / "Cargo.toml").write_text(
                '[package]\nname = "ri_semantic_fixture"\nversion = "0.1.0"\nedition = "2021"\n')
            source = "fn target() -> i32 { 1 }\nfn caller() -> i32 { let _ = \"😀\"; target() }\n".encode()
            path = root / "src/lib.rs"
            path.write_bytes(source)
            target = next(line.split(": ", 1)[1] for line in
                          subprocess.check_output(["rustc", "-vV"], text=True).splitlines()
                          if line.startswith("host: "))
            result = resolve_definition(root, path, 2,
                                        source.decode().splitlines()[1].index("target") + 1,
                                        features=(), no_default_features=False, target=target,
                                        timeout=60)
            self.assertEqual(result["status"], "resolved")
            self.assertEqual(result["result_kind"], "rust_semantic_definition_v1")
            self.assertEqual(result["reference"]["raw_sha256"], hashlib.sha256(source).hexdigest())
            self.assertEqual(result["configuration"]["cargo"]["target"], target)
            self.assertEqual(result["provider_status"]["health"], "ok")
            self.assertEqual(result["targets"][0]["range"]["start"]["line"], 0)
            self.assertEqual(result["targets"][0]["source_identity"]["raw_sha256"],
                             hashlib.sha256(source).hexdigest())
            self.assertEqual(result["targets"][0]["byte_binding"],
                             "checked_against_final_local_snapshot")
            self.assertEqual(result["source_snapshot"]["file_count"], 2)

    def test_unicode_separator_is_not_a_physical_line_boundary(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-") as raw:
            root = Path(raw)
            (root / "Cargo.toml").write_text('[package]\nname="x"\nversion="0.1.0"\n')
            path = root / "lib.rs"
            source = 'fn target() {}\nfn caller() { let _ = "a\u2028b"; target(); }\n'
            path.write_text(source)
            column = source.split("\n")[1].index("target") + 1
            with self.assertRaisesRegex(ValueError, "Explicit Cargo"):
                resolve_definition(root, path, 2, column, features=(),
                                   no_default_features=False, target="")
            # The same position with explicit settings must reach the provider;
            # a Unicode separator inside the string does not add an LSP line.
            class ProviderReached(Exception):
                pass

            with patch.object(rust_semantic.subprocess, "run", side_effect=ProviderReached):
                with self.assertRaises(ProviderReached):
                    resolve_definition(root, path, 2, column, features=(),
                                       no_default_features=False, target="test-target")

    def test_mutated_local_target_is_not_verified_as_analyzed_bytes(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-") as raw:
            root = Path(raw)
            (root / "Cargo.toml").write_text('[package]\nname="x"\nversion="0.1.0"\n')
            path = root / "lib.rs"
            original = b"fn target() {}\nfn caller() { target(); }\n"
            path.write_bytes(original)
            snapshot = rust_semantic._snapshot
            calls = 0

            def changing_snapshot(project):
                nonlocal calls
                calls += 1
                if calls == 2:
                    path.write_bytes(b"fn target() { changed(); }\nfn caller() { target(); }\n")
                return snapshot(project)

            class FakeAnalyzer:
                def __init__(self, *args):
                    self.last_status = {"health": "ok", "quiescent": True}

                def request(self, request_id, method, params):
                    if method == "textDocument/definition":
                        return {"uri": path.as_uri(), "range": {
                            "start": {"line": 0, "character": 3},
                            "end": {"line": 0, "character": 9}}}
                    return {}

                def send(self, message):
                    pass

                def wait_ready(self):
                    pass

                def close(self):
                    pass

            with patch.object(rust_semantic, "_RustAnalyzer", FakeAnalyzer), \
                    patch.object(rust_semantic, "_snapshot", side_effect=changing_snapshot), \
                    patch.object(rust_semantic.subprocess, "run") as version:
                version.return_value.stdout = "rust-analyzer test"
                result = resolve_definition(root, path, 2, 16, features=(),
                                            no_default_features=False, target="test-target")
            self.assertEqual(result["status"], "incomplete_changed_source")
            self.assertEqual(result["targets"][0]["source_identity"]["raw_sha256"],
                             hashlib.sha256(original).hexdigest())
            self.assertEqual(result["targets"][0]["byte_binding"],
                             "post_analysis_observation")

    def test_excluded_local_target_is_not_bound_to_snapshot(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-") as raw:
            root = Path(raw)
            (root / "Cargo.toml").write_text('[package]\nname="x"\nversion="0.1.0"\n')
            source = root / "lib.rs"
            source.write_text("fn caller() { target(); }\n")
            generated = root / "target/generated.rs"
            generated.parent.mkdir()
            generated.write_text("fn target() {}\n")

            class FakeAnalyzer:
                def __init__(self, *args):
                    self.last_status = {"health": "ok", "quiescent": True}

                def request(self, request_id, method, params):
                    if method == "textDocument/definition":
                        return {"uri": generated.resolve().as_uri(), "range": {
                            "start": {"line": 0, "character": 3},
                            "end": {"line": 0, "character": 9}}}
                    return {}

                def send(self, message):
                    pass

                def wait_ready(self):
                    pass

                def close(self):
                    pass

            with patch.object(rust_semantic, "_RustAnalyzer", FakeAnalyzer), \
                    patch.object(rust_semantic.subprocess, "run") as version:
                version.return_value.stdout = "rust-analyzer test"
                result = resolve_definition(root, source, 1, 15, features=(),
                                            no_default_features=False, target="test-target")
            self.assertEqual(result["status"], "resolved")
            self.assertTrue(result["targets"][0]["source_identity"]["within_project"])
            self.assertEqual(result["targets"][0]["byte_binding"],
                             "post_analysis_observation")

    def test_missing_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-") as raw:
            root = Path(raw)
            (root / "Cargo.toml").write_text('[package]\nname="x"\nversion="0.1.0"\n')
            path = root / "lib.rs"
            path.write_text("fn f(){}\n")
            with self.assertRaisesRegex(ValueError, "Explicit Cargo"):
                resolve_definition(root, path, 1, 1, features=(),
                                   no_default_features=False, target="")


if __name__ == "__main__":
    unittest.main()
