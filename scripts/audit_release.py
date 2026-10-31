"""Check the tracked release tree for accidental secrets, local paths and large files.

Run after git add. This is a release guard, not a complete security audit.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AIza[A-Za-z0-9_-]{30,}|sk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
LOCAL = re.compile(rb'(?:/(?:home)/[^/\s]+/|C:\\Users\\|Desktop[/\\]Workspace)')
ALLOWED_MEDIA = {'docs/preview.jpg', 'docs/preview.gif'}


def main():
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    errors = []
    for name in filter(None, paths):
        path = ROOT / name
        if path.is_symlink():
            errors.append(f'{name}: symlink')
            continue
        # Scan the staged bytes that will actually be committed.
        data = subprocess.check_output(['git', 'show', ':' + name], cwd=ROOT)
        if any(part in {'node_modules', '__pycache__', '.venv'} for part in path.parts):
            errors.append(f'{name}: local dependency/cache')
        if (path.name == '.env' or path.name.startswith('.env.')) and path.name != '.env.example':
            errors.append(f'{name}: environment file')
        if len(data) > 5_000_000:
            errors.append(f'{name}: over 5 MB')
        if path.suffix.lower() in {'.mp4', '.mp3', '.wav', '.png', '.jpg', '.gif', '.webm', '.ttf', '.woff2'} and name not in ALLOWED_MEDIA:
            errors.append(f'{name}: media missing from the audited release allowlist')
        if SECRET.search(data):
            errors.append(f'{name}: possible credential (value withheld)')
        if LOCAL.search(data):
            errors.append(f'{name}: machine-specific path')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'Release guard passed for {len(list(filter(None, paths)))} tracked files. Also review provenance and git history before publishing.')


if __name__ == '__main__':
    main()
