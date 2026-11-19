"""Reject withdrawn annotation records in public files and release archives.

This checks the current release, not remote caches or third-party clones.
Human-approved topic definitions and aggregate confusion counts remain public.
"""
from pathlib import Path, PurePosixPath
from io import BytesIO
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = {
    f'{stage}_{suffix}'
    for stage in ('development', 'evaluation')
    for suffix in ('annotations.csv', 'annotations.review.json', 'predictions.csv')
} | {'classified_corpus.csv', 'validate_predictions.csv', 'benchmark_predictions.csv',
     'development_labels.csv', 'evaluation_labels.csv'}


def check_responses(data, location):
    records = json.loads(data)
    if not isinstance(records, list) or any(
        not str(row.get('operation', '')).startswith('naming:') for row in records
    ):
        raise ValueError(f'Post-level benchmark responses in public artifact: {location}')


def check_archive(data, location):
    with zipfile.ZipFile(BytesIO(data)) as archive:
        for name in archive.namelist():
            base = PurePosixPath(name).name
            if base in PRIVATE:
                raise ValueError(f'Private annotation or prediction artifact: {location}/{name}')
            if base == 'api_responses.json':
                check_responses(archive.read(name), f'{location}/{name}')
            if base == 'campaign-evidence.zip':
                check_archive(archive.read(name), f'{location}/{name}')


def main():
    checked = 0
    for area in ('docs', 'dist'):
        public = ROOT / area
        if not public.exists():
            continue
        for path in public.rglob('*'):
            if path.is_file() and path.name in PRIVATE:
                raise ValueError(f'Private file in public tree: {path.relative_to(ROOT)}')
        responses = public / 'data/trump/campaign/api_responses.json'
        if responses.exists():
            check_responses(responses.read_bytes(), responses.relative_to(ROOT))
            checked += 1
        for relative in ('data/trump/campaign-evidence.zip', 'downloads/topicllm-research-source.zip'):
            archive = public / relative
            if archive.exists():
                check_archive(archive.read_bytes(), archive.relative_to(ROOT))
                checked += 1
    print(f'Publication privacy passed: {checked} logs/archives checked; no individual benchmark records.')


if __name__ == '__main__':
    main()
