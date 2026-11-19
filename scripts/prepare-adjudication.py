"""Render or check a source-bound joint review, without certifying research approval."""
import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dtm_pipeline.config import PipelineConfig
from dtm_pipeline.review import require_review
from dtm_pipeline.sampling import read_selected
from dtm_pipeline.adjudication import render_adjudication_ui,check_completed_adjudication

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--source',required=True,help='Unresolved merged independent-label CSV')
    parser.add_argument('--phase',choices=['development','evaluation'],default='development')
    parser.add_argument('--output',help='Standalone local HTML destination')
    parser.add_argument('--check',help='Completed researcher-exported CSV to verify; does not attest or execute classification')
    args=parser.parse_args()
    cfg=PipelineConfig(**json.loads(Path(args.config).read_text(encoding='utf-8')))
    require_review(cfg)
    target,selection=read_selected(cfg,'target');by_id={r['post_id']:r for r in target}
    with Path(args.source).open(encoding='utf-8-sig',newline='') as handle:rows=list(csv.DictReader(handle))
    for row in rows:
        original=by_id.get(row['post_id'])
        if original is None or any(row.get(k,'')!=original.get(k,'') for k in ['tweet','date']):
            raise ValueError('Adjudication text, dates or IDs differ from the declared target.')
    if cfg.annotation_manifest:
        sampling=json.loads(Path(cfg.annotation_manifest).read_text(encoding='utf-8'))
        if sampling['sampling']!=selection or set(sampling['packets'][args.phase]['ids'])!={r['post_id'] for r in rows}:
            raise ValueError('Adjudication must use exactly the frozen sample for this phase.')
    if args.check:
        result=check_completed_adjudication(args.check,args.source,cfg.codebook_path,cfg.none_label,args.phase)
    else:
        if not args.output:parser.error('--output is required when rendering')
        result=render_adjudication_ui(args.source,cfg.codebook_path,args.output,cfg.none_label,args.phase)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
