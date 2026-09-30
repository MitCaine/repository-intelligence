# Consumer evidence-preflight adapter

Use [the helper](../scripts/evidence_preflight.py) after candidate freeze and
before qualification/review handoff. It reads Git and local files, executes no
test commands, and writes only a JSON result to stdout. It is a portable source
template, not RI runtime behavior or a consumer authorization engine.

The consumer must export `contract.json` from its authenticated capsule,
authorization, accepted scope inventory and frozen execution plan. Export
`packet.json` from actual runner records. Store both and retained logs in the
consumer's existing permitted evidence area outside the clean candidate checkout.
Never let the implementor self-author the trusted expectations. These files are
adapter views of existing records, not a new authoritative receipt format.

Run with the interpreter available in that consumer:

```sh
python path/to/capsule-preflight/scripts/evidence_preflight.py \
  --repository /path/to/candidate --contract /path/to/contract.json \
  --packet /path/to/packet.json
```

Exit 0 reports `disposition: checked`; exit 2 reports `blocked` with a reason.
Checked means these deterministic comparisons passed. It does not establish
scope purpose, independent review, authorization signatures, run provenance,
remote branch identity, or approval. The consumer authenticates those through
its own tools and rejects an untrusted contract or packet before this helper.
The helper does not parse logs into test results: the trusted runner adapter
must reconcile exported observations with raw logs. Hashes detect retained-byte
changes; they do not authenticate the person or process that supplied them.

## Export fields

Both documents are JSON objects with `schema_version: 1`. Duplicate keys,
unsupported versions, malformed JSON and missing required data block.

Contract fields:

| Field | Value |
| --- | --- |
| `identity` | Object with nonempty `task_id`, positive integer `revision`, and full lowercase commit SHAs `base`, `planning`, `candidate` |
| `allowed_paths` | Nonempty list of unique exact repository-relative paths, exported after the consumer applies its own matcher/version rules |
| `inventory` | Nonempty list of unique `path`, `disposition` (`edit` or `inspect`), and nonempty `purpose` rows from accepted scope review |
| `checks` | Nonempty list with unique `id`, nonempty `profile`, booleans `probe_required` and `rehearsal_required`, and `allowed_skip_ids` (possibly empty) |

For a check requiring rehearsal, include `invocation` with exactly these fields:

| Field | Value |
| --- | --- |
| `argv` | Nonempty argument list; no shell evaluation occurs |
| `cwd` | Canonical repository-relative directory, `.` for repository root |
| `config` | String-to-string mapping of consumer-selected configuration identities/digests |
| `interpreter` | Exact interpreter/toolchain identity selected by consumer |
| `profiles` | Nonempty list of unique profiles |
| `isolation` | Exact protected policy identity/digest |
| `environment` | String-to-string mapping of relevant nonsecret settings; never export credentials |
| `source_files` | Nonempty path-to-identity mapping (`mode`: Git mode string, `sha256`: raw-byte hash) covering every rehearsal-sensitive test, fixture, runner and configuration file; the helper compares modes/types and hashes to Git C entries |

The consumer decides relevant source/configuration coverage. Equal incomplete
maps cannot prove complete rehearsal equivalence. New subprocess checks require `rehearsal_required: true` where the protected lane supports pre-freeze rehearsal; services requiring committed C instead retain their constraint and exact-C protected proof. Do not turn it off to
pass a failing gate. Ordinary host evidence must not be relabeled as protected.

Packet fields:

| Field | Value |
| --- | --- |
| `identity` | Exact contract identity |
| `checks` | Exactly the required check IDs, each with `candidate`, `profile`, integer `exit_code`, `log_path`, `log_sha256`, integer `skip_count`, and `skips` list |
| each skip | Unique nonempty `id` and nonempty `reason`; IDs must be permitted by the contract |
| `capability_probe` | Required when requested: boolean `available` and nonempty factual `detail` |
| `invocation` | Required for rehearsed checks: exact frozen invocation from contract |
| `rehearsals` | Exactly the IDs requiring rehearsal, each with unique check `id`, integer `exit_code`, exact `invocation`, `log_path` and `log_sha256` for each required rehearsal |

Log paths are relative to the packet directory. Logs must be regular files,
remain within that directory, and match SHA256. Records are limited to 2 MB,
logs to 32 MB. Symlink log files are rejected. Source reads use Git commit
objects; the candidate checkout must head C and be clean. B must precede P,
and P must precede C. Every changed path (both sides of a rename) must be an
authorized inventory edit. No glob or authorization matching policy is added.

## Remaining judgment and recovery

### Closeout and installed-workflow probes

When the consumer requires installation probes, export a `closeout` object in
both contract and packet. Omission of a required packet object blocks. Ordinary
tasks omit both objects; this does not add live probes to every capsule.
The consumer chooses these requirements during planning and must enforce their
presence when required; removing them from an unauthenticated contract is not
a valid bypass.

Build history through the consumer's existing schema-aware builder, if present.
Otherwise adapt its current schema into a builder rather than duplicating its
field list in RI. Run the existing history validator immediately after drafting,
before the planner returns or commits the closeout, then again on exact closeout
C before qualification/review. Retain that successful check among `checks`.

Contract `closeout` fields:

| Field | Value |
| --- | --- |
| `history_check_id` | ID of the mandatory successful history-validator check in `checks` |
| `required_metadata` | Unique nonempty field names exported from the consumer's current schema |
| `metadata` | Complete expected normalized metadata mapping from authenticated issue, repository and retained receipts |
| `installed_base`, `recovery_commit` | Full commit identities, independently authenticated by the consumer |
| `capsule_path`, `capsule_sha256` | Recovery capsule path and SHA256 of its bytes at `recovery_commit` |
| `workflow_identity` | Authenticated identity/digest of the installed trusted workflow |
| `selected_test_id` | Exact test selected for rejection and passing control |
| `probes` | Object with `negative` and `positive`, each containing exact `candidate` and provider `check_id` strings |

Packet `closeout` contains actual normalized `metadata`, `installed_base`,
`recovery_commit`, `capsule_sha256`, and `log_path`/`log_sha256` identifying the
retained original history record. Its `probes` list contains exactly two records:

- `id`: `negative` or `positive`;
- `candidate`, `check_id`, `installed_base`, `workflow_identity`;
- `selected_test_id`, `selected_test_outcome` (`failed` or `passed`);
- `failed_test_ids`: exactly the selected test for negative, empty for positive;
- `qualification_candidate`, `qualification_outcome` (`failed` or `passed`);
- integer `exit_code`: nonzero for negative, zero for positive;
- `log_path` and `log_sha256` for retained probe evidence.

Both probe candidates must descend from the installed base and be distinct
from it and each other. Metadata must match expected values; required fields
cannot be absent or empty. The capsule hash is computed directly from Git.
The adapter must authenticate provider check IDs, installed workflow provenance,
test collection/execution and qualification results, and reconcile normalized
metadata with the original history record. The helper hashes retained bytes;
it does not interpret arbitrary consumer history formats or provider logs.
A generic failing job, an unrelated failed test or a skipped selected test
cannot satisfy the negative probe. Independent review must still judge whether
these observations prove the original issue outcomes.

The scope challenger and controller inspect whether edits fit each purpose;
the script cannot infer this from prose. The consumer verifies remote refs,
actual supported hosts, provenance, standards and independent verdicts.

For missing evidence on unchanged C, use only the consumer's permitted
supplementation or rerun route. Re-export the complete observed packet and
recheck it, preserving failed records and required fresh review. The helper
never supplements records, changes C, retries native work, or approves a repair.

Closeout `validator_evidence` must exactly copy the observed history-validator check's `id`, `candidate`, `exit_code`, `log_path` and `log_sha256`. The trusted adapter must bind that check to validation of the retained history bytes; name membership alone is insufficient. Invocation `cwd` must exist as a directory and physically resolve inside the candidate checkout. Source modes distinguish regular files, executable files and symlinks even when stored bytes match.
