"""Propose and edit exact package pins declared by the TOML manifest."""

import json
from pathlib import Path
import re
from urllib.request import urlopen

import maintain


PIN = re.compile(r'([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9.!+_-]+)')
STABLE_VERSION = re.compile(r'(?:(\d+)!)?(\d+(?:\.\d+)*)(?:\.post(\d+))?')
TABLE = re.compile(r'^[ \t]*\[([^\]]+)\][ \t]*(?:#.*)?$', re.M)
FIELD = {'build-system': 'requires', 'project': 'dependencies'}

# 0.26.0 reproducibly crashes the deep-call fixture on macOS Python 3.13.
UNSAFE_RELEASES = {'tree-sitter': {'0.26.0'}}


def normalize(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def stable_key(version: str) -> tuple[int, tuple[int, ...], int]:
    match = STABLE_VERSION.fullmatch(version)
    if match is None:
        raise ValueError(f'Cannot compare non-stable package version: {version!r}')
    release = tuple(int(item) for item in match[2].split('.'))
    return int(match[1] or 0), release, int(match[3]) if match[3] is not None else -1


def is_newer(new: str, old: str) -> bool:
    newer, older = stable_key(new), stable_key(old)
    length = max(len(newer[1]), len(older[1]))
    return (newer[0], newer[1] + (0,) * (length - len(newer[1])), newer[2]) > (
        older[0], older[1] + (0,) * (length - len(older[1])), older[2])


def pin_spans(source: str) -> list[tuple[int, int, str, str]]:
    """Locate only quoted requirements in the two maintained TOML arrays."""
    spans = []
    tables = list(TABLE.finditer(source))
    for index, table in enumerate(tables):
        if table.group(1) not in FIELD:
            continue
        end = tables[index + 1].start() if index + 1 < len(tables) else len(source)
        field = FIELD[table.group(1)]
        match = re.search(rf'(?m)^[ \t]*{field}[ \t]*=[ \t]*\[',
                          source[table.end():end])
        if match is None:
            continue
        pos = table.end() + match.end()
        while pos < end:
            char = source[pos]
            if char == '#':
                newline = source.find('\n', pos, end)
                pos = end if newline < 0 else newline + 1
            elif char == ']':
                break
            elif char in ('"', "'"):
                start = pos + 1
                close = source.find(char, start, end)
                if close < 0:
                    raise ValueError(f'Unterminated {field} requirement')
                requirement = source[start:close]
                pin = PIN.fullmatch(requirement)
                if pin is None:
                    raise ValueError(f'Expected an exact pin in {field}: {requirement!r}')
                spans.append((start, close, normalize(pin[1]), pin[2]))
                pos = close + 1
            else:
                pos += 1
    return spans


def latest(name: str) -> str:
    with urlopen(f'https://pypi.org/pypi/{name}/json', timeout=15) as response:
        payload = json.load(response)
    version = payload['info']['version']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.!+_-]*', version):
        raise ValueError(f'Unexpected PyPI version for {name}: {version!r}')
    stable_key(version)
    if not any(file['packagetype'] == 'bdist_wheel' and not file.get('yanked')
               for file in payload['urls']):
        raise ValueError(f'Latest {name} {version} has no non-yanked wheel')
    return version


def proposals(path: Path) -> list[tuple[str, str, str]]:
    pins = maintain.load_pins(path)
    selected = pins['build'] | pins['runtime']
    if not selected:
        raise ValueError('No exact pins found in pyproject.toml')
    spans = pin_spans(path.read_text(encoding='utf-8'))
    if {name for _, _, name, _ in spans} != set(selected):
        raise ValueError('Could not locate every declared package pin')
    result = []
    for name, old in selected.items():
        new = latest(name)
        if is_newer(new, old) and new not in UNSAFE_RELEASES.get(name, set()):
            result.append((name, old, new))
    return result


def set_pin(path: Path, name: str, old: str, new: str) -> None:
    maintain.load_pins(path)
    source = path.read_text(encoding='utf-8')
    normalized = normalize(name)
    matches = [(start, end) for start, end, pin_name, version in pin_spans(source)
               if pin_name == normalized and version == old]
    if not matches:
        raise ValueError(f'Expected a current pin for {name}=={old}')
    for start, end in reversed(matches):
        raw_name = PIN.fullmatch(source[start:end])[1]
        source = source[:start] + f'{raw_name}=={new}' + source[end:]
    path.write_text(source, encoding='utf-8')
    maintain.load_pins(path)
