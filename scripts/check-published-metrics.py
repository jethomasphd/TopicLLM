"""Independently recompute the public aggregate arithmetic without private labels.

This verifies reported metrics and denominators. It cannot re-adjudicate the
private benchmark, establish validity, or recreate retained provider responses.
Uses only the Python standard library; makes no API calls.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
from statistics import NormalDist

if not __debug__:
    raise RuntimeError('Run verification without Python optimization; assertions must remain active.')

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/data/trump'


def read(name):
    return json.loads((BASE / name).read_text(encoding='utf-8'))


def verify_metrics(report, expected_n):
    matrix = report['confusion']
    labels = list(matrix)
    assert labels and all(set(row) == set(labels) for row in matrix.values())
    assert all(type(value) is int and value >= 0 for row in matrix.values() for value in row.values())
    reference = {label: sum(matrix[label].values()) for label in labels}
    predicted = {label: sum(matrix[row][label] for row in labels) for label in labels}
    n = sum(reference.values())
    assert n == expected_n
    matches = sum(matrix[label][label] for label in labels)
    agreement = matches / n
    expected = sum(reference[label] * predicted[label] for label in labels) / n ** 2
    kappa = round((agreement - expected) / (1 - expected), 4) if expected < 1 else None
    assert math.isclose(report['agreement'], agreement, abs_tol=1e-12)
    assert report['cohens_kappa'] == kappa
    if 'agreement_wilson_95' in report:
        z = NormalDist().inv_cdf(.975)
        denominator = n + z * z
        center = (matches + z * z / 2) / denominator
        radius = z * math.sqrt(matches * (n - matches) / n + z * z / 4) / denominator
        assert all(math.isclose(a, b, abs_tol=1e-12) for a, b in zip(
            report['agreement_wilson_95'], [center - radius, center + radius]))
    if 'per_label' in report:
        assert set(report['per_label']) == set(labels)
        for label in labels:
            correct = matrix[label][label]
            assert report['per_label'][label] == {
                'human_n': reference[label], 'pred_n': predicted[label],
                'precision': round(correct / predicted[label], 4) if predicted[label] else None,
                'recall': round(correct / reference[label], 4) if reference[label] else None,
            }
    return matches


def main():
    application = read('reference-run.json')
    development = read('campaign/development_report.json')
    evaluation = read('campaign/evaluation_report.json')
    for scores in development['scores'].values():
        verify_metrics(scores, development['n'])
    for report, size in [(development, development['n']), (evaluation, evaluation['n_benchmark'])]:
        agreements = verify_metrics(report['independent_human_agreement'], size)
        assert report['adjudicated_disagreements'] == size - agreements
    matches = verify_metrics(evaluation['metrics'], evaluation['n_benchmark'])
    themes = list(application['codebook']['themes'])
    unsupported = [name for name in themes if not evaluation['metrics']['per_label'][name]['human_n']
                   or not evaluation['metrics']['per_label'][name]['recall']]
    gate = evaluation['metrics']['agreement'] > evaluation['threshold'] and not unsupported
    assert set(evaluation['unsupported_themes']) == set(unsupported)
    assert evaluation['gate_passed'] == application['evaluation_gate_passed'] == gate
    assert application['validation'] == evaluation

    counts_path = BASE / 'campaign/theme_counts.csv'
    count_rows = 0
    if application.get('prevalence'):
        with counts_path.open(encoding='utf-8', newline='') as handle:
            counts = list(csv.DictReader(handle))
        labels = set(evaluation['metrics']['per_label'])
        assert len(counts) == len(labels) and {r['theme'] for r in counts} == labels
        n = application['target_records']
        assert sum(int(row['documents']) for row in counts) == n
        embedded = {row['theme']: row for row in application['prevalence']}
        for row in counts:
            assert int(row['denominator']) == n and int(row['documents']) >= 0
            assert math.isclose(float(row['share']), int(row['documents']) / n, abs_tol=1e-12)
            assert all(str(embedded[row['theme']][key]) == row[key]
                       for key in ['documents', 'denominator', 'share'])
            assert row['classifier_validated'].lower() == str(application['classifier_validated']).lower()
        if not application['classifier_validated']:
            assert application['demonstration_exception']['decision'] == 'continue_unvalidated_demonstration'
            assert application['estimand']['classifier_validated'] is False
            assert application['estimand']['model_mode'] == 'unvalidated-demonstration'
            verified = read('campaign/demonstration_verification.json')
            assert verified['status'] == 'pass' and verified['classifier_validated'] is False
            assert verified['target_posts'] == n and verified['missing_or_unresolved'] == 0
            verified_rows = {row['theme']: row for row in verified['rows']}
            assert len(verified['rows']) == len(labels) and set(verified_rows) == labels
            for row in counts:
                checked = verified_rows[row['theme']]
                assert checked['documents'] == int(row['documents']) and checked['denominator'] == n
                assert math.isclose(checked['share'], float(row['share']), abs_tol=1e-12)
        count_rows = len(counts)
    elif application['mode'].endswith('-complete'):
        raise AssertionError('A complete application needs its aggregate counts.')

    integrity = read('campaign/artifact-integrity.json')['files']
    for name, digest in integrity.items():
        assert hashlib.sha256((BASE / 'campaign' / name).read_bytes()).hexdigest() == digest, name
    print(json.dumps({
        'aggregate_checks': 'pass', 'heldout_matches': matches,
        'heldout_n': evaluation['n_benchmark'], 'heldout_gate_passed': gate,
        'aggregate_share_rows_checked': count_rows, 'evidence_hashes_checked': len(integrity),
        'scope': 'Arithmetic and file integrity only; no independent re-adjudication or scientific acceptance.',
    }, indent=2))


if __name__ == '__main__':
    main()
