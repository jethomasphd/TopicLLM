"""Bind checkpoints to exact inputs and analysis settings before reuse."""
import hashlib
import json
import platform
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

def input_kind(path, bundled_filename):
    from config import DEMO_DIR
    source, bundled = Path(path), Path(DEMO_DIR) / bundled_filename
    return ('bundled-synthetic' if source.is_file() and bundled.is_file()
            and source.read_bytes() == bundled.read_bytes() else 'researcher-supplied-unverified')

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), default=str).encode()).hexdigest()

def checkpoint_guard(path, specification, checkpoint_exists=False):
    path = Path(path)
    digest = fingerprint(specification)
    if path.exists():
        old = json.loads(path.read_text(encoding='utf-8'))
        if old.get('sha256') != digest:
            raise ValueError('Checkpoint inputs or settings changed. Use a new output directory; old labels cannot be reused.')
    elif checkpoint_exists:
        raise ValueError('Legacy checkpoint has no input fingerprint. Use a new output directory.')
    else:
        path.write_text(json.dumps({'sha256':digest,'specification':specification},indent=2,default=str),encoding='utf-8')
    return digest

def environment():
    packages={}
    for name in ['bertopic','sentence-transformers','umap-learn','hdbscan','gensim','nltk','pandas','numpy','scipy','scikit-learn','statsmodels','openai']:
        try: packages[name]=version(name)
        except PackageNotFoundError: packages[name]=None
    return {'python':platform.python_version(),'platform':platform.platform(),'packages':packages}
