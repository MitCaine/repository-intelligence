"""Real local Git observations for source materialization authority."""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import repository_intelligence.acquisition as acquisition
from repository_intelligence.acquisition import (
    GitSourceObserver, GitSourceObservation,
    LocalFileAcquisitionObserver, LocalFileAcquisitionObservation,
)
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


class LocalFileAcquisitionObserverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.file = self.root / "material.bin"
        self.file.write_bytes(b"independently observed input\n")
        self.identity = {
            "input_id": "input-local-a",
            "source_or_registry_id": "registry-a",
            "kind": "candidate-binary",
            "sha256": hashlib.sha256(self.file.read_bytes()).hexdigest(),
        }

    def test_controller_reads_exact_bytes_and_rechecks_before_use(self):
        observer = LocalFileAcquisitionObserver(self.identity, self.file)
        observed = observer.observe()
        self.assertEqual(observer.require(observed)["sha256"], self.identity["sha256"])
        self.assertEqual(observer.require(observed)["byte_size"], self.file.stat().st_size)
        self.assertEqual(observed.as_dict()["observation_kind"], "controller_read_regular_file")
        self.identity["sha256"] = "0" * 64
        self.assertNotEqual(observer.require(observed)["sha256"], self.identity["sha256"])
        with self.assertRaises(AttributeError):
            observer._path = self.root / "other"
        with self.assertRaises(AttributeError):
            observed._nonce = "replacement"
        self.file.write_bytes(b"changed input\n")
        with self.assertRaises(ValidationError):
            observer.require(observed)

    def test_restoring_same_bytes_does_not_revalidate_stale_observation(self):
        observer = LocalFileAcquisitionObserver(self.identity, self.file)
        observed = observer.observe()
        original = self.file.read_bytes()
        self.file.write_bytes(b"temporary change")
        self.file.write_bytes(original)
        with self.assertRaises(ValidationError):
            observer.require(observed)

    def test_forgeries_foreign_observations_and_copies_fail(self):
        observer = LocalFileAcquisitionObserver(self.identity, self.file)
        observed = observer.observe()
        with self.assertRaises(ValidationError):
            LocalFileAcquisitionObservation()
        with self.assertRaises(ValidationError):
            copy.copy(observed)
        with self.assertRaises(ValidationError):
            copy.deepcopy(observed)
        foreign = LocalFileAcquisitionObserver(self.identity, self.file)
        with self.assertRaises(ValidationError):
            foreign.require(observed)
        clone = object.__new__(LocalFileAcquisitionObservation)
        for name in ("_owner", "_nonce", "_payload", "_signature", "_sealed"):
            object.__setattr__(clone, name, object.__getattribute__(observed, name))
        with self.assertRaises(ValidationError):
            observer.require(clone)
        object.__setattr__(observed, "_signature", "0" * 64)
        with self.assertRaises(ValidationError):
            observer.require(observed)
        with self.assertRaises(ValidationError):
            observer.require(observed.as_dict())

    def test_missing_nonregular_symlink_and_mismatch_fail(self):
        wrong = {**self.identity, "sha256": "0" * 64}
        with self.assertRaises(ValidationError):
            LocalFileAcquisitionObserver(wrong, self.file).observe()
        with self.assertRaises(ValidationError):
            LocalFileAcquisitionObserver(self.identity, self.root / "missing").observe()
        with self.assertRaises(ValidationError):
            LocalFileAcquisitionObserver(self.identity, self.root).observe()
        link = self.root / "linked.bin"
        link.symlink_to(self.file)
        with self.assertRaises(ValidationError):
            LocalFileAcquisitionObserver(self.identity, link).observe()
        parent_link = self.root / "linked-dir"
        parent_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValidationError):
            LocalFileAcquisitionObserver(self.identity, parent_link / self.file.name).observe()

    def test_authored_identity_rejects_mutable_values_and_malformed_digests(self):
        for key in ("input_id", "source_or_registry_id", "kind"):
            for value in ("latest", "current", "any", "a/../b", ""):
                with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                    LocalFileAcquisitionObserver({**self.identity, key: value}, self.file)
        for value in ("A" * 64, "a" * 63, True):
            with self.subTest(digest=value), self.assertRaises(ValidationError):
                LocalFileAcquisitionObserver({**self.identity, "sha256": value}, self.file)
        with self.assertRaises(ValidationError):
            LocalFileAcquisitionObserver({**self.identity, "unexpected": "field"}, self.file)

    def test_observation_size_is_bounded(self):
        with mock.patch.object(acquisition, "_MAX_LOCAL_INPUT_BYTES", 1):
            with self.assertRaises(ValidationError):
                LocalFileAcquisitionObserver(self.identity, self.file).observe()


if __name__ == "__main__":
    unittest.main()
