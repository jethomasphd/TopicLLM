"""Publish measured campaign evidence and only actually completed research stages."""
import argparse,csv,hashlib,json,random,shutil,sys,zipfile
import pandas as pd
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dtm_pipeline.config import PipelineConfig
from dtm_pipeline.sampling import read_selected,CAMPAIGN,PRESIDENCY
from dtm_pipeline.review import require_review,sha
from dtm_pipeline.research_validation import require_validation_review,read_annotations,validation_spec
from dtm_pipeline.stage4_classification import score_labels
from dtm_pipeline.provenance import fingerprint
from dtm_pipeline.demonstration import require_demonstration_exception


def publish(config_path,allow_in_progress=False):
    cfg=PipelineConfig(**json.loads(Path(config_path).read_text(encoding='utf-8')))
    if cfg.discovery_window!=CAMPAIGN or cfg.target_window!=PRESIDENCY or not cfg.require_disjoint_windows:
        raise ValueError('This publisher is specific to the declared campaign-to-presidency application.')
    run=Path(cfg.output_dir);stage=run/'stage1';out=ROOT/'docs/data/trump';evidence=out/'campaign'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    rows=lambda p:list(csv.DictReader(p.open(encoding='utf-8',newline='')))
    dump=lambda p,v:p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    verify=read(run/'verification.json')
    record=read(stage/'run_manifest.json')
    selected,selection=read_selected(cfg,'discovery');target,target_selection=read_selected(cfg,'target')
    if verify['status']!='complete' or not verify['selected_model_reload_verified'] or verify['input_sha256']!=selection['source_sha256'] or verify['selection']!=selection:
        raise ValueError('Verify the exact selected campaign model before publishing evidence.')
    if hashlib.sha256((stage/'best_model/fitted_model.pkl').read_bytes()).hexdigest()!=verify['fitted_model_sha256']:
        raise ValueError('The verified model changed.')
    if selection['source_sha256']!=read(out/'manifest.json')['files']['corpus.csv']['sha256']:
        raise ValueError('Only the canonical public archive can be published.')
    assignments=rows(stage/'best_model/classified_tweets.csv');excluded=rows(stage/'excluded_empty.csv')
    ids=[r['post_id'] for r in assignments+excluded]
    if len(ids)!=len(set(ids)) or set(ids)!={r['post_id'] for r in selected}:
        raise ValueError('Assignments and exclusions must exactly partition campaign IDs.')
    complete=(run/'stage5/theme_counts.csv').exists()
    if complete:
        require_review(cfg)
        if cfg.demonstration_exception_path:require_demonstration_exception(cfg)
        else:require_validation_review(cfg)
        classified=rows(run/'stage4/classified_corpus.csv')
        if len(classified)!=len(target) or {r['post_id'] for r in classified}!={r['post_id'] for r in target}:
            raise ValueError('Classifications must exhaust the target population exactly.')
    elif not allow_in_progress:
        raise ValueError('Human validation and prevalence are unfinished. An explicit draft build is required.')
    names={int(r['topic']):r for r in rows(run/'stage2/topic_names.csv')} if (run/'stage2/topic_names.csv').exists() else {}
    tallies=rows(run/'stage2/vote_tallies.csv') if names else []
    if names:
        ballots=rows(run/'stage2/vote_log.csv')
        manifest=read(run/'stage2/naming_manifest.json')['specification']
        expected={int(r['topic']) for r in rows(stage/'topics_for_naming.csv')}
        if set(names)!=expected or set(int(r['topic']) for r in ballots)!=expected:
            raise ValueError('Naming must cover every adopted topic exactly.')
        for key,value in {'model':cfg.llm_model,'domain':cfg.domain_context,'max_tokens':cfg.naming_max_tokens,
                          'temperature':cfg.naming_temperature,'votes':cfg.votes_per_topic,'naming_run_id':cfg.naming_run_id}.items():
            if manifest.get(key)!=value:raise ValueError('Naming settings differ from the declared configuration: '+key)
        for ident in expected:
            group=[r for r in ballots if int(r['topic'])==ident]
            if len(group)!=cfg.votes_per_topic or {int(r['vote_index']) for r in group}!=set(range(1,cfg.votes_per_topic+1)) or any(r.get('complete')!='True' or r['label']=='__API_ERROR__' or not r['label'].strip() for r in group):
                raise ValueError('Incomplete or duplicated naming ballots.')
            if int(names[ident]['total_votes'])!=len(group) or sum(int(r['votes']) for r in tallies if int(r['topic'])==ident)!=len(group):
                raise ValueError('Naming totals do not match the retained ballots.')
    if any(row.get('model')!=cfg.llm_model or row.get('model')=='MOCK' for row in names.values()):
        raise ValueError('Only real, declared model measurements can be published as naming evidence.')
    if complete and any(row.get('model')=='MOCK' for row in classified):
        raise ValueError('Mock classifications cannot be published as research findings.')
    topics=[]
    for item in rows(stage/'topics_for_naming.csv'):
        ident=int(item['topic']);group=[r for r in assignments if int(r['topic'])==ident]
        sample=random.Random(42).sample(group,min(5,len(group)))
        topic={'id':ident,'words':item['words'].split(', '),'count':len(group),
               'examples':[{k:r[k] for k in ['post_id','tweet','date','is_retweet']} for r in sample]}
        if ident in names:
            name=names[ident]
            topic['naming']={'modal_label':name['modal_label'],'votes_for_modal':int(name['votes_for_modal']),
               'total_votes':int(name['total_votes']),'modal_share':float(name['modal_share']),
               'distinct_labels':int(name['distinct_labels']),'model':name['model'],
               'top_names':[{'label':r['norm'],'votes':int(r['votes'])} for r in tallies if int(r['topic'])==ident][:5]}
        topics.append(topic)
    noise=[r for r in assignments if int(r['topic'])==-1]
    summary={'schema_version':2,'dataset':'Donald Trump account archive: campaign-to-presidency application',
        'mode':'validated-campaign-presidency' if complete else 'campaign-research-in-progress',
        'input_sha256':selection['source_sha256'],'archive_records':selection['source_records'],
        'source_records':len(selected),'discovery_records':len(assignments),'excluded_empty':len(excluded),
        'discovery_window':CAMPAIGN,'target_window':PRESIDENCY,'target_records':len(target),
        'outliers':len(noise),'topics':topics,'parameters':read(stage/'best_model/parameters.json'),
        'selection_record':read(stage/'selection_record.json'),'verification':verify,
        'naming_completed':len(names)==len(topics),'human_review_performed':False,'classifier_validated':False,
        'scope':'Campaign topic discovery, human theme synthesis, independent evaluation and overall presidential prevalence.'}
    if (run/'stage3/review_record.json').exists():
        require_review(cfg);summary['human_review_performed']=True
        summary['codebook']=read(Path(cfg.codebook_path))
        summary['theme_map']=rows(run/'stage3/theme_map.csv')
        summary['reviewers']=read(run/'stage3/review_record.json')['reviewers']
    development=None
    if (run/'stage4/classifier_selection.json').exists():
        require_review(cfg)
        frozen=read(run/'stage4/classifier_selection.json')
        if frozen['specification']!=validation_spec(cfg):
            raise ValueError('Development selection no longer matches the approved research specification.')
        annotations=read_annotations(cfg.development_csv,cfg,{r['post_id']:r for r in target},'development')
        predictions=rows(run/'stage4/development_predictions.csv')
        source=annotations.set_index('post_id').to_dict(orient='index')
        if len(predictions)!=len(source) or {r['post_id'] for r in predictions}!=set(source):
            raise ValueError('Development predictions do not exactly cover the frozen annotations.')
        if any(any(row[key]!=source[row['post_id']][key] for key in annotations.columns if key!='post_id') for row in predictions):
            raise ValueError('Development predictions changed the human annotation evidence.')
        options=cfg.themes+[cfg.none_label]
        for name,metrics in frozen['development_scores'].items():
            if name=='llm' and any(r['llm_status']!='matched' for r in predictions):
                raise ValueError('Unresolved development responses cannot be published as scored results.')
            observed=score_labels(pd.Series([r['human_label'] for r in predictions]),pd.Series([r[name+'_pred'] for r in predictions]),options)
            if observed!=metrics:raise ValueError('Development metrics do not match retained predictions.')
        human=score_labels(annotations.reviewer_1_label,annotations.reviewer_2_label,options)
        development={'phase':'development','n':len(annotations),'winner':frozen['winner'],
            'selection_rule':frozen['selection_rule'],'selected_at':frozen['selected_at'],
            'scores':frozen['development_scores'],
            'independent_human_agreement':{k:human[k] for k in ['agreement','cohens_kappa','confusion']},
            'adjudicated_disagreements':int((annotations.reviewer_1_label!=annotations.reviewer_2_label).sum()),
            'annotations_sha256':sha(cfg.development_csv),
            'codebook_sha256':sha(cfg.codebook_path),
            'classifier_selection_sha256':sha(run/'stage4/classifier_selection.json'),
            'interpretation':'Development comparison for selection, not independent validation or presidential prevalence.'}
        summary['development']=development
        decision_path=run/'stage4/evaluation_proceed_decision.json'
        if decision_path.exists():
            decision=read(decision_path)
            expected={'codebook_sha256':sha(cfg.codebook_path),
                'classifier_selection_sha256':sha(run/'stage4/classifier_selection.json'),
                'sampling_manifest_sha256':sha(cfg.annotation_manifest)}
            if any(decision.get(k)!=v for k,v in expected.items()):
                raise ValueError('The decision to proceed belongs to different research evidence.')
            summary['evaluation_proceed_decision']=decision
    evaluation=None
    if (run/'stage4/validation_report.json').exists():
        if not development:raise ValueError('Held-out results require a current frozen development selection.')
        evaluation=read(run/'stage4/validation_report.json')
        annotated=read_annotations(cfg.benchmark_csv,cfg,{r['post_id']:r for r in target},'evaluation')
        predicted=rows(run/'stage4/validate_predictions.csv')
        originals=annotated.set_index('post_id').to_dict(orient='index')
        if len(predicted)!=len(originals) or {r['post_id'] for r in predicted}!=set(originals):
            raise ValueError('Held-out predictions must exactly cover the reserved human reference.')
        if any(any(row[k]!=originals[row['post_id']][k] for k in annotated.columns if k!='post_id') for row in predicted):
            raise ValueError('Held-out predictions changed the human reference evidence.')
        winner=frozen['winner']
        if winner=='llm' and any(r['llm_status']!='matched' for r in predicted):
            raise ValueError('Resolve every held-out response before publishing evaluation metrics.')
        observed=score_labels(pd.Series([r['human_label'] for r in predicted]),pd.Series([r[winner+'_pred'] for r in predicted]),options)
        unsupported=[name for name in cfg.themes if observed['per_label'][name]['human_n']==0 or observed['per_label'][name]['recall']==0]
        expected={'n_benchmark':len(annotated),'winner':winner,'metrics':observed,
            'benchmark_sha256':sha(cfg.benchmark_csv),'specification_sha256':fingerprint(validation_spec(cfg)),
            'threshold':cfg.agreement_threshold,'unsupported_themes':unsupported,
            'gate_passed':observed['agreement']>cfg.agreement_threshold and not unsupported}
        if any(evaluation.get(k)!=v for k,v in expected.items()):
            raise ValueError('Held-out report differs from the retained reference, predictions or frozen criteria.')
        summary.update(evaluation_completed=True,evaluation_gate_passed=evaluation['gate_passed'],validation=evaluation)
    if (run/'stage4/validation_review.json').exists():
        require_validation_review(cfg);summary['classifier_validated']=True
    if cfg.demonstration_exception_path:
        summary['demonstration_exception']=require_demonstration_exception(cfg)
        summary['measurement_status']='unvalidated-demonstration'
        summary['mode']='unvalidated-demonstration-complete' if complete else 'unvalidated-demonstration-in-progress'
    if complete:
        summary['prevalence']=rows(run/'stage5/theme_counts.csv')
        summary['estimand']=read(run/'stage5/estimand.json')
        if sum(int(r['documents']) for r in summary['prevalence'])!=len(target):raise ValueError('Shares must count the complete target corpus.')
        if cfg.demonstration_exception_path and (summary['estimand'].get('model_mode')!='unvalidated-demonstration' or summary['estimand'].get('classifier_validated') is not False):
            raise ValueError('Demonstration shares must preserve their unvalidated status.')
        if summary['estimand']['classified_corpus_sha256']!=sha(run/'stage4/classified_corpus.csv'):
            raise ValueError('The classified corpus changed after aggregation.')
    summary['annotation_publication']='Aggregate results only. Independent human labels, adjudication notes and post-level evaluation predictions are retained privately.'
    evidence.mkdir(exist_ok=True)
    # A previous publisher copied row-level human records. Withdraw those public
    # copies without touching the private run or its original submissions.
    for name in ['development_annotations.csv','development_annotations.review.json','development_predictions.csv',
                 'evaluation_annotations.csv','evaluation_annotations.review.json','evaluation_predictions.csv']:
        (evidence/name).unlink(missing_ok=True)
    if evaluation:
        for source_path,target_name in [(run/'stage4/validation_report.json','evaluation_report.json'),
                (run/'annotations/evaluation_import_provenance.json','evaluation_import_provenance.json'),
                (run/'stage4/evaluation_execution_record.json','evaluation_execution_record.json')]:
            shutil.copy2(source_path,evidence/target_name)
    if cfg.demonstration_exception_path:dump(evidence/'demonstration_exception.json',summary['demonstration_exception'])
    if complete:
        with (evidence/'theme_counts.csv').open('w',encoding='utf-8',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=['theme','documents','denominator','share','classifier_validated','interpretation'],lineterminator='\n');writer.writeheader()
            writer.writerows({**row,'classifier_validated':summary['classifier_validated'],'interpretation':summary['estimand']['interpretation']} for row in summary['prevalence'])
        shutil.copy2(run/'stage5/estimand.json',evidence/'estimand.json')
    if development:
        dump(evidence/'development_report.json',development)
        if summary.get('evaluation_proceed_decision'):
            shutil.copy2(run/'stage4/evaluation_proceed_decision.json',evidence/'evaluation_proceed_decision.json')
        for source_path,target_name in [(run/'stage4/classifier_selection.json','classifier_selection.json')]:
            shutil.copy2(source_path,evidence/target_name)
    # Keep the previous measured run as a clearly separate historical artifact.
    old=out/'reference-run.json'
    if old.exists() and read(old).get('schema_version')!=2:
        archive=out/'prior-diagnostic';archive.mkdir(exist_ok=True)
        for name in ['reference-run.json','reference-evidence.zip']:
            if (out/name).exists() and not (archive/name).exists():shutil.copy2(out/name,archive/name)
    dump(out/'reference-run.json',summary)
    live=read(out/'live-examples.json')
    live.update(domain=cfg.domain_context,discovery_window=CAMPAIGN,target_window=PRESIDENCY,
        topics=[{'id':str(t['id']),'words':', '.join(t['words']),'count':t['count']} for t in topics],
        selection='1,024 evenly spaced presidential source rows including endpoints; public practice classifications, not a probability sample for validation.')
    live['examples']=[{'id':'trump-'+r['post_id'],'post_id':r['post_id'],'text':r['tweet'],'date':r['date'],'is_retweet':r['is_retweet']}
                      for r in [target[round(i*(len(target)-1)/1023)] for i in range(1024)]]
    if summary['human_review_performed']:
        live.update(themes=cfg.themes,codebook=summary['codebook'],human_review_performed=True,
                    codebook_sha256=hashlib.sha256(Path(cfg.codebook_path).read_bytes()).hexdigest(),
                    taxonomy_status=(f"Human-reviewed themes; classifier remains unvalidated. Held-out agreement {evaluation['metrics']['agreement']:.0%}, below the declared acceptance criteria." if evaluation and not evaluation['gate_passed'] else 'Human-reviewed themes; classifier performance remains unvalidated.') if not summary['classifier_validated'] else 'Human-reviewed themes with independently validated research classification.')
        for name in ['theme_map.csv','codebook.json','review_record.json','human_synthesis_submission.json','synthesis_packet.json']:
            shutil.copy2(run/'stage3'/name,evidence/name)
    dump(out/'live-examples.json',live)
    for source,target_name in [('all_iteration_results.json','all_iteration_results.json'),('best_model/parameters.json','parameters.json'),('topics_for_naming.csv','topics_for_naming.csv'),('selection_record.json','selection_record.json'),('coherence_curve.png','coherence_curve.png')]:
        shutil.copy2(stage/source,evidence/target_name)
    for name,records,fields in [('assignments.csv',assignments,['post_id','date','topic']),('excluded.csv',excluded,['post_id','date'])]:
        with (evidence/name).open('w',encoding='utf-8',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in records)
    for name in ['topic_names.csv','vote_tallies.csv','vote_log.csv']:
        if (run/'stage2'/name).exists() and names:shutil.copy2(run/'stage2'/name,evidence/name)
    record['config'].update(input_csv='docs/data/trump/corpus.csv',discovery_input_csv=None,stopwords_file='docs/data/trump/stopwords.txt',output_dir='runs/campaign-presidency')
    record['publication_note']='Local input/output paths normalized; measured parameters and source/model hashes preserved.'
    record['scope']='Stage 1 discovery execution. The separate naming_manifest.json records the exact subsequent naming settings and revision.'
    dump(evidence/'run_manifest.json',record);dump(evidence/'verification.json',verify)
    if (run/'api_usage.json').exists():dump(evidence/'api_usage.json',read(run/'api_usage.json'))
    if names:
        for name in ['naming_manifest.json','all_naming_attempts.jsonl']:
            shutil.copy2(run/'stage2'/name,evidence/name)
        if (run/'stage2/naming_verification.json').exists():shutil.copy2(run/'stage2/naming_verification.json',evidence/'naming_verification.json')
        for name in ['naming_revision.json']:
            if (run/name).exists():shutil.copy2(run/name,evidence/name)
        if (run/'api_responses.json').exists():
            dump(evidence/'api_responses.json',[r for r in read(run/'api_responses.json') if r['operation'].startswith('naming:')])
        # Initial attempts remain available separately and cannot enter final tallies.
        for attempt in ['naming-attempt-15tokens','naming-attempt-32tokens-encoding']:
            if (run/attempt).exists():
                shutil.copytree(run/attempt,evidence/attempt,dirs_exist_ok=True)
    hashes={p.relative_to(evidence).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(evidence.rglob('*')) if p.is_file() and p.name!='artifact-integrity.json'}
    dump(evidence/'artifact-integrity.json',{'files':hashes})
    with zipfile.ZipFile(out/'campaign-evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(evidence.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(evidence).as_posix())
    print(json.dumps({k:summary[k] for k in ['mode','source_records','discovery_records','target_records','outliers','naming_completed','human_review_performed','classifier_validated']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--allow-in-progress',action='store_true')
    args=parser.parse_args();publish(args.config,args.allow_in_progress)
