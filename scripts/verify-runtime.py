#!/usr/bin/env python3
"""Check installed workflow nodes/models against a running ComfyUI server.

Also converts UI graphs to API prompts for repeatable smoke tests. No prompts
are queued unless --generate is supplied. An image must be supplied for I2V.
"""
import argparse
import copy
import json
import time
import urllib.request
from pathlib import Path

def request(base,path,data=None):
    req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)

def convert(d,info):
    if 'nodes' not in d:
        prompt=copy.deepcopy(d)
        keep=set()
        def visit_api(key):
            if key in keep:return
            keep.add(key)
            for val in prompt[key]['inputs'].values():
                if isinstance(val,list) and len(val)==2 and isinstance(val[0],str) and val[0] in prompt:visit_api(val[0])
        for key,node in prompt.items():
            if info[node['class_type']].get('output_node'):visit_api(key)
        return {k:v for k,v in prompt.items() if k in keep}
    nodes={str(n['id']):n for n in d['nodes']}
    links={l[0]:l for l in d['links']}
    def source(link_id):
        link=links[link_id];n=nodes[str(link[1])]
        if n['type']=='Reroute':return source(n['inputs'][0]['link'])
        if n.get('mode',0)==4:
            candidates=[i for i in n.get('inputs',[]) if i['type']==link[5] and i.get('link') is not None]
            if not candidates:raise ValueError(f'Cannot bypass node {n["id"]}')
            return source(candidates[0]['link'])
        assert n.get('mode',0)!=2,f'Muted node {n["id"]} is connected'
        return [str(link[1]),link[2]]
    prompt={}
    for key,n in nodes.items():
        if n.get('mode',0) in (2,4) or n['type']=='Reroute':continue
        typ=n['type'];schema=info[typ]['input'];widgets=iter(n.get('widgets_values',[]));inputs={}
        connected={i['name']:i for i in n.get('inputs',[]) if i.get('link') is not None}
        for group in ('required','optional'):
            for field,spec in schema.get(group,{}).items():
                kind=spec[0];opts=spec[1] if len(spec)>1 and isinstance(spec[1],dict) else {}
                widget_kind=opts.get('widgetType',kind)
                is_widget=(isinstance(widget_kind,list) or widget_kind in ('INT','FLOAT','STRING','BOOLEAN','COMBO')) and not opts.get('forceInput')
                if is_widget:
                    val=next(widgets,None)
                    if field not in connected and val is not None:inputs[field]=val
                    if opts.get('control_after_generate') or (typ=='RandomNoise' and field=='noise_seed') or (typ=='PrimitiveInt' and field=='value'):
                        next(widgets,None)
                if field in connected:inputs[field]=source(connected[field]['link'])
        # Dynamic ComfyMathExpression sockets do not appear in the fixed schema.
        for field,slot in connected.items():inputs[field]=source(slot['link'])
        if typ=='SaveVideo':
            saved=n.get('widgets_values',[])
            inputs.update(filename_prefix=saved[0],format=saved[1])
            inputs['format.codec']=saved[2]
            inputs.pop('codec',None)
        prompt[key]={'class_type':typ,'inputs':inputs}
    # Only send nodes contributing to actual outputs, excluding unused author experiments.
    keep=set()
    def visit(key):
        if key in keep:return
        keep.add(key)
        for val in prompt[key]['inputs'].values():
            if isinstance(val,list) and len(val)==2 and isinstance(val[0],str) and val[0] in prompt:visit(val[0])
    for key,node in prompt.items():
        if info[node['class_type']].get('output_node'):visit(key)
    return {k:v for k,v in prompt.items() if k in keep}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default='http://127.0.0.1:8188')
    p.add_argument('--workflows',type=Path,default=Path('/opt/sulphur/versions/2/workflows'))
    p.add_argument('--generate',choices=['I2V','T2V'])
    p.add_argument('--image',help='Existing filename in ComfyUI input directory')
    p.add_argument('--frames',type=int,default=25)
    p.add_argument('--output',type=Path,default=Path('/workspace/logs/sulphur-validation.json'))
    args=p.parse_args();info=request(args.url,'/object_info');stats=request(args.url,'/system_stats');results={'system':stats,'workflows':{}}
    for path in sorted(args.workflows.glob('*.json')):
        d=json.loads(path.read_text());prompt=convert(d,info)
        for key,node in prompt.items():
            assert node['class_type'] in info,(path.name,node['class_type'])
            schema=info[node['class_type']]['input']
            for group in ('required','optional'):
                for field,spec in schema.get(group,{}).items():
                    if group=='required':assert field in node['inputs'] or any(k.startswith(field+'.') for k in node['inputs']),(path.name,key,field,'missing input')
                    val=node['inputs'].get(field)
                    if node['class_type']=='LoadImage' and field=='image':continue  # users supply their own image
                    if isinstance(spec[0],list) and val is not None and not isinstance(val,list):
                        assert val in spec[0],(path.name,key,field,val,'model/option not available')
        print('[runtime] Nodes, required inputs and model choices verified:',path.name,flush=True)
        results['workflows'][path.name]={'nodes_and_models':'passed'}
        if args.generate and args.generate in path.name and 'DISTILLED' in path.name:
            assert args.frames%8==1,'LTX requires 8n+1 frames'
            for node in prompt.values():
                if node['class_type']=='LoadImage':
                    assert args.image,'Pass --image for I2V';node['inputs']['image']=args.image
                if node['class_type']=='PrimitiveStringMultiline':node['inputs']['value']='A small sailboat drifts across a calm lake at sunrise. Gentle wind and quiet water sounds. A steady cinematic wide shot.'
                if node['class_type']=='PrimitiveInt' and node['inputs'].get('value')==241:node['inputs']['value']=args.frames
            start=time.monotonic();queued=request(args.url,'/prompt',{'prompt':prompt});pid=queued['prompt_id']
            print('[generation] Queued',pid,'frames',args.frames,flush=True)
            deadline=start+3600
            while time.monotonic()<deadline:
                history=request(args.url,'/history/'+pid)
                if pid in history:
                    result=history[pid];assert result['status']['status_str']=='success',result['status']
                    results['workflows'][path.name].update(elapsed_seconds=time.monotonic()-start,history=result)
                    print('[generation] Completed in',round(time.monotonic()-start,2),'seconds',flush=True);break
                time.sleep(10)
            else:raise TimeoutError('GPU generation did not complete in one hour')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(results,indent=2)+'\n')
    print('[runtime] Results saved:',args.output)
if __name__=='__main__':main()
