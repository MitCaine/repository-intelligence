"""Small optional conformance checks over explicitly mapped consumer facts."""
from __future__ import annotations
import hashlib
import json


def request_digests(raw: bytes) -> dict[str, str]:
    value = json.loads(raw)
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    return {'raw_file_sha256': hashlib.sha256(raw).hexdigest(),
            'canonical_json_sha256': hashlib.sha256(canonical).hexdigest()}


def assess(facts: dict, expected_digests: dict) -> dict:
    """Consumer adapter maps native fields; never treat stability as gate success."""
    if not isinstance(facts, dict):
        return {'ready': False, 'errors': ['Consumer facts must be an object'], 'outcomes': None}
    errors = []
    digests = facts.get('request_digests')
    if not isinstance(digests, dict) or not digests or set(digests) - set(expected_digests):
        errors.append('Request hash representation is absent or unsupported')
    elif any(value != expected_digests[name] for name, value in digests.items()):
        errors.append('Request digest mismatch')
    if facts.get('source_stable') is not True or facts.get('terminal_complete') is not True:
        errors.append('Stable source and complete terminal are independently required')
    outcomes = facts.get('outcomes')
    if not isinstance(outcomes, list) or not outcomes:
        errors.append('Explicit outcomes required')
    else:
        for row in outcomes:
            if not isinstance(row, dict) or type(row.get('mandatory')) is not bool or row.get('status') not in ('passed', 'failed', 'blocked', 'unlaunched', 'incomplete'):
                errors.append('Outcome mapping invalid')
            elif row['mandatory'] and row['status'] != 'passed':
                errors.append('Mandatory outcome did not pass')
    return {'ready': not errors, 'errors': errors, 'outcomes': outcomes}
