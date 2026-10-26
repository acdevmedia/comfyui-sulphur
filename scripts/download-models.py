#!/usr/bin/env python3
"""Resumable, pinned single-file downloads directly into persistent model folders."""
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from huggingface_hub import hf_hub_download
APP=Path('/opt/sulphur')
profile=json.loads((APP/'versions/2/profile.json').read_text())
variant=os.getenv('SULPHUR_MODEL_VARIANT','fp8')
if variant not in ('fp8','bf16','native-distilled'):raise SystemExit('Unknown SULPHUR_MODEL_VARIANT; choose fp8, bf16, native-distilled.')
root=Path('/workspace/runpod-slim/ComfyUI/models');root.mkdir(parents=True,exist_ok=True)
selected=[m for m in profile['models'] if m['variant'] in (variant,'all')]
missing=sum(max(0,m['size']-(root/m['directory']/Path(m['file']).name).stat().st_size) if (root/m['directory']/Path(m['file']).name).exists() else m['size'] for m in selected)
free=shutil.disk_usage(root).free
print(f'[models] Profile {variant}: {sum(m["size"] for m in selected)/1e9:.2f} GB required; {missing/1e9:.2f} GB missing; {free/1e9:.2f} GB free.',flush=True)
if free<missing+10*10**9:raise SystemExit('[models] ERROR: Insufficient persistent disk space. Free space or increase the /workspace volume; 10 GB output reserve is required.')
for index,m in enumerate(selected,1):
    dest=root/m['directory'];dest.mkdir(exist_ok=True,parents=True)
    target=dest/Path(m['file']).name
    marker=target.with_suffix('.verified.json')
    signature={'sha256':m['sha256'],'size':m['size']}
    if target.exists() and target.stat().st_size==m['size'] and marker.exists() and json.loads(marker.read_text())==signature:
        print(f'[models {index}/{len(selected)}] Reusing verified {target.name}; no network download.',flush=True);continue
    start=time.monotonic()
    print(f'[models {index}/{len(selected)}] Fetching/verifying {target.name} ({m["size"]/1e9:.2f} GB). Interrupted downloads resume on restart. Progress below is download progress, not video generation.',flush=True)
    # local_dir uses .cache/huggingface metadata and partials without a second blob copy.
    path=Path(hf_hub_download(repo_id=m['repo'],filename=m['file'],revision=m['revision'],local_dir=dest,token=os.getenv('HF_TOKEN') or None))
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(16*1024*1024),b''):digest.update(block)
    if path.stat().st_size!=m['size'] or digest.hexdigest()!=m['sha256']:
        path.unlink(missing_ok=True);raise SystemExit(f'[models] ERROR: Integrity check failed for {target.name}; restart to retry.')
    if path!=target:path.replace(target)
    marker.write_text(json.dumps(signature))
    print(f'[models] SHA256 verified {target.name}; elapsed {time.monotonic()-start:.1f}s.',flush=True)
# Install versioned workflows once. Preserve all user edits across restarts.
workflows=Path('/workspace/runpod-slim/ComfyUI/user/default/workflows/Sulphur/2');workflows.mkdir(parents=True,exist_ok=True)
ckpt=next(m for m in selected if m['variant']==variant)['file']
for src in (APP/'versions/2/workflows').glob('*.json'):
    target=workflows/src.name
    if target.exists():continue
    text=src.read_text().replace('sulphur_dev_fp8mixed.safetensors',ckpt)
    d=json.loads(text)
    if variant=='native-distilled':
        if 'BASE' in src.name:continue
        # This checkpoint already contains distillation. Never stack another distill LoRA.
        if 'nodes' in d:
            for n in d['nodes']:
                if n['type']=='LoraLoaderModelOnly':n['mode']=4
        else:
            for key in list(d):
                if d[key]['class_type']=='LoraLoaderModelOnly':
                    source=d[key]['inputs']['model']
                    for node in d.values():
                        for field,val in node['inputs'].items():
                            if val==[key,0]:node['inputs'][field]=source
                    del d[key]
    target.write_text(json.dumps(d,indent=2)+'\n')
    print(f'[workflows] Installed {target.name}; your existing workflows are preserved.',flush=True)
print('[models] Model preparation complete. ComfyUI starts next.',flush=True)
