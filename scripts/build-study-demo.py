"""Generate an explicit seven-topic teaching reconstruction from synthetic truth.

This does not fit a topic model. It never alters the corpus, source documents,
or the observed 20-topic exploratory reference run. No historical ballots or
model outputs are fabricated.
"""
import csv
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'data'
CAMPAIGNS = {
    'delivery_app':0, 'shop_online':0, 'stay_home_sips':0, 'little_sunshine':0,
    'serve_strong_fund':1, 'takeout_support':1, 'bar_partners':1,
    'living_room_tour':2, 'howdy_neighbor':3, 'contests':3,
    'draft_night':4, 'couch_league':5, 'game_day':5,
    'charity_royale':6, 'game_night':6,
}

def build():
    study = json.loads((DATA / 'study.json').read_text(encoding='utf-8'))
    rows = list(csv.DictReader((DATA / 'demonstration_ground_truth.csv').open(encoding='utf-8',newline='\n')))
    mapped = [{'post_id':r['post_id'], 'topic':CAMPAIGNS.get(r['campaign'],-1), 'theme':r['theme']} for r in rows]
    assert set(r['topic'] for r in mapped if r['topic'] >= 0) == set(range(7))
    for r in mapped:
        if r['topic'] >= 0:
            assert study['topics'][r['topic']]['theme'] == r['theme']
    return {'schema_version':1,'mode':'calibrated-synthetic-reconstruction',
            'assignment_method':'Known generator campaigns mapped to seven teaching categories. No clustering was performed.',
            'corpus_sha256':hashlib.sha256((DATA/'demonstration_corpus.csv').read_bytes()).hexdigest(),
            'campaign_map':CAMPAIGNS, 'rows':mapped}

if __name__ == '__main__':
    (DATA/'study-demo.json').write_text(json.dumps(build(),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
    print('Wrote seven-topic synthetic reconstruction with explicit provenance.')
