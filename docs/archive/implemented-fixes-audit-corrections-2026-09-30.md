# Implemented-fixes audit corrections — 30 September 2026

The supplied implementation audit tested published `4353a837` with actual parsers,
helpers, subprocesses and CLI boundaries. Its five grouped findings were confirmed
and corrected locally. Nothing here establishes consumer adoption or host wake-up.

| Finding | Correction | Discriminating regression |
| --- | --- | --- |
| #84 mixed heading ancestry | Preserve logical levels across transparent grammar sections, isolate quote/list scopes. | 25 syntax pairs and 45 seeded traces across LF/CRLF/CR, exact paths/slices, separate-parent Details identities and one modified-section delta, quote-scope isolation. |
| #91 malformed reuse policy | Validate nonempty string claims and unique nonempty string-list allowlists before exact membership. | Exact-list positive; substring string, dictionary, duplicate, empty, numeric and null negatives. |
| #81/#82 JSON type substitution | Compare canonical recomputed JSON bytes. | Integer/float and zero/false substitutions with newly valid envelope hashes reject through verifier and read CLI; valid bundle remains readable. |
| #81/#82 expanded nesting | Check decoded depth after every reference expansion. | Shallow wire expanding past the 80-level bound rejects; decoded depth 80 succeeds; builder also rejects excessive input. |
| #94 first success inspection failure | Route initial permission uncertainty into the existing bounded cleanup routine. | Actual exit-zero child and transient-then-absent control; actual TERM-ignoring descendant stops writing. Persistent uncertainty remains unconfirmed. |

Markdown identities change, so adapter/mapping is v13 and inventory schema 16.
Navigation schema 7 and bundle wire schema 1 retain their shapes. Valid bundle
compatibility remains; malformed type/depth substitutions no longer verify.
Existing consumer pins require separate adoption rather than automatic replacement.

Issues #84, #91 and #94 were reopened pending publication; bundle work remains
under open #81/#82. Corrections are uncommitted and unpublished. An added CLI test
initially shadowed a fixture path variable, causing two test errors; that fixture
mistake was corrected separately from the product defects. The audit's future-
failed-obligation observation remains a contract question, not a confirmed sixth
bug or an authorized lifecycle-policy change.

## Verification

The corrected checkout passed full `scripts/maintain.py verify`: 354 tests,
zero skips and zero failures. The later expanded 210-evaluation Markdown
regression passed separately (same production bytes), as did documentation
links, five skill manifests and `git diff --check`. No hosted run of these local
changes was performed; the audit report’s native-Rust skips describe its host,
not this successful local run.
