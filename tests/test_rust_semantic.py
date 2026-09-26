"""One optional rust-analyzer definition question, separate from structural scans."""

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repository_intelligence import rust_semantic
from repository_intelligence.rust_semantic import resolve_definition


class RustSemanticTests(unittest.TestCase):
    def test_snapshot_propagates_directory_traversal_error(self):
        def inaccessible(root, *, followlinks=False, onerror=None):
            if onerror is not None:
                onerror(PermissionError("unreadable Rust directory"))
            return
            yield

        with tempfile.TemporaryDirectory() as raw, \
                patch.object(rust_semantic.os, "walk", side_effect=inaccessible):
            with self.assertRaises(PermissionError):
                rust_semantic._snapshot(Path(raw))

    def test_unreadable_external_target_preserves_location(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "project"
            root.mkdir()
            (root / "Cargo.toml").write_text('[package]\nname="x"\nversion="0.1.0"\n')
            source = root / "lib.rs"
            source.write_text("fn caller() { target(); }\n")
            target = Path(raw) / "external.rs"
            target.write_text("fn target() {}\n")

            class FakeAnalyzer:
                def __init__(self, *args):
                    self.last_status = {"health": "ok", "quiescent": True}

                def request(self, request_id, method, params):
                    if method == "textDocument/definition":
                        return {"uri": target.as_uri(), "range": {
                            "start": {"line": 0, "character": 3},
                            "end": {"line": 0, "character": 9}}}
                    return {}

                def send(self, message):
                    pass

                def wait_ready(self):
                    pass

                def close(self):
                    pass

            original_read = Path.read_bytes

            def read_or_fail(path):
                if path == target:
                    raise PermissionError("external target unreadable")
                return original_read(path)

            with patch.object(rust_semantic, "_RustAnalyzer", FakeAnalyzer), \
                    patch.object(rust_semantic.subprocess, "run") as version, \
                    patch.object(Path, "read_bytes", read_or_fail):
                version.return_value.stdout = "rust-analyzer test"
                result = resolve_definition(root, source, 1, 15, features=(),
                                            no_default_features=False, target="test-target")
            self.assertEqual(result["status"], "resolved")
            self.assertEqual(result["targets"][0]["uri"], target.as_uri())
            self.assertIsNone(result["targets"][0]["source_identity"])
            self.assertEqual(result["targets"][0]["source_identity_error"],
                             "PermissionError")
            self.assertEqual(result["targets"][0]["byte_binding"],
                             "post_analysis_observation")

    def test_provider_send_obeys_deadline_when_pipe_stalls(self):
        script = """\
import os, time
from types import SimpleNamespace
from repository_intelligence.rust_semantic import _RustAnalyzer
read_end, write_end = os.pipe()
os.set_blocking(write_end, False)
try:
    while True:
        os.write(write_end, b'x' * 4096)
except BlockingIOError:
    pass
os.set_blocking(write_end, True)
client = _RustAnalyzer.__new__(_RustAnalyzer)
client.proc = SimpleNamespace(stdin=os.fdopen(write_end, 'wb', buffering=0))
client.deadline = time.monotonic() + 0.05
try:
    client.send({'payload': 'test'})
except TimeoutError:
    print('deadline_observed')
finally:
    os.close(read_end)
"""
        completed = subprocess.run([sys.executable, "-c", script],
                                   capture_output=True, text=True, timeout=1)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "deadline_observed")

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
            self.assertEqual(result["result_kind"], "rust_semantic_definition_v2")
            self.assertEqual(result["reference"]["raw_sha256"], hashlib.sha256(source).hexdigest())
            self.assertEqual(result["configuration"]["cargo"]["target"], target)
            self.assertEqual(result["provider_status"]["health"], "ok")
            self.assertEqual(result["targets"][0]["range"]["start"]["line"], 0)
            self.assertEqual(result["targets"][0]["source_identity"]["raw_sha256"],
                             hashlib.sha256(source).hexdigest())
            self.assertEqual(result["targets"][0]["byte_binding"],
                             "checked_against_final_local_snapshot")
            self.assertEqual(result["source_snapshot"]["file_count"], 2)

    @unittest.skipUnless(shutil.which("rust-analyzer") and shutil.which("rustc"),
                         "rust-analyzer and rustc required for optional semantic proof")
    def test_definition_selects_explicit_normal_or_test_configuration(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-cfg-") as raw:
            root = Path(raw)
            (root / "src").mkdir()
            (root / "Cargo.toml").write_text(
                '[package]\nname="ri_cfg_fixture"\nversion="0.1.0"\nedition="2021"\n')
            path = root / "src/lib.rs"
            path.write_text(
                "#[cfg(test)]\nfn target() -> i32 { 1 }\n"
                "#[cfg(not(test))]\nfn target() -> i32 { 2 }\n"
                "fn caller() -> i32 { target() }\n")
            target = next(line.split(": ", 1)[1] for line in
                          subprocess.check_output(["rustc", "-vV"], text=True).splitlines()
                          if line.startswith("host: "))
            for test_mode, expected_line in ((False, 3), (True, 1)):
                with self.subTest(test_mode=test_mode):
                    result = resolve_definition(
                        root, path, 5, 24, features=(), no_default_features=False,
                        target=target, test_mode=test_mode, timeout=60)
                    self.assertEqual(result["status"], "resolved")
                    self.assertEqual(result["configuration"]["cfg"],
                                     {"setTest": test_mode})
                    self.assertEqual([item["range"] for item in result["targets"]],
                                     [{"start": {"line": expected_line, "character": 3},
                                       "end": {"line": expected_line, "character": 9}}])
                    self.assertEqual(result["targets"][0]["byte_binding"],
                                     "checked_against_final_local_snapshot")

    @unittest.skipUnless(shutil.which("rust-analyzer") and shutil.which("rustc"),
                         "rust-analyzer and rustc required for optional semantic proof")
    def test_definition_does_not_inject_miri_configuration(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-miri-") as raw:
            root = Path(raw)
            (root / "src").mkdir()
            (root / "Cargo.toml").write_text(
                '[package]\nname="ri_miri_fixture"\nversion="0.1.0"\nedition="2021"\n')
            path = root / "src/lib.rs"
            path.write_text(
                "#[cfg(miri)]\nfn target() -> i32 { 1 }\n"
                "#[cfg(not(miri))]\nfn target() -> i32 { 2 }\n"
                "fn caller() -> i32 { target() }\n")
            target = next(line.split(": ", 1)[1] for line in
                          subprocess.check_output(["rustc", "-vV"], text=True).splitlines()
                          if line.startswith("host: "))
            result = resolve_definition(root, path, 5, 24, features=(),
                                        no_default_features=False, target=target, timeout=60)
            self.assertEqual(result["status"], "resolved")
            self.assertEqual([item["range"] for item in result["targets"]],
                             [{"start": {"line": 3, "character": 3},
                               "end": {"line": 3, "character": 9}}])
            self.assertEqual(result["configuration"]["cargo"]["cfgs"], [])
            self.assertEqual(result["configuration"]["cfg"], {"setTest": False})

    @unittest.skipUnless(shutil.which("rust-analyzer") and shutil.which("rustc"),
                         "rust-analyzer and rustc required for optional semantic proof")
    def test_definition_uses_rust_lf_lines_and_counts_lone_cr_as_whitespace(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-newlines-") as raw:
            root = Path(raw)
            (root / "src").mkdir()
            (root / "Cargo.toml").write_text(
                '[package]\nname="ri_newline_fixture"\nversion="0.1.0"\nedition="2021"\n')
            path = root / "src/lib.rs"
            target = next(line.split(": ", 1)[1] for line in
                          subprocess.check_output(["rustc", "-vV"], text=True).splitlines()
                          if line.startswith("host: "))
            for separator, line, column in ((b"\n", 2, 18), (b"\r\n", 2, 18),
                                             (b"\r", 1, 33)):
                with self.subTest(separator=separator):
                    path.write_bytes(b"fn target() {}" + separator +
                                     b"fn caller() { target(); }\n")
                    result = resolve_definition(root, path, line, column, features=(),
                                                no_default_features=False,
                                                target=target, timeout=60)
                    self.assertEqual(result["status"], "resolved")
                    self.assertEqual([item["range"] for item in result["targets"]],
                                     [{"start": {"line": 0, "character": 3},
                                       "end": {"line": 0, "character": 9}}])

    def test_native_position_bounds_exclude_crlf_but_include_empty_final_line(self):
        class ProviderReached(Exception):
            pass

        with tempfile.TemporaryDirectory(prefix="ri-semantic-bounds-") as raw:
            root = Path(raw)
            (root / "Cargo.toml").write_text('[package]\nname="x"\nversion="0.1.0"\n')
            path = root / "lib.rs"
            source = b"fn f() {}\r\n"
            valid = ((source, 1, 10), (source, 2, 1), (b"fn f() {}\r", 1, 11))
            for content, line, column in valid:
                with self.subTest(valid=(content, line, column)):
                    path.write_bytes(content)
                    with patch.object(rust_semantic.subprocess, "run",
                                      side_effect=ProviderReached):
                        with self.assertRaises(ProviderReached):
                            resolve_definition(root, path, line, column, features=(),
                                               no_default_features=False, target="test-target")
            path.write_bytes(source)
            for line, column in ((1, 11), (2, 2), (3, 1)):
                with self.subTest(invalid=(line, column)):
                    with self.assertRaisesRegex(ValueError, "outside source"):
                        resolve_definition(root, path, line, column, features=(),
                                           no_default_features=False, target="test-target")

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

    def test_location_links_preserve_all_targets_and_utf16_reference_position(self):
        with tempfile.TemporaryDirectory(prefix="ri-semantic-links-") as raw:
            root = Path(raw).resolve()
            (root / "Cargo.toml").write_text('[package]\nname="x"\nversion="0.1.0"\n')
            source = root / "lib.rs"
            source.write_text('fn caller() { let _ = "😀"; target(); }\n')
            target = root / "other file é.rs"
            target_bytes = b"fn first() {}\nfn second() {}\n"
            target.write_bytes(target_bytes)
            spans = [{"start": {"line": line, "character": 3},
                      "end": {"line": line, "character": end}}
                     for line, end in ((0, 8), (1, 9))]
            observed = []

            class FakeAnalyzer:
                def __init__(self, *args):
                    self.last_status = {"health": "ok", "quiescent": True}

                def request(self, request_id, method, params):
                    if method == "textDocument/definition":
                        observed.append(params["position"])
                        return [{"targetUri": target.as_uri(),
                                 "targetSelectionRange": span,
                                 "targetRange": {"start": {"line": index, "character": 0},
                                                 "end": {"line": index, "character": 13 + index}}}
                                for index, span in enumerate(spans)]
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
                result = resolve_definition(root, source, 1, 31, features=(),
                                            no_default_features=False, target="test-target")
            # One astral character before the reference adds a UTF-16 code unit.
            self.assertEqual(observed, [{"line": 0, "character": 31}])
            self.assertEqual([item["range"] for item in result["targets"]], spans)
            self.assertEqual([item["uri"] for item in result["targets"]],
                             [target.as_uri(), target.as_uri()])
            for item in result["targets"]:
                self.assertEqual(item["source_identity"]["raw_sha256"],
                                 hashlib.sha256(target_bytes).hexdigest())
                self.assertEqual(item["byte_binding"], "checked_against_final_local_snapshot")

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
