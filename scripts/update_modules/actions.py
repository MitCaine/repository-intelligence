"""Refresh SHA-pinned GitHub Actions from their latest stable releases."""

import json
from pathlib import Path
import re
from urllib.request import Request, urlopen


ACTION = re.compile(r'(?m)^(?P<prefix>[ \t]*(?:-[ \t]+)?uses:[ \t]+)(?P<repo>[\w.-]+/[\w.-]+)@'
                    r'(?P<sha>[a-f0-9]{40})(?P<suffix>[ \t]+#[ \t]+)(?P<tag>v\S+)$')


def github(path: str) -> dict:
    request = Request('https://api.github.com/' + path,
                      headers={'Accept': 'application/vnd.github+json',
                               'User-Agent': 'repository-intelligence-updater'})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def release(repo: str) -> tuple[str, str]:
    tag = github(f'repos/{repo}/releases/latest')['tag_name']
    if not re.fullmatch(r'v[0-9][A-Za-z0-9._-]*', tag):
        raise ValueError(f'Unexpected release tag for {repo}: {tag!r}')
    ref = github(f'repos/{repo}/git/ref/tags/{tag}')['object']
    if ref['type'] == 'tag':
        ref = github(f'repos/{repo}/git/tags/{ref["sha"]}')['object']
    if ref['type'] != 'commit' or not re.fullmatch(r'[a-f0-9]{40}', ref['sha']):
        raise ValueError(f'Could not resolve {repo}@{tag} to a commit')
    return tag, ref['sha']


def update(workflows: Path) -> list[str]:
    changes = []
    for path in sorted((*workflows.glob('*.yml'), *workflows.glob('*.yaml'))):
        original = path.read_text(encoding='utf-8')

        def replace(match: re.Match) -> str:
            tag, sha = release(match['repo'])
            if (tag, sha) != (match['tag'], match['sha']):
                changes.append(f'{match["repo"]}: {match["tag"]} -> {tag}')
            return f'{match["prefix"]}{match["repo"]}@{sha}{match["suffix"]}{tag}'

        updated = ACTION.sub(replace, original)
        if updated != original:
            path.write_text(updated, encoding='utf-8')
    return changes
