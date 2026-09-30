"""Independent Markdown and manifest fixtures for the offline docs checker."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('docs_checker', Path(__file__).resolve().parents[1] / 'scripts/check_docs_and_skills.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class DocsCheckerTests(unittest.TestCase):
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
        for value in ('[unterminated', '"unterminated', 'true', '42', 'text: nested'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                checker.scalar_manifest(f'---\nname: fixture\ndescription: {value}\n---\n')
        for value in ('plain description', '"quoted: description"', "'single ''quote''' "):
            # Whitespace after quoted values is outside the deliberately narrow subset.
            if value.endswith(' '):
                value = value.rstrip()
            self.assertIsInstance(checker.scalar_manifest(f'---\nname: fixture\ndescription: {value}\n---\n')['description'], str)

    def test_missing_helper_link(self):
        self.assertIn('missing link', self.fixture('[helper](scripts/missing.py)\n')[0])
