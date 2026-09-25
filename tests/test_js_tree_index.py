"""Pinned JS/TS/TSX callable contract and source-byte fixtures."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import index_file, query_path


class JavaScriptTypeScriptTests(unittest.TestCase):
    def _index(self, suffix: str, source: bytes) -> dict:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / f"fixture{suffix}"
            path.write_bytes(source)
            return index_file(path)

    def _exact(self, result: dict, source: bytes) -> None:
        ids = set()
        for entry in result["functions"]:
            self.assertNotIn(entry["declaration_id"], ids)
            ids.add(entry["declaration_id"])
            span = entry["byte_range"]
            self.assertEqual(entry["declaration_sha256"], hashlib.sha256(
                source[span["start"]:span["end"]]).hexdigest())
        coverage = result["adapter_coverage"]
        self.assertEqual(coverage["promised_node_count"],
                         coverage["mapped_node_count"] + coverage["unhandled_node_count"])
        self.assertEqual(coverage["mapped_node_count"], len(ids))
        self.assertEqual(result["structural"]["declaration_count"],
                         coverage["promised_node_count"])

    def test_js_exports_methods_accessors_object_functions_and_callbacks(self):
        source = ("import helper from 'pkg';\n"
                  "export default function() { return helper(); }\n"
                  "export const run = async (x) => x;\n"
                  "class Café { constructor(){} get value(){return 1} set value(v){} method(){} }\n"
                  "const obj = { run(){}, f: function(){}, g: (x) => x };\n"
                  "callback(function(){}, x => x);\n").encode("utf-8")
        result = self._index(".js", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["function_count"], 11)
        self.assertEqual(result["module_bindings"]["imports"][0]["source"], "'pkg'")
        self.assertEqual([item["kind"] for item in result["module_bindings"]["exports"]],
                         ["default", "named"])
        by_name = {entry["qualified_name"]: entry for entry in result["functions"]}
        self.assertIn("Café.constructor", by_name)
        self.assertIn("obj.f", by_name)
        self.assertEqual(by_name["Café.constructor"]["declaration_kind"], "constructor")
        accessors = [entry for entry in result["functions"] if entry["qualified_name"] == "Café.value"]
        self.assertEqual({entry["declaration_kind"] for entry in accessors}, {"getter", "setter"})
        self.assertEqual(len({entry["declaration_id"] for entry in accessors}), 2)
        self.assertEqual(len([entry for entry in result["functions"] if entry["anonymous"]]), 3)
        self._exact(result, source)

    def test_js_extension_aliases_and_nested_generator(self):
        source = b"function* stream(){ function local(){} return () => local(); }\n"
        for suffix in (".js", ".jsx", ".mjs", ".cjs"):
            with self.subTest(suffix=suffix):
                result = self._index(suffix, source)
                self.assertEqual(result["mapping_status"], "navigation_only")
                self.assertEqual(result["function_count"], 3)
                self.assertIn("stream.local", {item["qualified_name"]
                                               for item in result["functions"]})
                self._exact(result, source)

    def test_typescript_namespace_and_commonjs_export_ownership(self):
        namespace = (b"namespace N { export function f(){} "
                     b"export namespace M { export const g = () => 1; } }\n")
        result = self._index(".ts", namespace)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual({entry["qualified_name"] for entry in result["functions"]},
                         {"N.f", "N.M.g"})
        self.assertEqual([entry["owner"] for entry in result["module_bindings"]["exports"]],
                         ["N", "N", "N.M"])
        self._exact(result, namespace)
        commonjs = b"module.exports = function(){}; exports.run = () => 1;\n"
        result = self._index(".cjs", commonjs)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual({entry["name"] for entry in result["functions"]},
                         {"module.exports", "exports.run"})
        self.assertEqual({item["kind"] for item in result["module_bindings"]["exports"]},
                         {"commonjs"})
        self._exact(result, commonjs)

    def test_class_field_ambient_and_merged_declarations(self):
        source = (b"declare function load(x: number): void;\n"
                  b"interface M { run(): void }\n"
                  b"namespace M { export function run(){} }\n"
                  b"class C { field = () => 1; }\n"
                  b"export { run as renamed } from 'pkg';\n")
        result = self._index(".ts", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["adapter_coverage"]["bodyless_excluded_count"], 2)
        self.assertEqual({entry["qualified_name"] for entry in result["functions"]},
                         {"M.run", "C.field"})
        exports = result["module_bindings"]["exports"]
        self.assertEqual([(item["owner"], item["source"]) for item in exports],
                         [("M", None), (None, "'pkg'")])
        self._exact(result, source)

    def test_merged_namespaces_keep_distinct_callable_identities(self):
        source = (b"namespace M { export function f(){} }\n"
                  b"namespace M { export function f(){} }\n"
                  b"export async function* stream(){ yield 1; }\n")
        result = self._index(".ts", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual([item["qualified_name"] for item in result["functions"]],
                         ["M.f", "M.f", "stream"])
        self.assertEqual(len({item["declaration_id"] for item in result["functions"]}), 3)
        self._exact(result, source)

    def test_typescript_bodyless_overloads_interface_abstract_and_default_arrow(self):
        source = (b"export interface I { run(x: number): void; get value(): number }\n"
                  b"abstract class A { abstract run(): void; method(){} }\n"
                  b"function f(x: string): string; function f(x: number): number;\n"
                  b"function f(x: any) { return x; }\n"
                  b"export default (x: number) => x;\n")
        result = self._index(".ts", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["adapter_coverage"]["bodyless_excluded_count"], 5)
        self.assertEqual(result["function_count"], 3)
        self.assertEqual({item["name"] for item in result["functions"] if not item["anonymous"]},
                         {"method", "f"})
        self.assertEqual(len(result["bodyless_declarations"]), 5)
        self._exact(result, source)

    def test_tsx_and_incomplete_syntax(self):
        tsx = b"export const View = (p: Props) => <div>{p.name}</div>;\n"
        result = self._index(".tsx", tsx)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["functions"][0]["name"], "View")
        self._exact(result, tsx)
        for suffix, source, kind in (
            (".js", b"function good() {}\nfunction bad(\n", "ERROR"),
            (".js", b"function f(){ return (1 + 2; }", "MISSING"),
            (".ts", b"function f(x: number): string { return x;", "MISSING"),
            (".tsx", b"const C = () => <div></div", "ERROR"),
        ):
            with self.subTest(suffix=suffix, kind=kind):
                incomplete = self._index(suffix, source)
                self.assertEqual(incomplete["mapping_status"], "incomplete")
                self.assertIn(kind, {item["kind"] for item in
                                     incomplete["structural"]["diagnostics"]})

    def test_js_inventory_delta_and_query(self):
        with tempfile.TemporaryDirectory() as raw:
            p, c = (Path(raw) / name for name in ("planning", "candidate"))
            p.mkdir()
            c.mkdir()
            (p / "main.ts").write_text("export function total(){ return 1; }\n")
            (c / "main.ts").write_text("export function total(){ return 2; }\n")
            self.assertEqual(query_path(c / "main.ts", "total")["matches"][0]["name"], "total")
            before, after = inventory_tree(p, stable=True), inventory_tree(c, stable=True)
            self.assertEqual(before["inventory_schema_version"], 4)
            self.assertEqual(before["scope"]["extensions"],
                             [".cjs", ".go", ".java", ".js", ".jsx", ".mjs", ".py", ".rs", ".ts", ".tsx"])
            delta = compare_inventories(before, after)
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual(len(delta["declaration_changes"]["modified"]), 1)


if __name__ == "__main__":
    unittest.main()
