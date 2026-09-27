"""Find current stable PyPI releases and edit only exact manifest pins."""

import json
from pathlib import Path
import re
from urllib.request import urlopen


PIN = re.compile(r'("(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==)(?P<version>[A-Za-z0-9.!+_-]+)(")')

# 0.26.0 reproducibly crashes the deep-call fixture on macOS Python 3.13.
# Keep the release out of fresh checkout updates; later versions can be tested.
UNSAFE_RELEASES = {'tree-sitter': {'0.26.0'}}


def latest(name: str) -> str:
    with urlopen(f'https://pypi.org/pypi/{name}/json', timeout=15) as response:
        payload = json.load(response)
    version = payload['info']['version']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.!+_-]*', version):
        raise ValueError(f'Unexpected PyPI version for {name}: {version!r}')
    if not any(file['packagetype'] == 'bdist_wheel' and not file.get('yanked')
               for file in payload['urls']):
        raise ValueError(f'Latest {name} {version} has no non-yanked wheel')
    return version


def proposals(path: Path) -> list[tuple[str, str, str]]:
    original = path.read_text(encoding='utf-8')
    if not PIN.search(original):
        raise ValueError('No exact pins found in pyproject.toml')
    return [(match['name'], match['version'], new)
            for match in PIN.finditer(original)
            if (new := latest(match['name'])) != match['version']
            and new not in UNSAFE_RELEASES.get(match['name'], set())]


def set_pin(path: Path, name: str, old: str, new: str) -> None:
    original = path.read_text(encoding='utf-8')
    needle = f'"{name}=={old}"'
    if original.count(needle) != 1:
        raise ValueError(f'Expected one current pin for {name}=={old}')
    path.write_text(original.replace(needle, f'"{name}=={new}"'), encoding='utf-8')
