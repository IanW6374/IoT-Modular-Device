"""Apply project-owned patches only for the duration of a pinned core build."""

import subprocess
from pathlib import Path


def _git(root, *arguments):
    subprocess.run(['git', *arguments], cwd=root, check=True, capture_output=True)


def restore_core_patches(root, applied):
    for patch in reversed(applied):
        # Never reset or overwrite unrelated developer changes.
        _git(root, 'apply', '--reverse', '--check', str(patch))
        _git(root, 'apply', '--reverse', str(patch))


def apply_core_patches(root, patches):
    patches = [Path(path).resolve() for path in patches]
    # Validate every patch before changing any tracked source.
    for patch in patches:
        _git(root, 'apply', '--check', str(patch))
    applied = []
    try:
        for patch in patches:
            _git(root, 'apply', str(patch))
            applied.append(patch)
    except BaseException:
        restore_core_patches(root, applied)
        raise
    return applied
