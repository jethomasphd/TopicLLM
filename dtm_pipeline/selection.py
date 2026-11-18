"""Adopt an actually reviewed candidate, preserving the coherence winner.

Reconstruct the saved candidate in the recorded ML environment, then require
exact assignment and word equality before promoting it for naming. This is an
explicit researcher selection, never an automatic coherence override.
"""
import argparse
import gzip
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',required=True)
    ap.add_argument('--iteration',required=True,type=int)
    ap.add_argument('--max-topics',required=True,type=int)
    ap.add_argument('--researcher',required=True)
    ap.add_argument('--rationale',required=True)
    args=ap.parse_args()
    import numpy as np
    import pandas as pd
    from sentence_transformers import SentenceTransformer
    from dtm_pipeline.stage1_topic_discovery import create_bertopic_model
    root=Path(args.run).resolve()/'stage1'
    if not args.researcher.strip() or len(args.rationale.strip())<30:
        raise ValueError('Record the actual researcher and a substantive selection rationale.')
    if (root.parent/'stage2/naming_manifest.json').exists() or (root/'selection_record.json').exists():
        raise ValueError('Selection is already frozen or naming has begun. Use a new declared analysis.')
    manifest=json.loads((root/'run_manifest.json').read_text(encoding='utf-8'))
    if manifest['status']!='complete':raise ValueError('Complete the search before selection.')
    candidate_path=root/'candidates'/f'iteration-{args.iteration:03d}-max-{args.max_topics:02d}.json.gz'
    candidate=json.loads(gzip.decompress(candidate_path.read_bytes()))
    cfg=manifest['config']
    frame=pd.read_csv(root/'preprocessed_tweets.csv',dtype={'post_id':str})
    docs=frame.preprocessed_tweet.tolist()
    embedder=SentenceTransformer(cfg['embedding_model'],revision=cfg['embedding_revision'])
    base=create_bertopic_model(embedder,set(manifest['effective_stopwords']),candidate['umap_params'],candidate['hdbscan_params'],None,cfg['random_seed'])
    base.fit_transform(docs,embeddings=np.load(root/'embeddings.npy'))
    base.reduce_topics(docs,nr_topics=args.max_topics)
    assert [int(t) for t in base.topics_]==candidate['assignments'], 'Reconstructed assignments differ; nothing promoted.'
    for topic in candidate['topics']:
        assert [w for w,_ in base.get_topic(topic['topic']) if w]==topic['words'], 'Reconstructed words differ; nothing promoted.'
    winner=root/'best_model'; preserved=root/'coherence_winner'
    if preserved.exists():raise ValueError('Coherence winner already preserved; inspect the previous selection attempt.')
    shutil.copytree(winner,preserved)
    shutil.copy2(root/'topics_for_naming.csv',preserved/'topics_for_naming.csv')
    shutil.copy2(root/'coherence_curve.png',preserved/'coherence_curve.png')
    shutil.copy2(root/'run_manifest.json',preserved/'run_manifest.json')
    base.save(str(winner/'fitted_model.pkl'),serialization='pickle',save_embedding_model=True)
    from bertopic import BERTopic
    reloaded = BERTopic.load(str(winner/'fitted_model.pkl'))
    assert list(reloaded.topics_) == candidate['assignments'], 'Saved candidate reload differs; inspect before naming.'
    # Do not leave figures of the coherence winner under the adopted model's path.
    for name in ['topic_visualization.html', 'topic_similarity.html']:
        (winner / name).unlink(missing_ok=True)
    try:
        base.visualize_topics().write_html(str(winner/'topic_visualization.html'))
        base.visualize_heatmap().write_html(str(winner/'topic_similarity.html'))
    except Exception as exc:
        (winner/'visualization_status.json').write_text(json.dumps({'available':False,'reason':type(exc).__name__}),encoding='utf-8')
    frame['topic']=base.topics_
    frame.to_csv(winner/'classified_tweets.csv',index=False)
    base.get_topic_info().to_csv(winner/'topic_words.csv',index=False)
    rows=[{'topic':t['topic'],'words':', '.join(t['words']),'n_documents':candidate['topic_sizes'][str(t['topic'])]} for t in candidate['topics']]
    pd.DataFrame(rows).to_csv(root/'topics_for_naming.csv',index=False)
    parameters={key:candidate[key] for key in ['iteration','umap_params','hdbscan_params','max_topics','coherence']}
    parameters.update(n_topics=candidate['n_topics_found'],seed=cfg['random_seed'],seed_umap=cfg['seed_umap'])
    (winner/'parameters.json').write_text(json.dumps(parameters,indent=2),encoding='utf-8')
    record={'decision':'researcher-selected-candidate','researcher':args.researcher,'rationale':args.rationale,
            'recorded_at':datetime.now(timezone.utc).isoformat(),'candidate_sha256':hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
            'exact_assignment_reconstruction_verified':True,'selected_model_reload_verified':True,'coherence_winner':json.loads((preserved/'parameters.json').read_text()),
            'selected_candidate':parameters,'scope':'campaign evidence only; no presidential outcomes used'}
    (root/'selection_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    manifest.update(selected_iteration=args.iteration,selected_coherence=candidate['coherence'],selection_decision=record,
                    fitted_model_sha256=hashlib.sha256((winner/'fitted_model.pkl').read_bytes()).hexdigest())
    (root/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    import matplotlib.pyplot as plt
    search=json.loads((root/'all_iteration_results.json').read_text())
    iteration=next(r for r in search['iterations'] if r['iteration']==args.iteration)
    xs,ys=zip(*iteration['results']);plt.figure(figsize=(10,6));plt.plot(xs,ys,'o-');plt.axvline(args.max_topics,color='#176b67',linestyle='--')
    plt.xlabel('Maximum topic setting');plt.ylabel('c_v coherence');plt.title('Researcher-selected campaign configuration')
    plt.tight_layout();plt.savefig(root/'coherence_curve.png',dpi=200);plt.close()
    print('Candidate adopted with exact reconstruction; numerical coherence winner preserved.')

if __name__=='__main__':main()
