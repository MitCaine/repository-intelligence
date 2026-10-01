"""Optional offline probe of published Poker callsites, never a production run.

Only disposable Git/data are written. Qualification eligibility is a fixture,
not a claim that a product candidate passed. No model, network or acceptance call.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--consumer', type=Path, required=True)
    args = parser.parse_args()
    consumer = args.consumer.resolve()
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    def git(*argv):
        return subprocess.check_output(['git', '-C', str(consumer), *argv], env=env, timeout=30)
    commit = git('rev-parse', 'HEAD').decode().strip()
    archive = git('archive', commit, 'scripts')
    with tempfile.TemporaryDirectory(prefix='ri-attempt-boundary-') as raw:
        root = Path(raw).resolve()
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            # Only tracked regular script files: no links, traversal or checkout writes.
            for member in source.getmembers():
                path = root / member.name
                if not path.resolve().is_relative_to(root):
                    raise ValueError('archive path escapes scratch')
                if member.issym() or member.islnk():
                    continue
                if member.isfile():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(source.extractfile(member).read())
        sys.path.insert(0, str(root))
        from scripts.test_capsule_checkpoints import Fixture
        from scripts.capsule_engine.checkpoints import Store, Policy
        from scripts.capsule_engine import artifacts
        fixture = Fixture()
        results = []
        try:
            store = Store(root / 'attempts', fixture.facts, fixture.runtime, 'fixture-implementor', Policy())
            # Isolate allocation persistence from eligibility, which belongs to Q.
            store.outcome = lambda **kwargs: 'QUALIFIED'
            with store.lock():
                store.register(fixture.root)
                attempt, directory = store.allocate_review()
            allocation = (directory / 'allocation.json').read_bytes()
            reopened = Store(root / 'attempts', fixture.facts, fixture.runtime, 'fixture-implementor', Policy())
            expect((directory / 'allocation.json').read_bytes() == allocation, 'allocation changed')
            expect(len(list((reopened.directory / 'attempts').iterdir())) == 1, 'duplicate allocation')
            expect('started' not in json.loads(allocation), 'allocation claims startup')
            results.append('lost-allocation-return-retains-one-allocation-not-start-proof')
            # Actual immutable publication: completion survived a lost caller return.
            payload = artifacts.canonical({'kind': 'fixture-completion', 'candidate': fixture.c})
            destination = directory / 'fixture-completion.json'
            artifacts.publish_bytes(payload, destination)
            digest = hashlib.sha256(payload).hexdigest()
            expect(artifacts.read_verified(destination, digest)['candidate'] == fixture.c, 'completion candidate mismatch')
            artifacts.publish_bytes(payload, destination)
            expect(destination.read_bytes() == payload, 'completion bytes changed')
            results.append('lost-completion-return-reconciles-identical-immutable-object')
            try:
                artifacts.publish_bytes(artifacts.canonical({'candidate': fixture.base}), destination)
            except ValueError:
                results.append('conflicting-completion-rejected')
            else:
                raise AssertionError('conflicting publication accepted')
            # A local integration ref changed before acknowledgement was lost.
            fixture.g.run('update-ref', 'refs/heads/integration-fixture', fixture.c)
            observed = fixture.g.text('rev-parse', 'refs/heads/integration-fixture')
            expect(observed == fixture.c, 'integration ref mismatch')
            # Reconciliation observes the existing ref; no second integration call.
            results.append('lost-local-ref-ack-reconciles-exact-ref-without-reapplying')
            reopened.outcome = lambda **kwargs: 'QUALIFIED'
            with reopened.lock():
                reopened.allocate_review()  # Existing one retry, no budget reset.
                try:
                    reopened.allocate_review()
                except ValueError:
                    results.append('reopen-preserves-finite-allocation-budget')
                else:
                    raise AssertionError('attempt budget renewed')
        finally:
            fixture.close()
        print(json.dumps({'consumer_commit': commit, 'callsites': ['Store.allocate_review',
            'artifacts.publish_bytes', 'artifacts.read_verified'], 'passed': results,
            'limitations': ['qualification eligibility is synthetic', 'no actual dispatch or model startup',
                'local ref observation is not remote guarded integration',
                'no production report import or end-of-turn host continuation']}, indent=2))


if __name__ == '__main__':
    main()
