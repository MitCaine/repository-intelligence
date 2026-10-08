"""Independent Markdown and manifest fixtures for the offline docs checker."""
import importlib.util
import ast
from pathlib import Path
import re
import shutil
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('docs_checker', Path(__file__).resolve().parents[1] / 'scripts/check_docs_and_skills.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class DocsCheckerTests(unittest.TestCase):
    def test_complete_skills_relocate_without_missing_resources(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as raw:
            installed = Path(raw) / '.agents' / 'skills'
            shutil.copytree(repo / 'docs' / 'skill-templates', installed)
            # The installation copies folders, not the template index.
            (installed / 'README.md').unlink()
            errors = checker.check(installed)
            self.assertEqual([e for e in errors if e !=
                              'docs/skill-templates: unexpected or missing skill manifests'], [])
            skills = list(installed.glob('*/SKILL.md'))
            self.assertEqual({skill.parent.name for skill in skills}, {
                'capsule-preflight', 'capsule-scope-review', 'capsule-independent-review',
                'capsule-queue', 'ri-evidence-handoff', 'ri-work-kickoff',
                'ri-codex-dispatcher-kickoff'})
            for skill in skills:
                self.assertEqual(checker.scalar_manifest(skill.read_text())['name'],
                                 skill.parent.name)
                locator = skill.parent / 'references' / 'project-procedure.md'
                self.assertTrue(locator.is_file())

    def test_current_documented_contracts_match_source(self):
        repo = Path(__file__).resolve().parents[1]

        def constant(filename, name):
            tree = ast.parse((repo / 'src' / 'repository_intelligence' / filename).read_text())
            return next(ast.literal_eval(node.value) for node in tree.body
                        if isinstance(node, ast.Assign) and any(
                            isinstance(target, ast.Name) and target.id == name
                            for target in node.targets))

        navigation = (repo / 'docs' / 'navigation.md').read_text()
        for field, filename, name in (
                ('schema_version', 'source.py', 'SCHEMA_VERSION'),
                ('inventory_schema_version', 'inventory.py', 'INVENTORY_SCHEMA_VERSION'),
                ('adapter_version', 'structural.py', 'ADAPTER_VERSION')):
            row = next(line for line in navigation.splitlines()
                       if line.startswith('| ') and f'`{field}`' in line)
            value = re.search(r'\| `(\d+)` \|', row)
            self.assertIsNotNone(value)
            self.assertEqual(int(value[1]), constant(filename, name))
        example = (repo / 'docs' / 'consumer-guide.md').read_text()
        values = re.findall(r"assert packet\['schema_version'\] == (\d+)", example)
        self.assertTrue(values)
        self.assertEqual({int(value) for value in values},
                         {constant('source.py', 'SCHEMA_VERSION')})

    def fixture(self, content):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'guide.md').write_text(content)
            return [e for e in checker.check(root) if e.startswith('guide.md:')]

    def test_same_page_fragment(self):
        self.assertEqual(self.fixture('# Guide\n[ok](#guide)\n'), [])
        self.assertIn('missing anchor', self.fixture('# Guide\n[bad](#missing)\n')[0])

    def test_inline_code_heading_keeps_words(self):
        self.assertEqual(self.fixture('# Use `codex queue`\n[ok](guide.md#use-codex-queue)\n'), [])

    def test_reference_links_and_missing_definitions(self):
        for use in ('[bad][target]', '[target][]', '[target]'):
            with self.subTest(use=use):
                self.assertIn('missing link', self.fixture(f'# Guide\n{use}\n[target]: missing.md\n')[0])
        self.assertIn('undefined reference', self.fixture('[text][absent]\n')[0])
        self.assertEqual(self.fixture('# Guide\n[ok][target]\n[target]: #guide\n'), [])

    def test_code_samples_are_not_links(self):
        self.assertEqual(self.fixture('`[bad](missing.md)`\n```md\n[bad](missing.md)\n```\n'), [])

    def test_manifest_rejects_malformed_or_unsupported_yaml(self):
        for value in ('[unterminated', '"unterminated', 'true', '42', 'text: nested',
                      '- foo', '? foo', ':foo', '#foo'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                checker.scalar_manifest(f'---\nname: fixture\ndescription: {value}\n---\n')
        for value in ('plain description', '"quoted: description"', "'single ''quote''' "):
            # Whitespace after quoted values is outside the deliberately narrow subset.
            if value.endswith(' '):
                value = value.rstrip()
            self.assertIsInstance(checker.scalar_manifest(f'---\nname: fixture\ndescription: {value}\n---\n')['description'], str)

    def test_missing_helper_link(self):
        self.assertIn('missing link', self.fixture('[helper](scripts/missing.py)\n')[0])

    def test_duplicate_reference_definition(self):
        self.assertIn('duplicate reference', self.fixture(
            '# Guide\n[ok][target]\n[target]: #guide\n[TARGET]: #guide\n')[0])
