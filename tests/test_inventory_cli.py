"""Controller-facing inventory commands preserve full accounting under bounded display."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InventoryCliTests(unittest.TestCase):
    def _run(self, *args: object) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
               "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run([sys.executable, "-m", "repository_intelligence.inventory",
                               *map(str, args)], text=True, capture_output=True, env=env,
                              timeout=30)

    def test_stable_json_and_bounded_compact_delta(self):
        with tempfile.TemporaryDirectory() as raw:
            planning, candidate = (Path(raw) / name for name in ("planning", "candidate"))
            planning.mkdir()
            candidate.mkdir()
            (planning / "main.py").write_text("def same(): return 1\ndef changed(): return 1\n")
            (candidate / "main.py").write_text("def same(): return 1\ndef changed(): return 2\n")
            (planning / "removed.rs").write_text("fn removed() {}\n")
            (candidate / "added.rs").write_text("fn added() {}\n")
            command = ("compare", planning, candidate, "--logical-root", "example",
                       "--assert-stable-materialization", "--limit", "1")
            compact = self._run(*command)
            self.assertEqual(compact.returncode, 0, compact.stderr)
            self.assertIn("comparison comparable_candidate_delta", compact.stdout)
            self.assertIn("schema=7 navigation_schema=2", compact.stdout)
            self.assertIn("logical_root=example extensions=.c,.cc,.cjs,.cpp,.cs,.cxx,.go,.hh,.hpp,.hxx,.java,.js,.jsx,.mjs,.py,.rs,.ts,.tsx",
                          compact.stdout)
            self.assertIn("files: added=1 removed=1 modified=1 unchanged=0", compact.stdout)
            self.assertIn("... 2 more files changes; use --json", compact.stdout)
            self.assertIn("RI does not attest", compact.stderr)
            full = self._run(*command, "--json")
            self.assertEqual(full.returncode, 0, full.stderr)
            delta = json.loads(full.stdout)
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual(delta["planning"]["scope"]["logical_root"], "example")
            self.assertEqual(delta["planning"]["inventory_schema_version"], 7)
            self.assertEqual(delta["planning"]["mapping_contract"],
                             delta["candidate"]["mapping_contract"])
            self.assertEqual(len(delta["file_changes"]["added"]), 1)
            self.assertEqual(len(delta["file_changes"]["removed"]), 1)
            self.assertEqual(len(delta["file_changes"]["modified"]), 1)
            self.assertEqual(len(delta["declaration_changes"]["modified"]), 1)
            scan = self._run("scan", planning, "--logical-root", "example",
                             "--assert-stable-materialization", "--json")
            self.assertEqual(scan.returncode, 0, scan.stderr)
            inventory = json.loads(scan.stdout)
            self.assertEqual(inventory["inventory_schema_version"], 7)
            self.assertEqual(inventory["scope"]["logical_root"], "example")

    def test_non_atomic_incomplete_and_incompatible_have_no_delta(self):
        with tempfile.TemporaryDirectory() as raw:
            planning, candidate = (Path(raw) / name for name in ("planning", "candidate"))
            planning.mkdir()
            candidate.mkdir()
            (planning / "main.py").write_text("def f(): return 1\n")
            (candidate / "main.py").write_text("def f(): return 2\n")
            live = self._run("compare", planning, candidate, "--json")
            self.assertEqual(live.returncode, 2)
            self.assertIsNone(json.loads(live.stdout)["declaration_changes"])
            (candidate / "main.py").write_text("def broken(:\n")
            broken = self._run("compare", planning, candidate,
                               "--assert-stable-materialization", "--json")
            self.assertEqual(broken.returncode, 2)
            self.assertIsNone(json.loads(broken.stdout)["declaration_changes"])
            (candidate / "main.py").write_text("def f(): return 2\n")
            (candidate / ".hidden").mkdir()
            scope = self._run("compare", planning, candidate,
                              "--assert-stable-materialization", "--json")
            self.assertEqual(scope.returncode, 3)
            result = json.loads(scope.stdout)
            self.assertEqual(result["status"], "incompatible")
            self.assertIn("scope", result["mismatches"])
            self.assertIsNone(result["file_changes"])

    def test_two_materialized_ri_source_snapshots_with_real_code_edit(self):
        sources = Path(__file__).resolve().parents[1] / "src" / "repository_intelligence"
        with tempfile.TemporaryDirectory() as raw:
            planning, candidate = (Path(raw) / name for name in ("planning", "candidate"))
            planning.mkdir()
            candidate.mkdir()
            for name in ("source.py", "declarations.py"):
                shutil.copy2(sources / name, planning / name)
                shutil.copy2(sources / name, candidate / name)
            edited = candidate / "source.py"
            original = edited.read_text()
            self.assertIn("    return lines\n", original)
            edited.write_text(original.replace("    return lines\n", "    return list(lines)\n", 1))
            result = self._run("compare", planning, candidate,
                               "--logical-root", "repository-intelligence",
                               "--assert-stable-materialization", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            delta = json.loads(result.stdout)
            self.assertEqual(delta["planning"]["scope"]["logical_root"],
                             "repository-intelligence")
            self.assertEqual(delta["planning"]["scope"], delta["candidate"]["scope"])
            self.assertEqual([item["path"] for item in delta["file_changes"]["modified"]],
                             ["source.py"])
            self.assertEqual([item["path"] for item in delta["file_changes"]["unchanged"]],
                             ["declarations.py"])
            self.assertEqual([item["declaration_id"] for item in
                              delta["declaration_changes"]["modified"]],
                             ["function:physical_lines#0"])


if __name__ == "__main__":
    unittest.main()
