"""Compile public source context. Requires pypdf==6.21.4; never modifies a source PDF."""
from pathlib import Path
import hashlib, json, re
from pypdf import PdfReader

root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((root/'source-integrity.json').read_text(encoding='utf-8'))
for item in manifest['files']:
    if sha(root/item['path'])!=item['sha256']:raise SystemExit('Protected source mismatch: '+item['path'])
pdf=root/'THOMAS-PRIMARY-2025.pdf'
chunks=[]
for page_number,page in enumerate(PdfReader(pdf).pages,1):
    text=re.sub(r'\s+',' ',page.extract_text() or '').strip()
    if len(text)<80:continue
    for offset in range(0,len(text),2600):
        part=text[max(0,offset-180):offset+2600]
        chunks.append({'id':f'dissertation-{page_number}-{offset//2600}', 'title':f'Dissertation · p. {page_number}', 'url':f'/THOMAS-PRIMARY-2025.pdf#page={page_number}', 'text':part})
inputs=['docs/guide/knowledge.md','README.md','REPRODUCE.md','AGENTS.md','AUDIT.md','docs/protocol.json','docs/paper/index.html','docs/welcome/index.html','docs/validation/index.html','docs/audit/index.html','docs/data/README.md','docs/data/index.html','docs/README.md','docs/data/trump/manifest.json','docs/data/trump/reference-run.json']
for name in inputs[1:]:
    raw=(root/name).read_text(encoding='utf-8')
    if name.endswith('.html'):raw=re.sub('<[^>]+>',' ',re.sub(r'<(style|script)\b.*?</\1>','',raw,flags=re.S))
    raw=re.sub(r'\s+',' ',raw).strip()
    url={'docs/paper/index.html':'/paper/','docs/welcome/index.html':'/welcome/','docs/validation/index.html':'/validation/','docs/audit/index.html':'/audit/','docs/data/index.html':'/data/'}.get(name) or ('/'+name[5:] if name.startswith('docs/') else 'https://github.com/jethomasphd/TopicLLM/blob/main/'+name)
    for offset in range(0,len(raw),2600):
        chunks.append({'id':re.sub(r'\W+','-',name)+f'-{offset//2600}', 'title':name, 'url':url, 'text':raw[max(0,offset-180):offset+2600]})
result={'version':'2026-11-20-teaching-scope','text_hash_format':'UTF-8 with LF line endings','dissertation_sha256':sha(pdf),'source_hashes':{name:hashlib.sha256((root/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name in inputs},'briefing':(root/inputs[0]).read_text(encoding='utf-8'),'chunks':chunks}
(root/'worker/guide-sources.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print(f'Indexed {len(chunks)} excerpts from the dissertation and repository; original hashes verified.')
