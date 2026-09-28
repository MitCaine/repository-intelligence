---
name: capsule-independent-review
description: Conduct or prepare a fresh, read-only review of one exact capsule candidate against its acceptance criteria and repository standards. Use for the independent reviewer lane, not self-review or controller approval.
---

# Capsule independent review

Use a fresh reviewer context when the consumer workflow requires independence. The controller supplies the controlling capsule and intent, exact planning/base and candidate identities, scope, complete changed-file list and diff including relevant untracked content, required checks and their raw outcomes, and current repository standards. Authenticate these against the candidate before judging it. Missing or inconsistent inputs are an evidence failure, not an implied PASS.

Keep the review read-only and bound to one candidate. Inspect actual source, contracts, call sites, configuration, build conditions, and tests needed for the stated acceptance criteria. RI may help navigate or compare stable planning and candidate trees, but its result is not a behavioral oracle or authorization. Require independently expected source slices, names, kinds, deltas, or runtime outcomes where the criterion needs them; agreement between production counters alone is insufficient.

Report a disposition for every active acceptance criterion and for applicable repository standards. Name the exact evidence and uncertainty behind each PASS or FAIL. Preserve mandatory tests and unsupported or incomplete evidence as unresolved; never convert them into PASS. Give actionable findings with candidate-bound file locations and the smallest useful reproduction. If review finds a substantive failure, preserve the failed candidate and evidence. A changed candidate needs fresh applicable qualification and review; do not transfer an earlier verdict.

Account for the controlling objective beyond RI's selected source contract. Check relevant configuration, manifests, workflows, build conditions, and unsupported source through the full diff and suitable evidence. If a capsule revision silently drops a requirement, return a finding instead of treating the narrower list as complete.

Return the complete review to the controller. Do not edit the candidate, approve, publish, accept, merge, or close the capsule from the reviewer lane.
