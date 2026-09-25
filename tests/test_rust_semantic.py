"""One optional rust-analyzer definition question, separate from structural scans."""

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.rust_semantic import resolve_definition


@unittest.skipUnless(shutil.which("rust-analyzer") and shutil.which("rustc"),
                     "rust-analyzer and rustc required for optional semantic proof")
class RustSemanticTests(unittest.TestCase):
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
            self.assertEqual(result["source_snapshot"]["file_count"], 2)

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
