# Native analysis and fallback

Tree-sitter supplies RI's ordinary structural navigation. Native syntax and
semantic questions are separate optional operations. There is no automatic
fallback ladder, universal native provider, or second inventory format to merge.
Keep the original structural result when asking another parser a question.

| Question | Current interface | What it can establish |
| --- | --- | --- |
| Find supported callables across languages | `locator.index_file` / `query_path` | Structural source locations and explicit coverage state |
| Parse Python with the installed interpreter | `python_index.index_source(path, source_bytes)` | Python AST syntax/navigation; support follows the Python version |
| Parse Rust with the installed native parser | `rust_index.index_source(path, source_bytes)` | Legacy named-function syntax/navigation through `rust-analyzer parse`; excludes closures |
| Resolve one Rust reference | `rust_semantic.resolve_definition(...)` | A configured native definition result, with provider and source information |
| Resolve other language references/types/callers | No RI-native interface yet | Use the project's existing language tools for the specific question |

A native AST answers syntax questions. It does not by itself resolve imports,
aliases, dispatch, or types. Rust definition lookup is a separate capability,
not a full call graph. More languages can get small adapters when a consumer
has a demonstrated need; no generic language-server framework is required.

## Preserve bytes and results

Work on a caller-stable materialization when exact same-source comparison is
needed. Start with `index_file`; inspect its status and failures. For a Python
parser gap, the following explicit handoff uses the existing public interfaces:

```python
import hashlib
from pathlib import Path
from repository_intelligence.locator import index_file
from repository_intelligence.python_index import index_source as native_index

root = Path('/path/to/project')
path = root / 'src/example.py'
structural = index_file(path, root=root)
# After deciding a native syntax question is needed for this readable file:
source = path.read_bytes()
if hashlib.sha256(source).hexdigest() != structural['raw_sha256']:
    raise RuntimeError('Source changed: refresh the structural observation')
native = native_index(path, source)
evidence = {'tree_sitter': structural, 'python_ast': native}
```

For Rust syntax, import `index_source` from `repository_intelligence.rust_index`
instead, and label the retained result `rust_analyzer_syntax`. `index_source`
parses the supplied bytes without reopening the file. The caller should retain
its RI revision and native runtime version with saved observations. A failed
native parse remains an error; it must not turn into an empty successful result.
Use this only for a selected readable source within the parser's 4 MB limit;
source exclusions and acquisition limits are not invitations to retry around them.

The source hash comparison prevents mixing observations of different file
contents. It does not claim the source remained unchanged after reading or
prove Git membership. Keep immutable planning observations separate from
subsequent working-tree observations. Refresh the latter when edits move ranges.

A concrete useful gap: Python 3.13's AST accepts
`def target[T = int](value: T): return value`, while the pinned Tree-sitter
Python grammar reports incomplete syntax. Python 3.12 cannot serve that fallback.
The native result remains supplementary navigation: it does not clear the
Tree-sitter failure or make an incomplete inventory comparable.

Do not union native and structural declaration lists or replace one with the
other. Even on identical Python bytes, Tree-sitter can include a trailing
inline comment in a callable's byte envelope while the native AST ends at the
last expression token. Preserve both ranges with their provider labels and use
the original source when choosing a context page. The legacy Rust parser omits closures and has a different declaration
contract. A native result with zero parse errors therefore need not cover all
Tree-sitter callables. The native Rust CLI omits parser diagnostics from its JSON
tree. Its legacy `parse_error_count` counts only `ERROR` nodes; missing closing
delimiters or semicolons can still produce zero. Packets explicitly label this
`diagnostic_coverage: error_nodes_only` and
`parse_error_count_kind: error_node_lower_bound`; compact output carries the same
caveat. Zero is not a syntax-validity claim.
Keep provider labels, original statuses, source hashes,
failures, and complete result records; compact display is a projection only.

## Resolve one Rust reference

`rust_semantic.resolve_definition` asks `rust-analyzer` for
`textDocument/definition`. Use it for the specific reference occurrence,
not the enclosing function's start.

```python
from pathlib import Path
from repository_intelligence.rust_semantic import resolve_definition

result = resolve_definition(
    Path("/path/to/cargo-project"),
    Path("/path/to/cargo-project/src/lib.rs"),
    line=42, column=17,                 # 1-based Unicode-character position
    features=(), no_default_features=False,
    test_mode=False,                   # True when asking about cfg(test) code
    target="aarch64-apple-darwin",     # choose the project's actual target
)
```

The project root must contain `Cargo.toml`; the source must be a Rust file
inside it. Pass the Cargo feature names, default-feature choice, and target
explicitly. `test_mode` defaults to `False` and sets the analyzer's `cfg.setTest`
explicitly; use `True` for references under `cfg(test)`. Result kind
`rust_semantic_definition_v2` identifies this change: v1 inherited
rust-analyzer's test-enabled default and could select a test-only definition for
a normal-source question. V2 also sends `cargo.cfgs: []`, avoiding the
analyzer's implicit `miri` and `debug_assertions` additions while leaving
toolchain-derived cfg values intact. These are analyzer settings, not an exact
compiler-build reproduction: toolchain/environment inputs, `rust_analyzer` cfg,
and sysroot interpretation can still differ. A working local `rust-analyzer` executable is required only for
this call. The result names its analyzer version, configuration, reference
byte hash, local Rust/Cargo-input digest, analyzer workspace status, and each
returned target's URI, range, and byte identity when readable. It says
`resolved` when a target was returned, `unresolved` when none was returned,
and `incomplete_changed_source` if checked local inputs changed during the
question. An analyzer failure raises an exception; it is not an absence proof.
Target bytes are captured before the final local checksum. A local target's
`byte_binding` says `checked_against_final_local_snapshot` only after that
check passes **and** the target path and observed bytes match a file included
in the final snapshot. Project-local targets omitted by the snapshot (for
example under `target/` or through a symlink) remain
`post_analysis_observation`. External or unreadable targets also remain
`post_analysis_observation`: their bytes, if available, are not verified to
match what the analyzer used. A target-byte read failure retains the URI and
range with `source_identity: null` and a `source_identity_error` class name;
it does not discard the resolved location. Required snapshot traversal or
source-read failures instead raise, so missing coverage is not reported as a
complete digest. None of these checks makes the working tree atomic.

The snapshot is a non-atomic checksum of local `.rs` files, Cargo manifests
and lockfiles, Rust toolchain files, and `.cargo` configuration below the
project root. It excludes external dependencies and the sysroot. Build
scripts and procedural macros are disabled for this proof. A resolved target
answers only this reference under this configuration: it does not certify all
build variants, dynamic relationships, generated code, or semantic
completeness of the repository. RI reports evidence; the controller decides
what source to inspect and whether the evidence is enough for a task.

Input positions are 1-based Unicode-character coordinates. Rust native positions
advance the line on LF (including CRLF); a lone CR is whitespace within the line.
The empty final line after a trailing LF is a valid position, while CRLF
terminators are excluded from the preceding line's character count. Returned LSP ranges
use 0-based lines and UTF-16 code-unit columns; convert before treating them as
RI display columns. A returned range can identify only the name of a symbol
(`LocationLink.targetSelectionRange`), not its full declaration or documentation;
inspect the target source to choose a context-page envelope. Retain all returned targets, failures, and unresolved results.

Macro-heavy or build-dependent questions can require the consumer's compiler
and build tools under its normal configuration. This interface does not silently
enable build scripts/procedural macros or resolve every build variant.

For context-page integration, see [Poker's capsule recipe](poker-capsule-workflow.md).
