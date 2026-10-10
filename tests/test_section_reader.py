"""Public CLI coverage with independently expected committed Markdown slices."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from repository_intelligence.section_reader import read_sections


class SectionReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.source = ("preamble\n# Parent\nintro\n## Child\nchild é\n"
                       "```md\n# Fence\n```\n### Nested\nbody\n"
                       "## Sibling\nsibling\n\nNext\n====\ntail\n").encode()
        (self.repo / "notes.md").write_bytes(self.source)
        (self.repo / "folder").mkdir()
        (self.repo / "folder" / "child.md").write_text("# Child\n")
        (self.repo / "duplicates.md").write_text("# Same\none\n# Same\ntwo\n")
        (self.repo / "scopes.md").write_text("# Main\n> # Quoted\n> text\n\n- # Listed\n")
        os.symlink("notes.md", self.repo / "link.md")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.revision = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True)

    def request(self, headings, **extra):
        return {"repository": str(self.repo), "revision": self.revision,
                "selections": [{"path": "notes.md", "headings": headings}], **extra}

    def cli(self, request):
        path = self.root / "request.json"
        path.write_text(json.dumps(request))
        process = subprocess.run([sys.executable, "-m", "repository_intelligence.section_reader",
                                  "--request", str(path)], capture_output=True, text=True)
        return process.returncode, json.loads(process.stdout)

    def test_public_cli_nested_fence_setext_and_identity(self):
        code, packet = self.cli(self.request(["Child", "Next"]))
        self.assertEqual(code, 0)
        self.assertEqual(packet["schema_version"], 1)
        self.assertEqual(packet["status"], "complete")
        document = packet["documents"][0]
        expected = ["## Child\nchild é\n```md\n# Fence\n```\n### Nested\nbody\n", "Next\n====\ntail\n"]
        self.assertEqual([item["text"] for item in document["ranges"]], expected)
        for item, text in zip(document["ranges"], expected):
            span = item["byte_range"]
            self.assertEqual(self.source[span["start"]:span["end"]], text.encode())
        identity = document["identity"]
        self.assertEqual(identity["raw_sha256"], hashlib.sha256(self.source).hexdigest())
        self.assertEqual(identity["byte_count"], len(self.source))
        self.assertEqual(identity["git_blob"]["object_id"], self.git("rev-parse", f"{self.revision}:notes.md").strip())
        (self.repo / "notes.md").write_text("# Changed\n")
        self.assertEqual(self.cli(self.request(["Child", "Next"]))[1], packet)

    def test_overlap_and_repeated_requests_emit_once(self):
        request = self.request(["Parent", "Child", "Child"])
        request["selections"].append({"path": "notes.md", "headings": ["Nested"]})
        packet = read_sections(request)
        self.assertEqual(packet["status"], "complete")
        self.assertEqual(len(packet["documents"]), 1)
        document = packet["documents"][0]
        self.assertEqual(len(document["ranges"]), 1)
        self.assertEqual(document["ranges"][0]["text"], self.source.decode().split("preamble\n", 1)[1].split("Next\n", 1)[0])
        self.assertEqual([v["heading"] for v in document["selection_coverage"]], ["Parent", "Child", "Nested"])

    def test_missing_fenced_and_duplicate_headings_are_incomplete(self):
        for path, heading, reason in [("notes.md", "Missing", "missing_heading"),
                                      ("notes.md", "Fence", "missing_heading"),
                                      ("duplicates.md", "Same", "ambiguous_heading"),
                                      ("scopes.md", "Quoted", "missing_heading"),
                                      ("scopes.md", "Listed", "missing_heading")]:
            with self.subTest(path=path, heading=heading):
                request = self.request([heading])
                request["selections"][0]["path"] = path
                code, packet = self.cli(request)
                self.assertEqual(code, 1)
                document = packet["documents"][0]
                self.assertEqual(document["ranges"], [])
                self.assertEqual(document["selection_coverage"][0]["reason"], reason)

    def test_budget_never_certifies_partial_sections(self):
        for limit in [0, 2, len("## Child\nchild ".encode()) + 1]:
            with self.subTest(limit=limit):
                packet = read_sections(self.request(["Child", "Next"], max_output_bytes=limit))
                self.assertEqual(packet["status"], "incomplete")
                self.assertLessEqual(packet["emitted_bytes"], limit)
                document = packet["documents"][0]
                self.assertTrue(all(v["status"] == "incomplete" for v in document["selection_coverage"]))
                self.assertTrue(all(not v["complete"] for v in document["ranges"]))
                for item in document["ranges"]:
                    bounds = item["byte_range"]
                    self.assertEqual(item["text"].encode(), self.source[bounds["start"]:bounds["end"]])
        full = read_sections(self.request(["Child"]))
        exact = read_sections(self.request(["Child"], max_output_bytes=full["emitted_bytes"]))
        self.assertEqual(exact["status"], "complete")

    def test_invalid_paths_and_nonregular_sources(self):
        for path in ["../notes.md", "/notes.md", "./notes.md", "a/../notes.md", "a//b", "link.md", ".git/config", "missing.md", "notes.md/", "folder"]:
            with self.subTest(path=path):
                request = self.request(["Parent"])
                request["selections"][0]["path"] = path
                code, packet = self.cli(request)
                self.assertEqual(code, 1)
                self.assertEqual(packet["status"], "incomplete")
                self.assertTrue(packet["errors"] or packet["documents"][0]["errors"])

    def test_expected_identity_mismatch_and_exact_revision(self):
        request = self.request(["Parent"])
        request["selections"][0]["expected_sha256"] = "0" * 64
        packet = read_sections(request)
        self.assertEqual(packet["status"], "incomplete")
        self.assertEqual(packet["documents"][0]["ranges"], [])
        self.assertIn("sha256", packet["documents"][0]["errors"][0])
        request["selections"][0]["expected_sha256"] = hashlib.sha256(self.source).hexdigest()
        self.assertEqual(read_sections(request)["status"], "complete")
        for revision in ["HEAD", self.revision[:12], self.git("rev-parse", "HEAD:notes.md").strip()]:
            request["revision"] = revision
            self.assertEqual(read_sections(request)["status"], "incomplete")

    def test_explicit_repository_ignores_foreign_git_environment(self):
        foreign = self.root / "foreign"
        foreign.mkdir()
        subprocess.run(["git", "-C", str(foreign), "init", "-q"], check=True)
        with patch.dict(os.environ, {"GIT_DIR": str(foreign / ".git"),
                                     "GIT_WORK_TREE": str(foreign),
                                     "GIT_INDEX_FILE": str(foreign / ".git" / "index"),
                                     "GIT_COMMON_DIR": str(foreign / ".git"),
                                     "GIT_OBJECT_DIRECTORY": str(foreign / ".git" / "objects"),
                                     "GIT_NAMESPACE": "foreign"}):
            code, packet = self.cli(self.request(["Next"]))
        self.assertEqual(code, 0)
        self.assertEqual(packet["repository"], str(self.repo.resolve()))
        self.assertEqual(packet["documents"][0]["ranges"][0]["text"], "Next\n====\ntail\n")
        request = self.request(["Child"])
        request["repository"] = str(self.repo / "folder")
        code, packet = self.cli(request)
        self.assertEqual(code, 1)
        self.assertIn("exact Git repository root", packet["errors"][0])

    def test_resource_bounds_and_invalid_requests(self):
        for extra in [{"max_output_bytes": -1}, {"max_output_bytes": True},
                      {"max_output_bytes": 4_000_001}, {"selections": []}]:
            code, packet = self.cli(self.request(["Parent"], **extra))
            self.assertEqual(code, 1)
            self.assertEqual(packet["status"], "incomplete")
        (self.repo / "large.md").write_bytes(b"# Large\n" + b"a" * 4_000_000)
        self.git("add", "large.md")
        self.git("commit", "-qm", "large source")
        self.revision = self.git("rev-parse", "HEAD").strip()
        request = self.request(["Large"])
        request["selections"][0]["path"] = "large.md"
        packet = read_sections(request)
        self.assertEqual(packet["status"], "incomplete")
        self.assertIn("4 MB", packet["documents"][0]["errors"][0])
        self.assertEqual(packet["documents"][0]["ranges"], [])

    def test_crlf_lone_cr_and_invalid_utf8(self):
        for newline in ["\r\n", "\r"]:
            source = "One\n===\nbody\n\n## Two\nchild\n# End\nend\n".replace("\n", newline).encode()
            (self.repo / "notes.md").write_bytes(source)
            self.git("add", "notes.md")
            self.git("commit", "-qm", "line endings")
            self.revision = self.git("rev-parse", "HEAD").strip()
            packet = read_sections(self.request(["One"]))
            self.assertEqual(packet["status"], "complete")
            self.assertEqual(packet["documents"][0]["ranges"][0]["text"].encode(),
                             "One\n===\nbody\n\n## Two\nchild\n".replace("\n", newline).encode())
        (self.repo / "notes.md").write_bytes(b"# One\n\xff\n")
        self.git("add", "notes.md")
        self.git("commit", "-qm", "invalid utf8")
        self.revision = self.git("rev-parse", "HEAD").strip()
        self.assertEqual(read_sections(self.request(["One"]))["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
