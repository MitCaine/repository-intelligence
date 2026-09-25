# Known limitations and outstanding review findings

Baseline: `80d56d9433813a7da8debafb3a3a88b96178695c`, after PR #61. This page distinguishes deliberate limits from four remaining source/logic findings. It does not claim those findings are fixed.

## Deliberate boundaries

Navigation is lexical and bounded; no matches is not proof of absence. Inventories cover the documented source constructs in selected supported files, not the whole compiled program. C/C++ macros, conditionals, includes, and build settings remain unexpanded. Imports, initializers, configuration, enclosing containers, and unsupported files can change behavior without a callable delta. Full changed-file review remains required.

Working-tree reads are non-atomic. `stable=True` is the caller's assertion. Computed hashes are byte identities, not attestation. Anonymous offsets may change after preceding edits; ambiguous named declarations are compared conservatively. Default exclusions are explicit but do not implement `.gitignore` or Git-tracked-file selection.

The 32,000,000-byte acquisition limit and 4,000,000-byte parser limit belong to the shared scanner. Optional native and legacy entry points have separate behavior. Recorded platform verification is limited to the hosts described in [install and verify](install-and-verify.md).

## F01: C++ bodyless handling can hide a nested lambda

In `c_family_tree_index.index_source`, the defaulted/deleted-function branch records the enclosing declaration as bodyless and immediately continues. It does not enqueue its children. A valid example is:

```cpp
struct C { void f(int x = [](){return 1;}()) = delete; };
```

The lambda has a body and belongs to the callable contract even though `f` is deleted. The branch can produce zero promised/mapped/unhandled callables and one bodyless declaration. Keep excluding the enclosing deleted callable, but continue traversing its parameter expressions. Add a test requiring the exact lambda slice and one mapped lambda. Do not rely on the declaration delta alone for this case until corrected.

## F02: C++ declarator traversal assumes a named field

`_name` and `_parameter_identity` follow only `child_by_field_name('declarator')`. In pinned tree-sitter-cpp v0.23.4, a `reference_declarator` contains its next declarator as an unnamed child. Thus `int &get(int &x) { return x; }` reaches an unhandled-name path, while renaming a reference parameter can change its identity key because the local name was not removed.

Use a grammar-aware declarator helper shared by name, terminal-kind, parameter, and signature extraction. Preserve reference shape while omitting local names. Tests should cover reference returns and reference-parameter renames, with additional parenthesized/function-pointer fixtures before claiming those variants work.

## F03: Comments can become identity components

C++, Java, and C# form parameter signatures by iterating every `parameters.named_children`. A standalone named comment extra becomes a separate empty token key instead of being excluded from the parameter list. For example, inserting `/* note */` between two parameters can create a removal/addition rather than a modified declaration with stable identity. C# generic arity also uses `len(type_parameters.named_children)`, which can count a comment as another type parameter.

Select actual parameter/type-parameter node kinds before building the signature. Token-level trivia filtering inside an individual parameter is not sufficient. Test comments both within a parameter and between parameters; expect unchanged identities and changed exact hashes.

## F04: C# constructor kind still depends on annotation text

The conversion-operator fix uses keyword syntax, but constructor classification still checks `b'static' in prefix.split()`. An instance-constructor header with the following attribute text triggers the static branch:

```csharp
class C { [System.Obsolete(" static ")] public C() {} }
```

Select the constructor's actual modifier node/token, not arbitrary header text. Test instance/static constructors with annotations and comments. The annotation should affect the source hash, not manufacture a static-constructor kind.

## Evidence and verification status

The follow-up audit executed the unchanged C++ adapter with manually constructed nodes matching the relevant pinned grammar shapes. Its copied C++ adapter, declaration helper, and source helper were verified against GitHub blob hashes. It also executed the C# header-classification expression and the new Python offset helper, and compiled the C++ and Java source examples. Those are source/logic and compiler checks, not an installed Tree-sitter test run.

The pinned dependencies were unavailable in the audit runtime. Eight proposed integration regressions therefore remain to be run in the repository's pinned environment. PR #61's recorded 139-test pass is separate evidence for its existing suite. In particular, the standalone-comment node placements and full C# examples should be confirmed by those integration tests before closing the corresponding findings. Delete or revise a finding only after reproducing and verifying the relevant behavior, not merely because counters agree.
