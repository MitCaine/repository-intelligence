"""Check local Markdown links and portable skill manifests without network access."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'(?<!!)\[[^\]]+\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)')
HEADING = re.compile(r'^#{1,6}\s+(.+?)\s*#*\s*$')


def visible_lines(content: str) -> list[str]:
    lines = []
    fence = None
    for line in content.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            if fence is None:
                fence = marker.group(1)[0]
            elif marker.group(1)[0] == fence:
                fence = None
            continue
        if fence is None:
            lines.append(re.sub(r'`[^`]*`', '', line))
    return lines


def anchors(path: Path) -> set[str]:
    found = set()
    for line in visible_lines(path.read_text(encoding='utf-8')):
        heading = HEADING.match(line)
        if heading:
            slug = re.sub(r'[^\w -]', '', heading.group(1).lower()).strip().replace(' ', '-')
            candidate = slug
            suffix = 1
            while candidate in found:
                candidate = f'{slug}-{suffix}'
                suffix += 1
            found.add(candidate)
    return found


def check(root: Path = ROOT) -> list[str]:
    errors = []
    for path in sorted(root.rglob('*.md')):
        if any(part.startswith('.') for part in path.relative_to(root).parts):
            continue
        for line in visible_lines(path.read_text(encoding='utf-8')):
            for match in LINK.finditer(line):
                target = match.group(1).strip('<>')
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith(('#', 'mailto:')) or target.startswith('//'):
                    continue
                destination = (path.parent / unquote(parsed.path)).resolve()
                if not destination.is_relative_to(root.resolve()) or not destination.exists():
                    errors.append(f'{path.relative_to(root)}: missing link {target}')
                elif parsed.fragment and destination.suffix == '.md' and unquote(parsed.fragment) not in anchors(destination):
                    errors.append(f'{path.relative_to(root)}: missing anchor {target}')
    skills = root / 'docs' / 'skill-templates'
    for path in sorted(skills.glob('*/SKILL.md')):
        content = path.read_text(encoding='utf-8')
        match = re.match(r'\A---\n(.*?)\n---\n', content, re.S)
        if not match:
            errors.append(f'{path.relative_to(root)}: missing YAML frontmatter')
            continue
        fields = dict(re.findall(r'^([a-z_]+):\s*(.+)$', match.group(1), re.M))
        if fields.get('name') != path.parent.name:
            errors.append(f'{path.relative_to(root)}: name must match skill folder')
        if not fields.get('description', '').strip():
            errors.append(f'{path.relative_to(root)}: missing description')
    if len(list(skills.glob('*/SKILL.md'))) != 4:
        errors.append('docs/skill-templates: expected four skill manifests')
    return errors


if __name__ == '__main__':
    failures = check()
    if failures:
        raise SystemExit('\n'.join(failures))
    print('Documentation links and four skill manifests: OK')
