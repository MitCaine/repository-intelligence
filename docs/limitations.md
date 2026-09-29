# Limits and interpretation

Use these limits when deciding what additional source or tool evidence a task
needs. Current packet fields and byte limits are in [navigation](navigation.md);
per-language promises are in [language support](language-support.md).

| Area | Current limit | Consumer action |
| --- | --- | --- |
| Search | Lexical ranking and bounded display; zero matches does not prove absence | Refine a named question and inspect relevant source |
| Coverage | Only the declared source constructs in selected supported files | Review unsupported paths, omissions, failures, and the full changed-file list |
| Program behavior | Imports, types, enclosing containers, initializers, and configuration may change without callable deltas | Read the owning contracts and relevant file changes |
| Markdown | Block grammar maps headings, front matter, and task items; it does not validate capsule fields, links, inline syntax, or acceptance decisions | Run the consumer's capsule validator and inspect the full document diff |
| C/C++ and generated code | Macros, includes, conditional compilation, and build settings are unexpanded | Use compiler/build evidence when effective declarations matter |
| Source freshness | Directory reads are non-atomic; `stable=True` is the caller's assertion | Supply stable materializations for comparison; refresh changed working-source locations |
| Identity | Hashes identify observed bytes, not commit membership; anonymous offsets can move | Bind planning through the consumer's Git workflow; accept conservative ambiguous/add-remove deltas |
| Scan policy | Explicit exclusions do not implement `.gitignore` or tracked-file selection | Select roots, headers, and exclusions deliberately |
| Native fallback | Syntax/native providers have distinct coverage and result shapes | Preserve each result; do not silently merge or upgrade an incomplete inventory |
| Rust semantics | One definition query; local checksums omit external dependencies/sysroot, build scripts and procedural macros are disabled | Retain provider/configuration/target evidence and unresolved limits |
| Hosts | Package metadata permits more environments than have been exercised | Use the [verification record](maintenance.md#verification-scope) rather than infer support |

The scanner bounds acquisition and parsing separately. Legacy/native APIs have
separate resource behavior. See [navigation limits](navigation.md#status-and-byte-identity)
and [native analysis](native-analysis.md) before substituting one path for another.

Corrected defects and historical measurements belong in the [audit record](archive/audit-2026-09-25.md),
not a current bug list. Passing accounting counters and fixtures support their
specific promises; they do not establish exhaustive grammar correctness.
