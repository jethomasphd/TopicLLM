"""Package the current source and a built wheel; never include local credentials/runs."""
from pathlib import Path
import hashlib, json, shutil, subprocess, zipfile, tomllib
root=Path(__file__).resolve().parents[1]
out=root/'docs/downloads';out.mkdir(parents=True,exist_ok=True)
version=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
wheels=sorted((root/'dist_wheels').glob(f'topicllm_research-{version}-*.whl'))
if len(wheels)!=1:raise SystemExit('Build exactly one wheel for the declared release version into dist_wheels first.')
shutil.copy2(wheels[0],out/wheels[0].name)
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
with zipfile.ZipFile(out/'topicllm-research-source.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for name in sorted(set(files)):
        if not name:continue
        path=root/name
        if not path.is_file() or name.startswith(('docs/downloads/','dist/','dist_wheels/','build/')):continue
        if any(part in ['node_modules','.git','.wrangler','.venv','__pycache__','private','runs'] or part.startswith('.env') or part.startswith('.dev.vars') for part in Path(name).parts):continue
        if path.suffix in ('.key','.pem','.sqlite','.pyc','.pkl'):continue
        info=zipfile.ZipInfo('TopicLLM/'+name,(2026,11,17,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        archive.writestr(info,path.read_bytes())
manifest={'package_version':version,'files':[{ 'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in [out/wheels[0].name]],
          'source_archive':{'url':'https://github.com/jethomasphd/TopicLLM/archive/refs/heads/main.zip','description':'GitHub snapshot of the current main branch; record its commit when beginning a run.'}}
(out/'download-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,indent=2))
