# Navigation result v1 (retired interim contract)

The shared locator now emits [version 4](navigation-result-v4.md). Version 1
was an interim navigation shape without explicit `excluded` file results or
display columns. Check `schema_version` before consuming either result; do not
reinterpret a version-2 result as version 1.
