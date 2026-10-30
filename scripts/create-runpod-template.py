#!/usr/bin/env python3
"""Create/update the Sulphur 2 template. Never sends local GitHub credentials."""
import argparse
import json
import os
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    payload=json.loads((ROOT/'config/runpod-template.json').read_text())
    payload['readme']=(ROOT/'README.md').read_text()+'\n\n'+(ROOT/'docs/runpod-environment.md').read_text()
    if args.dry_run:print(json.dumps(payload,indent=2));return
    values={}
    if (ROOT/'.env').exists():
        for line in (ROOT/'.env').read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1);values[k.strip()]=v.strip().strip('\"\'')
    key=os.getenv('RUNPOD_API_KEY') or values.get('RUNPOD_API_KEY');assert key,'RUNPOD_API_KEY is required'
    def request(path,method='GET',data=None):
        req=urllib.request.Request('https://rest.runpod.io/v1'+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'curl/8.0'})
        with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
    matches=[t for t in request('/templates') if t['name'] in (payload['name'],'Sulfur 2 LTX 2.3 ComfyUI Video One-Click','Sulphur 2 — ComfyUI SageAttention')]
    assert len(matches)<=1,'Duplicate templates found; refusing ambiguous update'
    update={k:v for k,v in payload.items() if k not in ('category','isServerless')}
    result=request('/templates/'+matches[0]['id'],'PATCH',update) if matches else request('/templates','POST',payload)
    print(json.dumps({k:result.get(k) for k in ('id','name','imageName','containerDiskInGb','volumeInGb','volumeMountPath','ports')},indent=2))
if __name__=='__main__':main()
