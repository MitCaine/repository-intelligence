"""Keep the project interpreter discoverable by VS Code and Codex."""

import json
from pathlib import Path


def configure(root: Path) -> None:
    settings_path = root / '.vscode' / 'settings.json'
    settings_path.parent.mkdir(exist_ok=True)
    settings = json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.exists() else {}
    settings['python.defaultInterpreterPath'] = '${workspaceFolder}/.venv/bin/python'
    settings_path.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
