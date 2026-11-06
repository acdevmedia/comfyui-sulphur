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
    assert matches,'No existing template; create it in Runpod first'
    # GraphQL, like the other packages: REST PATCH wrongly refuses public templates over registry credentials.
    source=json.loads((ROOT/'.runpod/template-source.json').read_text())
    value={'id':matches[0]['id'],'name':payload['name'],'imageName':payload['imageName'],'containerDiskInGb':payload['containerDiskInGb'],'volumeInGb':0,'volumeMountPath':payload['volumeMountPath'],'isPublic':payload['isPublic'],'isServerless':False,'dockerArgs':'','ports':','.join(payload['ports']),'portsConfig':[{'port':x.split('/')[0],'name':{'8188':'ComfyUI','3923':'Copyparty'}[x.split('/')[0]]} for x in payload['ports']],'env':[{'key':k,'value':v} for k,v in payload['env'].items()],'readme':payload['readme'],'category':'NVIDIA','startJupyter':source['startJupyter'],'startSsh':source['startSsh']}
    req=urllib.request.Request('https://api.runpod.io/graphql',data=json.dumps({'query':'mutation($input: SaveTemplateInput!) { saveTemplate(input:$input) { id name imageName } }','variables':{'input':value}}).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=45) as response:result=json.load(response)
    if result.get('errors'):raise RuntimeError([e['message'][-200:] for e in result['errors']])
    print(json.dumps(result['data']['saveTemplate'],indent=2))
if __name__=='__main__':main()
