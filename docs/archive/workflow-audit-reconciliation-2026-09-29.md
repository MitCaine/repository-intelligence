# Workflow audit reconciliation — 2026-09-29

The supplied audit inspected RI `e882fcfde65da02b3aed4ae44463ba73326889b3`
and Poker `51d148a971e96ada626b6d3c61f9f08547e0f716`. This reconciliation
includes later local RI changes; it is not hosted qualification of an unpublished
commit. Consumer source was read locally at the same audited Poker revision.

| Finding | RI correction | Verification boundary |
| --- | --- | --- |
| WF-01 | Mandatory runtime compatibility probe before accepting P; runtime/harness drift invalidates dependent readiness. | Local constants confirm the mismatch; no consumer upgrade or installed-runtime qualification performed. |
| WF-02 | Resolved execution map and consumer-authorized capture/publication; Poker recipe refreshed from its command owner. | Preserve explicit implementor commit/push grants in consumers that permit them. No consumer permissions changed. |
| WF-03 | POSIX group cleanup independent of leader exit; bounded TERM/KILL cleanup with truthful unresolved status. | Real macOS TERM-ignoring descendant writer regression passes; escaped sessions/remote jobs remain outside local containment. |
| WF-04 | Review/parser/export fixture gate and accepted report requirements; Poker dispositions and export supplements documented. | Consumer installation/import/export trial still required. |
| WF-05 | Current-phase required inputs and recovery; correction lineage/allowance remains consumer-owned. | No new universal status engine or allowance introduced. |
| WF-06 | Retained checkpoint, live resume verification and safe rule adoption. | Fresh/resumed/active-job/adoption trials specified; Work-host wake-up remains unqualified. |
| WF-07 | Collection, fixture, skips/deselection, baseline and hosted workflow/source requirements explicit. | Exact source-bound behavioral proof remains the consumer's runner responsibility. |
| WF-08 | Same-page fragments, visible inline-code heading words, reference links and strict scalar-manifest parsing. | Focused fixtures pass; YAML support is an explicitly limited subset. Mechanical validation does not prove agent behavior. |
| WF-09 | Closeout predicate requires retrievable source/evidence, issue/history/ref and safe checkout reconciliation before pruning. | History/probe template checks pass; real guarded consumer closeout remains required. |

RI source/offline verification passed 303 tests after the main changes. Queue
regressions were rerun after preserving timeout outcome on cleanup errors.
Documentation links and whitespace checks passed. No live notification,
production consumer acceptance, remote mutation or skill installation occurred.
The audit's original limitations and the adoption probe's partial qualification
remain in force. See the current controller, setup, Poker and adoption guides
for procedural ownership rather than treating this historical record as policy.
