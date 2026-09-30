"""Check local Markdown links and the documented scalar-only skill manifests."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'(?<!!)\[[^\]]+\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)')
REFERENCE = re.compile(r'^\s*\[([^\]]+)\]:\s*(<[^>]+>|\S+)')
REFERENCE_USE = re.compile(r'(?<!!)\[([^\]]+)\](?:\[([^\]]*)\])?')
HEADING = re.compile(r'^#{1,6}\s+(.+?)\s*#*\s*$')


def visible_lines(content):
    lines, fence = [], None
    for line in content.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return lines


def anchors(path):
    found = set()
    for line in visible_lines(path.read_text(encoding='utf-8')):
        heading = HEADING.match(line)
        if heading:
            text = re.sub(r'!?\[([^\]]+)\]\([^)]*\)', r'\1', heading[1])
            slug = re.sub(r'[^\w -]', '', text.lower()).strip().replace(' ', '-')
            candidate, suffix = slug, 1
            while candidate in found:
                candidate = f'{slug}-{suffix}'
                suffix += 1
            found.add(candidate)
    return found


def scalar_manifest(content):
    """Parse our strict YAML subset: unique top-level name/description strings."""
    match = re.match(r'\A---\n(.*?)\n---\n', content, re.S)
    if not match:
        raise ValueError('missing YAML frontmatter')
    fields = {}
    for line in match[1].splitlines():
        row = re.fullmatch(r'(name|description):[ \t]+(.+)', line)
        if not row or row[1] in fields:
            raise ValueError('manifest requires unique name/description scalar lines')
        value = row[2]
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except ValueError as error:
                raise ValueError('invalid quoted manifest scalar') from error
        elif value.startswith("'"):
            if not re.fullmatch(r"'(?:[^']|'')*'", value):
                raise ValueError('invalid quoted manifest scalar')
            value = value[1:-1].replace("''", "'")
        elif value[0] in '[]{}&*!|>@`%' or re.search(r':\s|\s#', value) or value.lower() in {
                'null', '~', 'true', 'false', 'yes', 'no', 'on', 'off'} or re.fullmatch(r'[-+]?\d+(?:\.\d+)?', value):
            raise ValueError('unsupported manifest scalar; use a quoted string')
        if not isinstance(value, str) or not value.strip():
            raise ValueError('empty or nonstring manifest scalar')
        fields[row[1]] = value
    if set(fields) != {'name', 'description'}:
        raise ValueError('manifest requires name and description')
    return fields


def check(root=ROOT):
    errors = []
    for path in sorted(root.rglob('*.md')):
        if any(part.startswith('.') for part in path.relative_to(root).parts):
            continue
        lines = visible_lines(path.read_text(encoding='utf-8'))
        references = {m[1].strip().casefold(): m[2] for line in lines
                      if (m := REFERENCE.match(line))}
        targets = list(references.values())
        for line in lines:
            if REFERENCE.match(line):
                continue
            line = re.sub(r'`+[^`]*`+', '', line)
            targets.extend(m[1] for m in LINK.finditer(line))
            # Remove inline links before recognizing full, collapsed, shortcut references.
            line = LINK.sub('', line)
            for m in REFERENCE_USE.finditer(line):
                label = (m[2] or m[1]).strip().casefold()
                if label in references:
                    targets.append(references[label])
                elif m[2] is not None:
                    errors.append(f'{path.relative_to(root)}: undefined reference {label}')
        for target in targets:
            target = target.strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith('//'):
                continue
            destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path.resolve()
            if not destination.is_relative_to(root.resolve()) or not destination.exists():
                errors.append(f'{path.relative_to(root)}: missing link {target}')
            elif parsed.fragment and destination.suffix == '.md' and unquote(parsed.fragment) not in anchors(destination):
                errors.append(f'{path.relative_to(root)}: missing anchor {target}')
    skills = root / 'docs' / 'skill-templates'
    for path in sorted(skills.glob('*/SKILL.md')):
        try:
            fields = scalar_manifest(path.read_text(encoding='utf-8'))
            if fields['name'] != path.parent.name:
                raise ValueError('name must match skill folder')
        except ValueError as error:
            errors.append(f'{path.relative_to(root)}: {error}')
    expected = {'capsule-preflight', 'capsule-scope-review', 'capsule-independent-review',
                'capsule-queue', 'ri-evidence-handoff'}
    if {p.parent.name for p in skills.glob('*/SKILL.md')} != expected:
        errors.append('docs/skill-templates: unexpected or missing skill manifests')
    return errors


if __name__ == '__main__':
    failures = check()
    if failures:
        raise SystemExit('\n'.join(failures))
    print('Documentation links and five skill manifests: OK')
