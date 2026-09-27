"""Refresh optional rustup tools when requested."""

import shutil
import subprocess


def update() -> None:
    rustup = shutil.which('rustup')
    if rustup is None:
        print('Native tools skipped: rustup is unavailable')
        return
    subprocess.run([rustup, 'update', 'stable'], check=True, timeout=900)
    subprocess.run([rustup, 'component', 'add', '--toolchain', 'stable',
                    'rust-analyzer', 'rust-src'], check=True, timeout=300)
