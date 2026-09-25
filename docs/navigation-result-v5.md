# Navigation result v5

The shared locator returns `schema_version: 5`. It retains the [v4 packet
shape and source-level limits](navigation-result-v4.md), but changes the
meaning of some declaration IDs, source ranges, and classifications. Consumers
must not compare v5 records or inventory packets as if they were v4.

Python declarations in supported declared encodings use byte positions from
the actual incremental decoding of the source, not re-encoded text prefixes.
If a codec cannot produce an unambiguous raw character boundary, RI returns an
incomplete mapping. A BOM-only UTF-8 source is valid empty source. C++
function-definition ranges include directly attached chains of template and
friend wrappers, stopping before the containing class or namespace. These
ranges and their hashes remain source-level evidence, not a complete compiler
view.

C++ and C# parameter identity preserves syntax-token boundaries, so tokens
such as `unsigned int` and `unsignedint`, or `ref int` and `refint`, do not
collapse. Java parameter identity omits a varargs local name; members of
local classes inside different overloaded methods inherit an internal owner
discriminator without changing their display names. C++ constructor
function-try-blocks count as implementations; defaulted and deleted function
definitions count as intentionally bodyless. Qualified conversions derive
their kind from the terminal declarator. JavaScript/TypeScript callable export
labels refer to the direct binding, not nested class methods or callbacks;
CommonJS targets match syntax members, not text prefixes; only non-static
class-member `constructor` receives constructor kind. C# conversion labels
come from the actual keyword token.

Non-regular source paths are disclosed without reading. Source acquisition
is bounded at 32 MB; above that bound RI returns `incomplete` without a byte
identity. The 4 MB parser limit is separate: readable regular files between
those bounds keep exact byte identity while their mapping is incomplete.
Optional Python call-name formatting failures retain the raw lexical target.
Coverage rejects duplicate exact ranges, and inventory comparison validates
declaration IDs, hashes, and in-bounds nonempty ranges before comparing.
These checks do not attest to a checkout or replace a full Git changed-file
diff.

Inventory schema 11, mapping contract
`python-rust-javascript-typescript-java-go-csharp-c-cpp-source-callables-v4`,
and adapter version 4 identify this behavior. Compare only matching contracts.
