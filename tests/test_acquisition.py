"""Real local Git observations for source materialization authority."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from repository_intelligence.acquisition import GitSourceObserver, GitSourceObservation
from repository_intelligence.errors import ValidationError


class GitSourceObserverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "source"
        self.root.mkdir()
        self.git("init", "-q")
        (self.root / "source.txt").write_text("source\n", encoding="utf-8")
        self.git("add", "source.txt")
        self.git("-c", "user.name=Observer Test", "-c", "user.email=observer@example.invalid", "commit", "-qm", "initial")
        self.revision = self.git("rev-parse", "HEAD").stdout.strip()
        self.pin = {
            "source_id": "source-a",
            "repository": "example/source",
            "revision": self.revision,
            "language": "Rust",
            "source_state_mode": "immutable_committed",
            "configuration_id": "config-a",
        }

    def git(self, *args):
        return subprocess.run(
            ("git", "-C", str(self.root), *args),
            check=True, capture_output=True, text=True,
        )

    def test_observes_exact_clean_git_objects_and_rechecks(self):
        observer = GitSourceObserver(self.pin, self.root)
        observed = observer.observe()
        self.assertEqual(observer.require(observed)["revision"], self.revision)
        self.assertEqual(observer.require(observed)["tree_sha"], self.git("rev-parse", "HEAD^{tree}").stdout.strip())
        self.pin["revision"] = "0" * 40
        self.assertEqual(observer.require(observed)["revision"], self.revision)
        (self.root / "untracked.txt").write_text("not clean", encoding="utf-8")
        with self.assertRaises(ValidationError):
            observer.require(observed)

    def test_direct_copied_foreign_and_altered_records_fail(self):
        observer = GitSourceObserver(self.pin, self.root)
        observed = observer.observe()
        with self.assertRaises(ValidationError):
            GitSourceObservation()
        with self.assertRaises(ValidationError):
            copy.copy(observed)
        foreign = GitSourceObserver(self.pin, self.root)
        with self.assertRaises(ValidationError):
            foreign.require(observed)
        clone = object.__new__(GitSourceObservation)
        for name in ("_owner", "_nonce", "_payload", "_signature", "_sealed"):
            object.__setattr__(clone, name, object.__getattribute__(observed, name))
        with self.assertRaises(ValidationError):
            observer.require(clone)
        object.__setattr__(observed, "_signature", "0" * 64)
        with self.assertRaises(ValidationError):
            observer.require(observed)

    def test_wrong_head_dirty_or_nested_root_fails(self):
        (self.root / "source.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(ValidationError):
            GitSourceObserver(self.pin, self.root).observe()
        self.git("restore", "source.txt")
        wrong = {**self.pin, "revision": "0" * 40}
        with self.assertRaises(ValidationError):
            GitSourceObserver(wrong, self.root).observe()
        nested = self.root / "nested"
        nested.mkdir()
        with self.assertRaises(ValidationError):
            GitSourceObserver(self.pin, nested).observe()
        for invalid in ("latest", "A" * 40, "0" * 39):
            with self.assertRaises(ValidationError):
                GitSourceObserver({**self.pin, "revision": invalid}, self.root)
        with self.assertRaises(ValidationError):
            GitSourceObserver({**self.pin, "repository": "example/latest"}, self.root)

    def test_inherited_git_environment_cannot_redirect_observation(self):
        observer = GitSourceObserver(self.pin, self.root)
        with mock.patch.dict(os.environ, {"GIT_DIR": str(self.root / "missing-git-dir")}):
            observation = observer.observe()
            self.assertEqual(observer.require(observation)["revision"], self.revision)

    def test_observation_is_stale_after_head_moves(self):
        observer = GitSourceObserver(self.pin, self.root)
        observation = observer.observe()
        (self.root / "source.txt").write_text("new source\n", encoding="utf-8")
        self.git("add", "source.txt")
        self.git("-c", "user.name=Observer Test", "-c", "user.email=observer@example.invalid", "commit", "-qm", "new")
        with self.assertRaises(ValidationError):
            observer.require(observation)


if __name__ == "__main__":
    unittest.main()
