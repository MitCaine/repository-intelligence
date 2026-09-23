"""Tests for sealed independently replayed conformance authority."""
from __future__ import annotations

import copy
import unittest

from repository_intelligence.conformance import (
    AuthenticatedConformanceRun,
    ConformanceRunner,
)
from repository_intelligence.errors import ValidationError


class ConformanceRunnerTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {"case_id": "case-a", "disposition": "pass", "checks": ["check-a"]},
            {
                "case_id": "case-b",
                "disposition": "pass",
                "checks": ["check-b", "check-c"],
            },
        ]
        self.expected = {
            "case-a": ("check-a",),
            "case-b": ("check-b", "check-c"),
        }
        self.runner = ConformanceRunner(self.expected, lambda: self.records)

    def test_run_is_authenticated_frozen_and_defensively_copied(self):
        run = self.runner.run()
        self.records[0]["checks"].append("later")
        cases = self.runner.require(run)
        self.assertEqual(cases[0]["checks"], ("check-a",))
        with self.assertRaises(TypeError):
            cases[0]["case_id"] = "other"
        with self.assertRaises(AttributeError):
            self.runner._evaluator = lambda: []
        with self.assertRaises(ValidationError):
            AuthenticatedConformanceRun()
        with self.assertRaises(ValidationError):
            copy.copy(run)
        copied = object.__new__(AuthenticatedConformanceRun)
        for name in ("_owner", "_cases", "_nonce", "_signature", "_sealed"):
            object.__setattr__(copied, name, object.__getattribute__(run, name))
        with self.assertRaises(ValidationError):
            self.runner.require(copied)

    def test_foreign_runner_and_tampered_case_shapes_fail_closed(self):
        run = self.runner.run()
        foreign = ConformanceRunner(self.expected, lambda: self.records)
        with self.assertRaises(ValidationError):
            foreign.require(run)
        variants = (
            self.records[:-1],
            list(reversed(self.records)),
            self.records + [self.records[0]],
            [{**self.records[0], "extra": True}, self.records[1]],
            [{**self.records[0], "disposition": "fail"}, self.records[1]],
            [
                {**self.records[0], "checks": ["receipt-selected"]},
                self.records[1],
            ],
        )
        for records in variants:
            runner = ConformanceRunner(self.expected, lambda records=records: records)
            with self.subTest(records=records), self.assertRaises(ValidationError):
                runner.run()

    def test_expected_contract_is_copied_and_closed(self):
        expected = {"case-a": ["check-a"]}
        runner = ConformanceRunner(expected, lambda: [self.records[0]])
        expected["case-a"].append("later")
        self.assertEqual(runner.require(runner.run())[0]["checks"], ("check-a",))
        for invalid in (
            {},
            {"case-a": []},
            {"case-a": ["check-a", "check-a"]},
            {"case a": ["check-a"]},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                ConformanceRunner(invalid, lambda: [])

    def test_each_authenticated_run_reexecutes_the_sealed_evaluator(self):
        calls = []

        def evaluate():
            calls.append(len(calls) + 1)
            return [self.records[0]]

        runner = ConformanceRunner({"case-a": ("check-a",)}, evaluate)
        runner.require(runner.run())
        runner.require(runner.run())
        self.assertEqual(calls, [1, 2])


if __name__ == "__main__":
    unittest.main()
