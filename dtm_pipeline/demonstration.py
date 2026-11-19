"""An explicit scientific exception never converts a failed evaluation into validation."""
import json
from pathlib import Path


def require_demonstration_exception(cfg):
    if __package__:
        from .review import require_review, sha
        from .research_validation import validation_spec
        from .provenance import fingerprint
        from .sampling import read_selected
    else:
        from review import require_review, sha
        from research_validation import validation_spec
        from provenance import fingerprint
        from sampling import read_selected
    require_review(cfg)
    if not cfg.demonstration_exception_path:
        raise ValueError('An explicit researcher demonstration exception is required.')
    record=json.loads(Path(cfg.demonstration_exception_path).read_text(encoding='utf-8'))
    root=Path(cfg.output_dir,'stage4')
    report=json.loads((root/'validation_report.json').read_text(encoding='utf-8'))
    selection=json.loads((root/'classifier_selection.json').read_text(encoding='utf-8'))
    _,target=read_selected(cfg,'target')
    expected={'decision':'continue_unvalidated_demonstration','classifier_validated':False,
        'validation_report_sha256':sha(root/'validation_report.json'),
        'classifier_selection_sha256':sha(root/'classifier_selection.json'),
        'benchmark_sha256':sha(cfg.benchmark_csv),'specification_sha256':fingerprint(validation_spec(cfg)),
        'target_selection':target,'reporting':'unvalidated model-assigned shares'}
    if any(record.get(k)!=v for k,v in expected.items()):
        raise ValueError('Demonstration exception is stale or does not explicitly retain unvalidated status.')
    if not all(isinstance(record.get(k),str) and record[k].strip() for k in ['researcher','rationale','recorded_at']):
        raise ValueError('Record the actual researcher, rationale and date of the exception.')
    ceiling=record.get('cumulative_budget_usd')
    if not isinstance(ceiling,(int,float)) or isinstance(ceiling,bool) or not 0<ceiling<=1000 or cfg.api_budget_usd is None or cfg.api_budget_usd>ceiling:
        raise ValueError('The configured budget exceeds the demonstration authorization.')
    if cfg.run_pairwise_tests:
        raise ValueError('A demonstration exception permits descriptive shares only, not significance tests.')
    if report.get('gate_passed') is not False or report.get('benchmark_sha256')!=sha(cfg.benchmark_csv) or selection['specification']!=validation_spec(cfg):
        raise ValueError('This exception requires the unchanged, completed failed evaluation.')
    return record
