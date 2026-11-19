"""Artificial fixtures only. No test decision is a research annotation."""
import csv,json
import pytest
from dtm_pipeline.adjudication import adjudication_evidence,render_adjudication_ui,check_completed_adjudication

def fixture(root):
    rows=[{'post_id':'0001','date':'2018-01-01','tweet':'Artificial example </script> & text','reviewer_1':'Fixture human A','reviewer_2':'Fixture human B','reviewer_1_label':'A','reviewer_2_label':'B','human_label':'','adjudication_note':'','reviewer_1_notes':'original note','reviewer_2_notes':''},
          {'post_id':'0002','date':'2018-01-02','tweet':'Another artificial example','reviewer_1':'Fixture human A','reviewer_2':'Fixture human B','reviewer_1_label':'A','reviewer_2_label':'A','human_label':'A','adjudication_note':'Independent agreement','reviewer_1_notes':'','reviewer_2_notes':''}]
    source=root/'source.csv';write(source,rows)
    book=root/'book.json';book.write_text(json.dumps({'themes':{'A':'Artificial first definition','B':'Artificial second definition'},'decision_rule':'Artificial fixture rule.'}))
    return source,book

def write(path,rows):
    with path.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def completed(source,book):
    p=adjudication_evidence(source,book,'Residual')
    rows=[{**r,'adjudication_source_sha256':p['source_sha256'],'codebook_sha256':p['codebook_sha256'],'annotation_phase':'development','both_reviewers_confirmed':'true'} for r in p['rows']]
    rows[0].update(human_label='B',adjudication_note='Actual input simulated for this software test only.')
    return rows

def test_render_retains_originals_and_never_resolves_disagreement(tmp_path):
    source,book=fixture(tmp_path);before=source.read_bytes()
    result=render_adjudication_ui(source,book,tmp_path/'review.html','Residual')
    assert result['agreements']==1 and result['disagreements']==1 and result['cohens_kappa']==0
    page=(tmp_path/'review.html').read_text(encoding='utf-8')
    assert 'Artificial example </script>' not in page and '\\u003c/script\\u003e' in page
    assert source.read_bytes()==before
    assert adjudication_evidence(source,book,'Residual')['rows'][0]['human_label']==''

def test_completed_export_checks_original_labels_and_consensus(tmp_path):
    source,book=fixture(tmp_path);output=tmp_path/'completed.csv';write(output,completed(source,book))
    assert check_completed_adjudication(output,source,book,'Residual')['disagreements_adjudicated']==1
    assert not output.with_name(output.name+'.review.json').exists()

@pytest.mark.parametrize('case',['label','note','source','book','confirm','phase','original','agreement','missing','duplicate'])
def test_invalid_exports_cannot_pass(tmp_path,case):
    source,book=fixture(tmp_path);rows=completed(source,book)
    field={'label':'human_label','note':'adjudication_note','source':'adjudication_source_sha256','book':'codebook_sha256','confirm':'both_reviewers_confirmed','phase':'annotation_phase','original':'reviewer_1_label'}.get(case)
    if field:rows[0][field]='' if case in ['label','note'] else 'changed'
    elif case=='agreement':rows[1]['human_label']='B'
    elif case=='missing':rows.pop()
    elif case=='duplicate':rows.append(rows[0])
    output=tmp_path/'completed.csv';write(output,rows)
    with pytest.raises(ValueError):check_completed_adjudication(output,source,book,'Residual')
