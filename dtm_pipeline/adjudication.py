"""Present actual independent labels for human consensus; never choose a winner."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def adjudication_evidence(csv_path, codebook_path, none_label, phase='development'):
    if phase not in ['development', 'evaluation']:
        raise ValueError('Choose development or evaluation.')
    source, book = Path(csv_path), Path(codebook_path)
    with source.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    codebook = json.loads(book.read_text(encoding='utf-8'))
    labels = list(codebook['themes']) + [none_label]
    if not codebook.get('decision_rule') or not rows:
        raise ValueError('Supply a frozen codebook and independent annotations.')
    required = {'post_id', 'tweet', 'reviewer_1', 'reviewer_2', 'reviewer_1_label', 'reviewer_2_label', 'human_label', 'adjudication_note'}
    if any(not required <= row.keys() for row in rows):
        raise ValueError('Use the merged independent-reviewer CSV.')
    if len({r['post_id'] for r in rows}) != len(rows) or any(not r['post_id'] for r in rows):
        raise ValueError('Every source ID must be present exactly once.')
    reviewers = [rows[0]['reviewer_1'], rows[0]['reviewer_2']]
    if len({n.strip().casefold() for n in reviewers}) != 2 or not all(n.strip() for n in reviewers):
        raise ValueError('Two distinct actual reviewers are required.')
    for row in rows:
        if [row['reviewer_1'], row['reviewer_2']] != reviewers:
            raise ValueError('Reviewer identities must be consistent across rows.')
        if row['reviewer_1_label'] not in labels or row['reviewer_2_label'] not in labels:
            raise ValueError('An independent label is outside the frozen codebook.')
        agreed = row['reviewer_1_label'] == row['reviewer_2_label']
        if (agreed and row['human_label'] != row['reviewer_1_label']) or (not agreed and row['human_label']):
            raise ValueError('Start from the unresolved merge; never overwrite existing adjudication.')
    n = len(rows)
    a, b = (Counter(r[column] for r in rows) for column in ['reviewer_1_label', 'reviewer_2_label'])
    agreements = sum(r['reviewer_1_label'] == r['reviewer_2_label'] for r in rows)
    po = agreements / n
    pe = sum(a[label] * b[label] for label in labels) / n**2
    packet = {'schema_version': 1, 'phase': phase, 'rows': rows, 'reviewers': reviewers, 'codebook': codebook,
              'none_label': none_label, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'codebook_sha256': hashlib.sha256(book.read_bytes()).hexdigest(),
              'statistics': {'n': n, 'agreements': agreements, 'disagreements': n-agreements,
                             'agreement': po, 'cohens_kappa': (po-pe)/(1-pe) if pe < 1 else None}}
    packet['packet_sha256'] = hashlib.sha256(json.dumps(packet, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return packet


def render_adjudication_ui(csv_path, codebook_path, output, none_label, phase='development'):
    packet = adjudication_evidence(csv_path, codebook_path, none_label, phase)
    payload = json.dumps(packet, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = Path(__file__).with_name('adjudication_ui.html').read_text(encoding='utf-8')
    Path(output).write_text(template.replace('__PACKET_JSON__', payload), encoding='utf-8', newline='\n')
    return packet['statistics']


def check_completed_adjudication(csv_path, source_csv, codebook_path, none_label, phase='development'):
    """Check the returned export against both original labels and frozen meanings."""
    packet = adjudication_evidence(source_csv, codebook_path, none_label, phase)
    with Path(csv_path).open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    indexed = {r['post_id']: r for r in rows}
    if len(indexed) != len(rows) or set(indexed) != {r['post_id'] for r in packet['rows']}:
        raise ValueError('Adjudication must contain the exact original IDs, once each.')
    labels = set(packet['codebook']['themes']) | {none_label}
    for original in packet['rows']:
        row = indexed[original['post_id']]
        for field, value in original.items():
            if field not in ['human_label', 'adjudication_note'] and row.get(field) != value:
                raise ValueError('Original text, independent labels and reviewer notes must remain unchanged.')
        if row.get('human_label') not in labels or not row.get('adjudication_note', '').strip():
            raise ValueError('Every disagreement requires a valid agreed label and rationale.')
        if original['human_label'] and any(row.get(k) != original[k] for k in ['human_label', 'adjudication_note']):
            raise ValueError('The agreement rows changed; document any additional correction separately.')
        if any(row.get(k) != v for k, v in {'adjudication_source_sha256':packet['source_sha256'],
                'codebook_sha256':packet['codebook_sha256'], 'annotation_phase':phase, 'both_reviewers_confirmed':'true'}.items()):
            raise ValueError('Current source/codebook hashes and both actual human confirmations are required.')
    return {'records':len(rows), 'reviewers':packet['reviewers'], 'disagreements_adjudicated':packet['statistics']['disagreements'],
            'annotations_sha256':hashlib.sha256(Path(csv_path).read_bytes()).hexdigest()}
