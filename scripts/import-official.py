#!/usr/bin/env python3
"""Resolve official ComfyUI subgraphs offline using their pinned node schemas."""
import copy
import json
from pathlib import Path
from workflow_panels import flatten

def parse_widgets(typ,widgets,info):
    schema=info[typ]['input'];stream=iter(widgets or []);named={};aux={}
    def walk(schema,prefix=''):
        for group in ('required','optional'):
            for name,spec in schema.get(group,{}).items():
                field=prefix+name;kind=spec[0];opts=spec[1] if len(spec)>1 and isinstance(spec[1],dict) else {}
                if opts.get('hidden'):continue
                if kind=='COMFY_DYNAMICCOMBO_V3':
                    value=next(stream,opts['options'][0]['key']);named[field]=value
                    choice=next((o for o in opts['options'] if o['key']==value),opts['options'][0]);walk(choice['inputs'],field+'.');continue
                widget_type=opts.get('widgetType',kind)
                if opts.get('forceInput') or not (isinstance(widget_type,list) or widget_type in ('INT','FLOAT','STRING','BOOLEAN','COMBO')):continue
                default=opts.get('default',kind[0] if isinstance(kind,list) and kind else '')
                value=next(stream,default);named[field]=value
                if opts.get('control_after_generate'):aux['control_after_generate']=next(stream,'fixed')
    walk(schema);return named,aux

def import_ui(d,info):
    d=copy.deepcopy(d);defs={s['id']:s for s in d.get('definitions',{}).get('subgraphs',[])}
    groups=[d]+list(defs.values());raw={}
    for group in groups:
        for n in group.get('nodes',[]):
            if n['type'] in info:
                named,aux=parse_widgets(n['type'],n.get('widgets_values'),info);n['widgets_values_named']=named;raw[id(n)]=(named,aux)
    # Parent values follow proxyWidgets order, not necessarily input-slot order.
    for group in groups:
        for n in group.get('nodes',[]):
            if n['type'] not in defs:continue
            sub=defs[n['type']];nodes={str(v['id']):v for v in sub['nodes']};bindings={}
            for (target,field),value in zip(n.get('properties',{}).get('proxyWidgets',[]),n.get('widgets_values') or []):bindings[(str(target),field)]=value
            named=n.setdefault('widgets_values_named',{})
            links={l['id']:l for l in sub['links']}
            for slot in sub.get('inputs',[]):
                if slot['name'] in named:continue
                lid=next(iter(slot.get('linkIds',[])),None)
                if lid is None or lid not in links:continue
                link=links[lid];target=nodes[str(link['target_id'])];field=target['inputs'][link['target_slot']]['name']
                named[slot['name']]=bindings.get((str(target['id']),field),target.get('widgets_values_named',{}).get(field))
    flat=flatten(d);names={path:':'.join(map(str,path)) for path in flat};prompt={}
    for path,(typ,widgets,inputs) in flat.items():
        prompt[names[path]]={'class_type':typ,'inputs':{field:(val[1] if val[0]=='value' else [names[val[1]],val[2]]) for field,val in inputs.items()}}
    return prompt

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('workflow',type=Path);p.add_argument('--schemas',type=Path,default=Path('.runtime/object-info.json'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    api=import_ui(json.loads(a.workflow.read_text()),json.loads(a.schemas.read_text()));a.output.write_text(json.dumps(api,indent=2)+'\n')
