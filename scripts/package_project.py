"""Package source, public verification evidence and demos; exclude keys and dependencies."""
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / 'proof-of-hunt-verified.zip'
excluded_parts = {'private', 'node_modules', '__pycache__', '.git', '.codex', '.agents', 'rendered', 'dist'}
excluded_names = {'.DS_Store', 'ollama-native-server.log', 'ollama-native-install.log',
                  'ollama-pull.log', 'ollama-14b-pull.log', 'studio-start.log', 'web-server.log'}
files = [root / n for n in ('README.md', 'RUN.md', '.gitignore', '.vercelignore', 'vercel.json')]
for directory in ('.github', 'contracts', 'clues', 'scripts', 'web', 'video', 'verification'):
    for file in (root / directory).rglob('*'):
        rel = file.relative_to(root)
        if not file.is_file() or set(rel.parts) & excluded_parts:
            continue
        if (file.name.startswith('ollama-') and file.name.endswith('-pull.log')) or file.name in excluded_names or file.name.startswith('.env') or file.suffix == '.pyc':
            continue
        files.append(file)
manifest = {}
with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for file in sorted(files):
        relative = file.relative_to(root).as_posix()
        archive.write(file, relative)
        manifest[relative] = hashlib.sha256(file.read_bytes()).hexdigest()
    archive.writestr('ARCHIVE-MANIFEST.json', json.dumps(manifest, indent=2)+'\n')
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert not any(set(Path(name).parts) & excluded_parts for name in archive.namelist())
print(f'{output}: {len(files)} files, {output.stat().st_size} bytes')
