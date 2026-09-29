"""Pinned JS/TS/TSX callable contract and source-byte fixtures."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import index_file, query_path


class JavaScriptTypeScriptTests(unittest.TestCase):
    def test_static_and_instance_methods_have_distinct_identity(self):
        source = b"class C { run() {return 1;} static run() {return 2;} }"
        for suffix in (".js", ".ts"):
            with self.subTest(suffix=suffix):
                entries = [entry for entry in self._index(suffix, source)["functions"]
                           if entry["name"] == "run"]
                self.assertEqual(len(entries), 2)
                self.assertFalse(any(entry["identity_ambiguous"] for entry in entries))
                self.assertEqual(len({entry["declaration_id"] for entry in entries}), 2)
                with tempfile.TemporaryDirectory() as raw:
                    left, right = Path(raw) / "left", Path(raw) / "right"
                    left.mkdir(); right.mkdir()
                    (left / f"f{suffix}").write_bytes(source)
                    (right / f"f{suffix}").write_bytes(b"// unrelated\n" + source)
                    changes = compare_inventories(inventory_tree(left, stable=True),
                                                  inventory_tree(right, stable=True))["declaration_changes"]
                    self.assertEqual(tuple(len(changes[key]) for key in
                                           ("added", "removed", "modified", "unchanged")),
                                     (0, 0, 0, 2))

    def test_class_field_arrow_binding_in_js_and_ts(self):
        source = b"class Worker { reconcileInvoices = () => 1; }"
        for suffix in (".js", ".ts"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as raw:
                path = Path(raw) / f"worker{suffix}"
                path.write_bytes(source)
                result = index_file(path)
                self.assertEqual(result["function_count"], 1)
                self.assertEqual(result["functions"][0]["qualified_name"],
                                 "Worker.reconcileInvoices")
                self.assertEqual(len(query_path(path, "reconcile invoices")["matches"]), 1)

    def test_nested_object_in_class_field_preserves_owner(self):
        source = b"class Worker { api = { reconcileInvoices: () => 1 }; }"
        for suffix in (".js", ".ts"):
            with self.subTest(suffix=suffix):
                entries = self._index(suffix, source)["functions"]
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["qualified_name"],
                                 "Worker.api.reconcileInvoices")

    def test_export_is_direct_and_commonjs_target_is_exact(self):
        source = (b"export class C { run() {} }\n"
                  b"export const n = register(() => 1);\n"
                  b"module.exportsBackup = function backup() {};\n"
                  b"module.exports = function direct() {};\n")
        indexed = self._index(".js", source)
        by_name = {entry["name"]: entry for entry in indexed["functions"]}
        self.assertIsNone(by_name["run"]["export_kind"])
        callback = next(entry for entry in indexed["functions"]
                        if entry["syntax_kind"] == "arrow_function")
        self.assertIsNone(callback["export_kind"])
        self.assertIsNone(by_name["backup"]["export_kind"])
        self.assertEqual(by_name["direct"]["export_kind"], "commonjs")
        self.assertEqual([item["kind"] for item in indexed["module_bindings"]["exports"]],
                         ["named", "named", "commonjs"])

    def test_constructor_kind_requires_nonstatic_class_member(self):
        source = (b"const obj = { constructor() {} };\n"
                  b"class C { static constructor() {} constructor() {} }\n")
        entries = [entry for entry in self._index(".js", source)["functions"]
                   if entry["name"] == "constructor"]
        self.assertEqual([entry["declaration_kind"] for entry in entries],
                         ["method", "method", "constructor"])

    def test_named_expression_keeps_external_binding_searchable_once(self):
        for suffix in (".js", ".ts"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as raw:
                source = (b"const locateInvoice = function worker(x: number) { return x; };\n"
                          if suffix == ".ts" else
                          b"const locateInvoice = function worker() { return 1; };\n")
                path = Path(raw) / f"fixture{suffix}"
                path.write_bytes(source)
                indexed = index_file(path)
                self.assertEqual(indexed["function_count"], 1)
                entry = indexed["functions"][0]
                self.assertEqual(entry["qualified_name"], "worker")
                self.assertEqual(entry["binding_aliases"], ["locateInvoice"])
                self.assertEqual(entry["byte_range"],
                                 {"start": source.index(b"function"), "end": source.index(b"}") + 1})
                self.assertEqual(query_path(path, "locate invoice")["matches"][0]["name"],
                                 "worker")
                self._exact(indexed, source)

    def test_nested_callable_does_not_inherit_outer_export(self):
        for suffix in (".js", ".ts"):
            with self.subTest(suffix=suffix):
                source = (b"export function outer() { function helper() {} return helper; }\n"
                          b"export default function directDefault() {}\n"
                          b"exports.direct = function directWorker() {};\n")
                indexed = self._index(suffix, source)
                by_name = {entry["qualified_name"]: entry for entry in indexed["functions"]}
                self.assertEqual(len(by_name), 4)
                self.assertEqual(by_name["outer"]["export_kind"], "named")
                self.assertIsNone(by_name["outer.helper"]["export_kind"])
                self.assertEqual(by_name["directDefault"]["export_kind"], "default")
                self.assertEqual(by_name["directWorker"]["export_kind"], "commonjs")
                self._exact(indexed, source)

    def test_nearby_comment_terms_find_opaque_method_name(self):
        source = b"// Reconcile overdue invoices.\nfunction run(){}\n"
        result = self._index(".ts", source)
        self.assertIn("overdue invoices", result["functions"][0]["docs"])
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.ts"
            path.write_bytes(source)
            self.assertEqual(query_path(path, "overdue invoices")["matches"][0]["name"], "run")
    def test_nested_owners_and_static_accessors(self):
        source = (b"class C { first(){ function helper(){} } second(){ function helper(){} }\n"
                  b"static get value(){return 1} static set value(v){} }\n"
                  b"const left = () => { function helper(){} };\n"
                  b"const right = () => { function helper(){} };\n")
        result = self._index(".ts", source)
        by_name = {(entry["qualified_name"], entry["declaration_kind"])
                   for entry in result["functions"]}
        self.assertIn(("C.first.helper", "function"), by_name)
        self.assertIn(("C.second.helper", "function"), by_name)
        self.assertIn(("left.helper", "function"), by_name)
        self.assertIn(("right.helper", "function"), by_name)
        self.assertIn(("C.value", "getter"), by_name)
        self.assertIn(("C.value", "setter"), by_name)
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
            self.assertEqual(before["inventory_schema_version"], 14)
            self.assertEqual(before["scope"]["extensions"],
                             [".c", ".cc", ".cjs", ".cpp", ".cs", ".cts", ".cxx", ".go", ".hh", ".hpp", ".hxx", ".java", ".js", ".jsx", ".md", ".mjs", ".mts", ".py", ".rs", ".ts", ".tsx"])
            delta = compare_inventories(before, after)
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual(len(delta["declaration_changes"]["modified"]), 1)


if __name__ == "__main__":
    unittest.main()
