"""The shipped source adapters, selected by explicit file suffix."""

from . import (c_family_tree_index, csharp_tree_index, go_tree_index, java_tree_index,
               js_tree_index, python_tree_index, rust_tree_index)


PARSERS = {".py": python_tree_index.index_source, ".rs": rust_tree_index.index_source,
           ".java": java_tree_index.index_source,
           ".go": go_tree_index.index_source,
           ".cs": csharp_tree_index.index_source,
           **{suffix: c_family_tree_index.index_source for suffix in
              (".c", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx")},
           **{suffix: js_tree_index.index_source for suffix in
              (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")}}
