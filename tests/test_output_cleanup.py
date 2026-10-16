"""Real disposable filesystem cases for the optional shared lifecycle seam.

The fixture owner uses one definition for creation and validation. The tiny
disposal callbacks are synthetic consumer adapters, not Poker/Nutrition wiring.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from repository_intelligence.output_cleanup import (
    assess_output, create_output, dispose_output,
)
from repository_intelligence.worker_execution import identity


@unittest.skipUnless(os.name == 'posix', 'optional local output interface is POSIX-only')
class OutputCleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.definition = self.root / 'selected-runner.json'
        self.definition.write_text('{"output":"target"}\n')
        self.binding = identity(self.definition)
        # Same owner definition drives the actual exclusive creation and validation.
        self.output = self.root / json.loads(self.definition.read_text())['output']
        self.receipt = create_output(str(self.output), task='T1', attempt='A1', definition=self.binding)
        (self.output / 'build.o').write_bytes(b'compiled fixture\n')
        self.original_log = self.output / 'failed.log'
        self.original_log.write_bytes(b'original failing gate; source abc\n')
        self.durable = self.root / 'retained'
        self.durable.mkdir()
        retained_log = self.durable / 'failed.log'
        shutil.copyfile(self.original_log, retained_log)
        self.assertEqual(identity(retained_log)['sha256'], identity(self.original_log)['sha256'])
        self.retained = [identity(retained_log)]
        # Current pointers relocate; original source/command/path identities stay in the log.
        self.reference = self.durable / 'current-reference.txt'
        self.reference.write_text(str(retained_log))
        self.protected = [str(self.durable)]
        self.observation = dict(task='T1', attempt='A1', state='completed', exclusive=True,
                                quiescent=True, regenerable=True, source_preserved=True,
                                references_relocated=True)
        self.calls = []

    def assess(self, **kwargs):
        return assess_output(self.receipt, self.observation,
                             protected=kwargs.get('protected', self.protected),
                             retained=kwargs.get('retained', self.retained))

    def delete(self, path):
        self.calls.append(path)
        shutil.rmtree(path)
        return {'kind': 'deleted'}

    def dispose(self, **kwargs):
        return dispose_output(self.receipt, self.observation, protected=self.protected,
                              retained=self.retained, authorized=kwargs.get('authorized', True),
                              dispose=kwargs.get('dispose', self.delete))

    def test_creation_receipt_is_exact_and_cannot_adopt_existing_output(self):
        self.assertEqual(self.receipt['definition'], self.binding)
        self.assertEqual(self.receipt['node'], [self.output.stat().st_dev, self.output.stat().st_ino])
        with self.assertRaises(FileExistsError):
            create_output(str(self.output), task='T1', attempt='A2', definition=self.binding)
        self.definition.write_text('changed authoritative definition\n')
        self.assertEqual(self.assess()['status'], 'retained')

    def test_completed_output_dry_run_exact_bytes_then_delete_and_retry(self):
        expected = len(b'compiled fixture\n') + len(b'original failing gate; source abc\n')
        before = self.assess()
        self.assertEqual((before['path'], before['status'], before['bytes']),
                         (str(self.output), 'eligible', expected))
        self.assertTrue(self.output.exists())  # Dry run never disposes.
        result = self.dispose()
        self.assertEqual((result['status'], result['removed_bytes']), ('deleted', expected))
        self.assertIsNone(result['reclaimed_bytes'])  # Logical size is not physical disk reclamation.
        retry = self.dispose()
        self.assertEqual((retry['status'], retry['removed_bytes']), ('absent', 0))
        self.assertEqual(len(self.calls), 1)
        retained_log = Path(self.reference.read_text())
        self.assertEqual(retained_log.read_bytes(), b'original failing gate; source abc\n')
        self.assertEqual(identity(retained_log), self.retained[0])

    def test_superseded_terminal_is_eligible_but_active_paused_unknown_are_not(self):
        for state in ('active', 'paused', 'unknown', 'superseded', None):
            with self.subTest(state=state):
                self.observation['state'] = state
                self.assertEqual(self.dispose()['status'], 'retained')
        self.observation['state'] = 'superseded_terminal'
        self.assertEqual(self.assess()['status'], 'eligible')
        self.assertEqual(self.calls, [])

    def test_unknown_shared_live_runtime_or_unretained_source_blocks_only_item(self):
        original = self.observation.copy()
        for fact in ('exclusive', 'quiescent', 'regenerable', 'source_preserved', 'references_relocated'):
            for value in (False, None, 'true', 1):
                with self.subTest(fact=fact, value=value):
                    self.observation = dict(original, **{fact: value})
                    self.assertEqual(self.dispose()['status'], 'retained')
        self.assertTrue(self.output.exists())
        self.assertEqual(self.calls, [])

    def test_unique_uncommitted_source_is_preserved_until_consumer_establishes_recovery(self):
        source = self.output / 'uncommitted.rs'
        source.write_text('unique uncommitted source\n')
        self.observation['source_preserved'] = False
        self.assertEqual(self.dispose()['status'], 'retained')
        self.assertEqual(source.read_text(), 'unique uncommitted source\n')

    def test_missing_permission_does_not_delete(self):
        self.assertEqual(self.dispose(authorized=False)['status'], 'retained')
        self.assertEqual(self.calls, [])

    def test_required_runtime_shared_path_and_retained_file_inside_output_are_protected(self):
        for protected in ([str(self.output)], [str(self.output / 'build.o')], [str(self.root)]):
            with self.subTest(protected=protected):
                self.assertEqual(self.assess(protected=protected)['status'], 'retained')
        self.assertEqual(self.assess(retained=[identity(self.original_log)])['status'], 'retained')

    def test_retention_must_be_complete_readable_and_match_original_identity(self):
        self.assertEqual(self.assess(retained=[])['status'], 'retained')
        self.assertEqual(self.assess(protected=[])['status'], 'retained')
        retained_log = Path(self.retained[0]['path'])
        retained_log.write_bytes(b'changed failure history')
        self.assertEqual(self.dispose()['status'], 'retained')
        retained_log.unlink()
        self.assertEqual(self.dispose()['status'], 'retained')

    @unittest.skipIf(getattr(os, 'geteuid', lambda: 0)() == 0, 'root can bypass fixture filesystem permissions')
    def test_real_unreadable_output_or_evidence_cannot_pass(self):
        directory = self.output / 'unreadable'
        directory.mkdir()
        (directory / 'hidden.o').write_bytes(b'not empty')
        directory.chmod(0)
        try:
            self.assertEqual(self.dispose()['status'], 'retained')
        finally:
            directory.chmod(0o700)
        retained_log = Path(self.retained[0]['path'])
        retained_log.chmod(0)
        try:
            self.assertEqual(self.dispose()['status'], 'retained')
        finally:
            retained_log.chmod(0o600)

    def test_symlink_ancestor_root_descendant_hardlink_and_fifo_refused(self):
        sentinel = self.root / 'outside.txt'
        sentinel.write_text('outside sentinel')
        link = self.output / 'link'
        link.symlink_to(sentinel)
        self.assertEqual(self.dispose()['status'], 'retained')
        link.unlink()
        os.link(sentinel, link)
        self.assertEqual(self.dispose()['status'], 'retained')
        link.unlink()
        os.mkfifo(link)
        self.assertEqual(self.dispose()['status'], 'retained')
        link.unlink()
        self.output.rename(self.root / 'moved')
        self.output.symlink_to(self.root / 'moved', target_is_directory=True)
        self.assertEqual(self.dispose()['status'], 'retained')
        alias = self.root / 'alias'
        alias.symlink_to(self.root / 'moved', target_is_directory=True)
        with self.assertRaises(ValueError):
            create_output(str(alias / 'child'), task='T1', attempt='A2', definition=self.binding)
        self.assertEqual(sentinel.read_text(), 'outside sentinel')

    def test_path_escape_and_replaced_identity_refused(self):
        record = copy.deepcopy(self.receipt)
        record['path'] = str(self.output) + '/../target'
        self.assertEqual(assess_output(record, self.observation, protected=self.protected,
                                      retained=self.retained)['status'], 'retained')
        self.output.rename(self.root / 'original-target')
        self.output.mkdir()
        self.assertEqual(self.dispose()['status'], 'retained')

    def test_recoverable_disposal_does_not_claim_reclaimed_bytes(self):
        quarantine = self.root / 'quarantined-target'
        def move(path):
            path.rename(quarantine)
            return {'kind': 'quarantined', 'path': str(quarantine)}
        result = self.dispose(dispose=move)
        self.assertEqual((result['status'], result['reclaimed_bytes'], result['removed_bytes']),
                         ('quarantined', 0, 0))
        self.assertTrue((quarantine / 'build.o').exists())

    def test_partial_failure_and_bad_adapter_result_remain_incomplete(self):
        def partial(path):
            (path / 'build.o').unlink()
            raise OSError('fixture failure after partial removal')
        result = self.dispose(dispose=partial)
        self.assertEqual(result['status'], 'incomplete')
        self.assertIsNone(result['removed_bytes'])
        self.assertTrue(self.original_log.exists())
        self.assertEqual(self.dispose()['status'], 'deleted')  # Reobserved safe retry.

    def test_unknown_item_does_not_block_an_independent_safe_item(self):
        old = self.receipt
        self.receipt = {}
        self.assertEqual(self.dispose()['status'], 'retained')
        self.receipt = old
        self.assertEqual(self.dispose()['status'], 'deleted')

    def test_ordinary_callback_exceptions_after_partial_removal_are_incomplete(self):
        class AdapterFailure(Exception):
            pass
        for failure in (RuntimeError, AdapterFailure):
            with self.subTest(failure=failure.__name__):
                (self.output / 'build.o').write_bytes(b'compiled fixture\n')
                def partial(path):
                    (path / 'build.o').unlink()
                    raise failure('adapter stopped after removing one output')
                result = self.dispose(dispose=partial)
                self.assertEqual(result['status'], 'incomplete')
                self.assertIsNone(result['removed_bytes'])
                self.assertIsNone(result['reclaimed_bytes'])
                self.assertTrue(self.original_log.exists())
                self.assertIn('adapter stopped', result['reason'])

    def test_wrong_attempt_and_unknown_quarantine_outcome_do_not_pass(self):
        self.observation['attempt'] = 'other'
        self.assertEqual(self.dispose()['status'], 'retained')
        self.observation['attempt'] = 'A1'
        def wrong(path):
            shutil.rmtree(path)
            return {'kind': 'quarantined', 'path': str(self.root / 'missing')}
        self.assertEqual(self.dispose(dispose=wrong)['status'], 'incomplete')
