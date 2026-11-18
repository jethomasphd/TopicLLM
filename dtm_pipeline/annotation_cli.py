"""Create independent human annotation workbooks from a declared run config."""
import argparse
import json
import sys
from pathlib import Path
from dtm_pipeline.config import PipelineConfig
from dtm_pipeline.annotations import draw_packets, adjudication_packet, render_annotation_ui

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--development-n', type=int, default=100)
    parser.add_argument('--evaluation-n', type=int, default=250)
    parser.add_argument('--seed', type=int, default=20261118)
    parser.add_argument('--reviewer-exports', nargs=2, help='Merge two real exports into an unresolved adjudication CSV')
    parser.add_argument('--render-only', action='store_true', help='Render existing blank packets with the newly frozen codebook; never redraw')
    args=parser.parse_args()
    cfg=PipelineConfig(**json.loads(Path(args.config).read_text(encoding='utf-8')))
    if args.reviewer_exports:
        print(json.dumps(adjudication_packet(*args.reviewer_exports,args.output),indent=2))
    else:
        if args.render_only:
            result=json.loads((Path(args.output)/'sampling_manifest.json').read_text(encoding='utf-8'))
            from dtm_pipeline.sampling import read_selected
            import hashlib
            if result['sampling']!=read_selected(cfg,'target')[1]:
                raise ValueError('Existing packets belong to a different target selection.')
            for phase in ['development','evaluation']:
                packet_path=Path(args.output)/f'{phase}_blank.csv'
                if hashlib.sha256(packet_path.read_bytes()).hexdigest()!=result['packets'][phase]['blank_sha256']:
                    raise ValueError('A blank packet changed after sampling; refusing to render it.')
            if not cfg.codebook_path:raise ValueError('Freeze the codebook before rendering annotation interfaces.')
        else:
            result=draw_packets(cfg,args.output,args.development_n,args.evaluation_n,args.seed)
        if cfg.codebook_path:
            for phase in ['development','evaluation']:
                render_annotation_ui(Path(args.output)/f'{phase}_blank.csv',cfg.codebook_path,Path(args.output)/f'{phase}.html',phase,cfg.none_label)
        print(json.dumps({k:v for k,v in result.items() if k!='packets'},indent=2))

if __name__=='__main__':main()
