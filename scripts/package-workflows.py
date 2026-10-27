#!/usr/bin/env python3
"""Build genuine ComfyUI UI graphs with a compact native shot-settings panel."""
import copy
import json
from pathlib import Path
from workflow_panels import fold_into_panel
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'versions/2'
SCHEMA=json.loads((P/'node-schemas.json').read_text())
PRIMITIVES={'INT','FLOAT','STRING','BOOLEAN','COMBO'}

def fields(schema,values,prefix=''):
    for group in ('required','optional'):
        for name,spec in schema.get(group,{}).items():
            name=prefix+name;kind=spec[0];options=spec[1] if len(spec)>1 and isinstance(spec[1],dict) else {}
            if kind=='COMFY_DYNAMICCOMBO_V3':
                value=values.get(name,options['options'][0]['key'])
                yield name,['COMBO',{'options':[o['key'] for o in options['options']]}],value,True
                choice=next(o for o in options['options'] if o['key']==value)
                yield from fields(choice['inputs'],values,name+'.')
            elif kind=='COMFY_AUTOGROW_V3':
                template=next(iter(options['template']['input']['required'].values()))
                for key,value in values.items():
                    if key.startswith(name+'.'):yield key,template,value,False
            else:
                widget=not options.get('forceInput') and (isinstance(kind,list) or options.get('widgetType',kind) in PRIMITIVES)
                if name in values:value=values[name]
                elif 'default' in options:value=options['default']
                elif isinstance(kind,list):value=kind[0] if kind else ''
                elif kind=='COMBO':value=options.get('options',[''])[0] if options.get('options') else ''
                else:value={'INT':0,'FLOAT':0.0,'STRING':'','BOOLEAN':False}.get(options.get('widgetType',kind))
                if group=='optional' and name not in values and not widget:continue
                if options.get('hidden'):continue
                yield name,spec,value,widget

def to_ui(api,title):
    api=copy.deepcopy(api)
    next_id=max(map(int,api))+1
    for source in list(api.values()):
        typ=source['class_type']
        for field,spec,value,widget in list(fields(SCHEMA[typ]['input'],source['inputs'])):
            if field in source['inputs'] and not widget and value is not None and not isinstance(value,list):
                kind='PrimitiveBoolean' if isinstance(value,bool) else 'PrimitiveInt' if isinstance(value,int) else 'PrimitiveFloat' if isinstance(value,float) else 'PrimitiveStringMultiline' if isinstance(value,str) else None
                if kind:
                    key=str(next_id);next_id+=1;api[key]={'class_type':kind,'inputs':{'value':value}};source['inputs'][field]=[key,0]
    d={'id':title,'last_node_id':max(map(int,api)),'last_link_id':0,'nodes':[],'links':[],'groups':[],'config':{},'extra':{'ds':{'scale':0.75,'offset':[20,70]}},'version':0.4}
    nodes={};pending=[]
    for order,(key,source) in enumerate(api.items()):
        typ=source['class_type'];schema=SCHEMA[typ]
        n={'id':int(key),'type':typ,'pos':[(order%6)*350,(order//6)*300],'size':[310,160],'flags':{},'order':order,'mode':0,'inputs':[],'outputs':[],'properties':{'Node name for S&R':typ},'widgets_values':[],'widgets_values_named':{}}
        for field,spec,value,widget in fields(schema['input'],source['inputs']):
            options=spec[1] if len(spec)>1 and isinstance(spec[1],dict) else {};kind=spec[0]
            slot={'name':field,'type':'COMBO' if isinstance(kind,list) else kind,'link':None}
            if widget:slot['widget']={'name':field}
            n['inputs'].append(slot)
            if widget:
                fallback=options.get('default',0 if kind in ('INT','FLOAT') else '' if kind=='STRING' else False if kind=='BOOLEAN' else kind[0] if isinstance(kind,list) and kind else '')
                n['widgets_values'].append(fallback if isinstance(value,list) else value)
                n['widgets_values_named'][field]=fallback if isinstance(value,list) else value
                if options.get('control_after_generate'):n['widgets_values'].append('fixed')
            if isinstance(value,list):pending.append((n, len(n['inputs'])-1,value))
        for i,kind in enumerate(schema.get('output',[])):
            name=schema.get('output_name',schema['output'])[i]
            n['outputs'].append({'name':name,'type':kind,'links':[]})
        nodes[int(key)]=n;d['nodes'].append(n)
    for n,slot,value in pending:
        source,out=int(value[0]),value[1];lid=len(d['links'])+1;kind=nodes[source]['outputs'][out]['type']
        d['links'].append([lid,source,out,n['id'],slot,kind]);n['inputs'][slot]['link']=lid;nodes[source]['outputs'][out]['links'].append(lid)
    d['last_link_id']=len(d['links'])
    return d

def package(path):
    catalog=json.loads((P/'workflow-catalog.json').read_text()) if (P/'workflow-catalog.json').exists() else {}
    if path.name in catalog:return package_extra(path,catalog[path.name])
    api=json.loads(path.read_text());title=('Image to Video' if 'I2V' in path.name else 'Text to Video')+' — '+('Distilled' if 'DISTILLED' in path.name else 'Base')
    d=to_ui(api,title);nodes={n['id']:n for n in d['nodes']}
    # Keep input selection, the prompt and the finished video on the canvas.
    keep={n['id'] for n in d['nodes'] if n['type'] in ('LoadImage','SaveVideo','PrimitiveStringMultiline')}
    nodes[29].update(title='Prompt — describe the shot',size=[500,230])
    if 67 in nodes:nodes[67].update(title='Starting image — upload your own',size=[340,350])
    fields_to_expose=[{'label':'Width','source':40},{'label':'Height','source':25},{'label':'Frames (8n + 1)','source':27},{'label':'FPS','source':26},
        {'label':'Seed','kind':'PrimitiveInt','targets':[(2,'noise_seed')]},
        {'label':'Refinement seed','kind':'PrimitiveInt','targets':[(1,'noise_seed')]},
        {'label':'CFG','kind':'PrimitiveFloat','targets':[(42,'cfg')]},
        {'label':'Refinement CFG','kind':'PrimitiveFloat','targets':[(8,'cfg')]},
        {'label':'Sampling steps','kind':'PrimitiveInt','targets':[(47,'steps')]},
        {'label':'Negative prompt','kind':'PrimitiveStringMultiline','targets':[(41,'text')]}]
    fold_into_panel(d,'Shot settings — '+title,keep,fields_to_expose)
    for n in d['nodes']:
        if n['type']=='PrimitiveStringMultiline':n['pos']=[0,0]
        elif n['type']=='LoadImage':n['pos']=[0,310]
        elif n['type']=='SaveVideo':n.update(pos=[1110,0],size=[580,540],title='Finished video — preview and download')
        else:n.update(pos=[550,0],size=[500,680],color='#24364b',bgcolor='#172331')
    d['groups']=[]
    output_name={'Sulphur_I2V_DISTILLED.json':'01_Sulphur_Image_to_Video_Distilled.json','Sulphur_T2V_DISTILLED.json':'02_Sulphur_Text_to_Video_Distilled.json','Sulphur_I2V_BASE.json':'03_Sulphur_Image_to_Video_Base.json','Sulphur_T2V_BASE.json':'04_Sulphur_Text_to_Video_Base.json'}[path.name]
    (P/'workflows'/output_name).write_text(json.dumps(d,indent=2)+'\n')

def package_extra(path,entry):
    api=json.loads(path.read_text());d=to_ui(api,entry['title']);nodes={n['id']:n for n in d['nodes']}
    keep_types={'LoadImage','LoadVideo','LoadAudio','SaveVideo','SaveAudioAdvanced','LTXVSparseTrackEditor'}
    keep={n['id'] for n in d['nodes'] if n['type'] in keep_types}
    prompt_id=entry.get('prompt_id')
    if prompt_id is not None:keep.add(prompt_id)
    for key,label in entry.get('input_labels',{}).items():nodes[int(key)]['title']=label
    if prompt_id in nodes:nodes[prompt_id].update(title='Prompt — describe the result',size=[500,200])
    fold_into_panel(d,'Shot settings — '+entry['title'],keep,entry['controls'])
    input_y=250
    for n in d['nodes']:
        if n['id']==prompt_id:n['pos']=[0,0]
        elif n['type'] in ('LoadImage','LoadVideo','LoadAudio','LTXVSparseTrackEditor'):
            n['pos']=[0,input_y];n['size']=[390,250];input_y+=300
        elif n['type'].startswith('Save'):
            n['pos']=[1110,0];n['size']=[580,540];n['title']='Finished result — preview and download'
        else:n.update(pos=[550,0],size=[500,640],color='#24364b',bgcolor='#172331')
    d['groups']=[]
    (P/'workflows'/entry['file']).write_text(json.dumps(d,indent=2)+'\n')

if __name__=='__main__':
    for path in sorted((P/'api').glob('*.json')):package(path)
