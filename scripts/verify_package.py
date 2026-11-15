"""Check a built wheel imports its catalog independently of the source checkout."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

wheel = max(Path('reports/wheels').glob('chemat-*.whl'), key=lambda p:p.stat().st_mtime)
with tempfile.TemporaryDirectory(prefix='chemat-package-') as folder:
    with zipfile.ZipFile(wheel) as archive:
        assert 'chemat/catalog.json' in archive.namelist()
        archive.extractall(folder)
    env = {**os.environ, 'PYTHONPATH': folder}
    subprocess.run([sys.executable, '-c',
                    'from chemat.match import Match; m=Match(["a","b"],7,0); '
                    'assert sum(len(d.cards) for d in m.decks.values())+2==211; '
                    'print("Packaged catalog and match setup verified")'],
                   cwd=folder, env=env, check=True)
