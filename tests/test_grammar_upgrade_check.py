"""Offline regression checks for the optional maintainer grammar review tool."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import runpy
import tempfile
import unittest

from repository_intelligence.structural import GRAMMARS


ROOT = Path(__file__).resolve().parents[1]
CHECK = runpy.run_path(str(ROOT / "scripts" / "check_grammar_nodes.py"))


def matching_nodes(language):
    """Supply the review tool's input shape; this is not a grammar correctness oracle."""
    return [{"type": kind, "named": True,
             "fields": {field: {"required": required}
                        for field, required in fields.items()}}
            for kind, fields in CHECK["EXPECTED"][language].items()]


class GrammarUpgradeCheckTests(unittest.TestCase):
    def test_every_shipped_parser_variant_has_a_review_contract_and_source(self):
        names = {"Python": "python", "Rust": "rust", "JavaScript": "javascript",
                 "TypeScript": "typescript", "TSX": "tsx", "Java": "java",
                 "Go": "go", "CSharp": "c-sharp", "C": "c", "C++": "cpp",
                 "Markdown": "markdown"}
        shipped = {names[name] for name, _, _ in GRAMMARS.values()}
        self.assertEqual(set(CHECK["EXPECTED"]), shipped)
        self.assertEqual(set(CHECK["SOURCES"]), shipped)
        for name, distribution, _ in GRAMMARS.values():
            self.assertEqual(CHECK["SOURCES"][names[name]][0], distribution)

    def test_matching_selected_shapes_pass_for_each_variant(self):
        for language in CHECK["EXPECTED"]:
            with self.subTest(language=language):
                self.assertEqual(CHECK["check"](language, matching_nodes(language)), [])

    def test_missing_optional_field_is_drift_not_an_absent_value(self):
        nodes = matching_nodes("go")
        function = next(node for node in nodes if node["type"] == "function_declaration")
        del function["fields"]["body"]
        self.assertEqual(CHECK["check"]("go", nodes),
                         ["go: function_declaration missing field body"])

    def test_body_requiredness_changes_fail_both_directions(self):
        cases = (("rust", "function_item", False),
                 ("c-sharp", "method_declaration", True),
                 ("cpp", "function_definition", True))
        for language, kind, changed in cases:
            with self.subTest(language=language):
                nodes = matching_nodes(language)
                node = next(node for node in nodes if node["type"] == kind)
                node["fields"]["body"]["required"] = changed
                self.assertEqual(CHECK["check"](language, nodes),
                                 [f"{language}: {kind}.body requiredness changed"])

    def test_unnamed_node_cannot_replace_a_named_declaration(self):
        nodes = matching_nodes("java")
        next(node for node in nodes if node["type"] == "compact_constructor_declaration")["named"] = False
        self.assertEqual(CHECK["check"]("java", nodes),
                         ["java: missing named node compact_constructor_declaration"])

    def test_no_field_contract_still_requires_the_node(self):
        nodes = [node for node in matching_nodes("cpp")
                 if node["type"] != "reference_declarator"]
        self.assertEqual(CHECK["check"]("cpp", nodes),
                         ["cpp: missing named node reference_declarator"])

    def test_source_urls_follow_project_pins_and_preserve_tsx_path(self):
        original = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "pyproject.toml"
            old = next(value for value in CHECK["source_urls"]().values()
                       if "/tree-sitter-typescript/" in value).split("/v")[1].split("/")[0]
            project.write_text(original.replace(f"tree-sitter-typescript=={old}",
                                                "tree-sitter-typescript==99.1.2"), encoding="utf-8")
            urls = CHECK["source_urls"](project)
        self.assertEqual(urls["typescript"], "https://raw.githubusercontent.com/tree-sitter/"
                         "tree-sitter-typescript/v99.1.2/typescript/src/node-types.json")
        self.assertEqual(urls["tsx"], "https://raw.githubusercontent.com/tree-sitter/"
                         "tree-sitter-typescript/v99.1.2/tsx/src/node-types.json")

    def test_non_exact_grammar_pin_has_no_guessed_upstream_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "pyproject.toml"
            project.write_text('[project]\ndependencies = ["tree-sitter-python>=0.25"]\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "tree-sitter-python needs an exact pin"):
                CHECK["source_urls"](project)

    def test_cli_reports_only_checked_languages_and_retains_legacy_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = []
            for language in ("python", "rust"):
                path = Path(temporary) / f"{language}.json"
                path.write_text(json.dumps(matching_nodes(language)), encoding="utf-8")
                paths.append(str(path))
            for arguments, languages in ((paths, "python, rust"), (["python=" + paths[0]], "python")):
                output = StringIO()
                with redirect_stdout(output):
                    status = CHECK["main"](arguments)
                self.assertEqual(status, 0)
                self.assertIn("Checked node/field assumptions: " + languages, output.getvalue())
                self.assertIn("not a coverage proof", output.getvalue())

    def test_cli_require_all_rejects_missing_tsx_and_duplicate_language(self):
        for args, message in ((["--require-all", "python=missing.json"], "tsx"),
                              (["python=one.json", "python=two.json"], "duplicate language: python")):
            with self.subTest(arguments=args):
                output = StringIO()
                with redirect_stderr(output), self.assertRaises(SystemExit) as error:
                    CHECK["main"](args)
                self.assertEqual(error.exception.code, 2)
                self.assertIn(message, output.getvalue())

    def test_cli_bad_input_reports_failure_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nodes.json"
            for content in ("{broken", '{"type":"function_item"}', '[null]'):
                with self.subTest(content=content):
                    path.write_text(content, encoding="utf-8")
                    output = StringIO()
                    with redirect_stdout(output):
                        status = CHECK["main"]([f"rust={path}"])
                    self.assertEqual(status, 1)
                    self.assertIn("rust:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
