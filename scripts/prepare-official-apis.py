#!/usr/bin/env python3
"""Adapt pinned official LTX 2.3 examples to the Sulphur model and shot controls."""
import copy
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'versions/2'
spec=importlib.util.spec_from_file_location('official',ROOT/'scripts/import-official.py');official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
MODEL='sulphur_dev_fp8mixed.safetensors';LORA='ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors'

def prune(api):
    keep=set()
    def visit(k):
        if k in keep:return
        keep.add(k)
        for v in api[k]['inputs'].values():
            if isinstance(v,list):visit(v[0])
    for k,n in api.items():
        if n['class_type'] in ('SaveVideo','SaveAudioAdvanced'):visit(k)
    return {k:n for k,n in api.items() if k in keep}

def replace(api,key,source,out=0):
    for n in api.values():
        for f,v in n['inputs'].items():
            if v==[key,out]:n['inputs'][f]=copy.deepcopy(source)

def renumber(api):
    mapping={k:str(i+100) for i,k in enumerate(api)}
    return {mapping[k]:{'class_type':n['class_type'],'inputs':{f:[mapping[v[0]],v[1]] if isinstance(v,list) else v for f,v in n['inputs'].items()}} for k,n in api.items()}

def adapt(api,title,*,frames=241,width=960,height=544,audio_only=False,inject_distillation=False):
    api=copy.deepcopy(api)
    # Remove the optional external prompt enhancer and optional Gemma tuning.
    for k,n in list(api.items()):
        if n['class_type']=='ComfySwitchNode' and isinstance(n['inputs'].get('on_false'),str):
            n['class_type']='PrimitiveStringMultiline';n['inputs']={'value':n['inputs']['on_false']}
        if n['class_type']=='LoraLoader' and 'gemma' in str(n['inputs'].get('lora_name','')):
            replace(api,k,n['inputs']['model'],0);replace(api,k,n['inputs']['clip'],1);del api[k]
        if n['class_type']=='PreviewAudio':
            n['class_type']='SaveAudioAdvanced';n['inputs'].update(filename_prefix='audio/Sulphur',format='flac')
        i=n['inputs']
        if 'ckpt_name' in i:i['ckpt_name']=MODEL
        if 'text_encoder' in i:i['text_encoder']='gemma_3_12B_it_fp4_mixed.safetensors'
        if 'lora_name' in i:
            i['lora_name']=i['lora_name'].split('/')[-1]
            if 'distill' in i['lora_name']:i['lora_name']=LORA
        if n['class_type'] in ('LoadImage','LoadAudio'):i['image' if n['class_type']=='LoadImage' else 'audio']=''
        if n['class_type']=='LoadVideo':i['file']=''
    api=renumber(prune(api));controls={}
    values={'9000':('PrimitiveInt',width),'9001':('PrimitiveInt',height),'9002':('PrimitiveInt',frames),'9003':('PrimitiveInt',24),'9004':('PrimitiveStringMultiline','A cinematic shot with natural movement and ambient sound.'),'9005':('PrimitiveStringMultiline','blurry, low quality, distorted motion, flickering'),'9006':('PrimitiveFloat',1.0),'9007':('PrimitiveInt',42)}
    for k,(typ,value) in values.items():api[k]={'class_type':typ,'inputs':{'value':value}}
    # Source templates expose seconds; the filming interface consistently exposes frames.
    for k,n in list(api.items()):
        typ=n['class_type'];i=n['inputs']
        if typ=='ComfyMathExpression' and i.get('expression','').replace(' ','')=='a*b+1':
            replace(api,k,['9002',0],0);replace(api,k,['9002',0],1)
        if typ=='ComfyMathExpression' and i.get('expression')=='a' and i.get('values.a') in (24,25):i['values.a']=['9003',0]
        if typ=='ComfyMathExpression' and i.get('expression') in ('a/2','a / 2'):
            v=i.get('values.a')
            if v in (1280,1366,1920,1024):i['values.a']=['9000',0]
            elif v in (720,768,1088,512):i['values.a']=['9001',0]
        if typ in ('EmptyLTXVLatentVideo','LTXVEmptyLatentAudio'):
            if 'length' in i:i['length']=['9002',0]
            if 'frames_number' in i:i['frames_number']=['9002',0]
            # Preserve source half-resolution expressions where supplied.
            if isinstance(i.get('width'),(int,float)):i['width']=['9000',0]
            if isinstance(i.get('height'),(int,float)):i['height']=['9001',0]
        if typ in ('ResizeImageMaskNode','ImageScale','SolidMask'):
            for field in ('width','resize_type.width'):
                if field in i:i[field]=['9000',0]
            for field in ('height','resize_type.height'):
                if field in i:i[field]=['9001',0]
        for field in ('fps','frame_rate'):
            if field in i:i[field]=['9003',0]
        if typ=='TrimAudioDuration':
            api['9010']={'class_type':'ComfyMathExpression','inputs':{'expression':'(a-1)/b','values.a':['9002',0],'values.b':['9003',0]}}
            i['duration']=['9010',0]
        if typ=='CFGGuider':i['cfg']=['9006',0]
        if typ=='KSampler':i.update(cfg=['9006',0],seed=['9007',0])
        if typ=='RandomNoise':i['noise_seed']=['9007',0]
        if typ=='LTXVConditioning':
            for field,control in (('positive','9004'),('negative','9005')):
                ref=i.get(field)
                if isinstance(ref,list) and api[ref[0]]['class_type']=='CLIPTextEncode':api[ref[0]]['inputs']['text']=[control,0]
        if typ.startswith('Save'):i['filename_prefix']=('audio/' if 'Audio' in typ else 'video/')+'Sulphur_'+title.replace(' ','_')
    if inject_distillation:
        model=next(k for k,n in api.items() if n['class_type']=='CheckpointLoaderSimple')
        for n in list(api.values()):
            for f,v in n['inputs'].items():
                if v==[model,0]:n['inputs'][f]=['9011',0]
        api['9011']={'class_type':'LoraLoaderModelOnly','inputs':{'model':[model,0],'lora_name':LORA,'strength_model':0.7}}
    # Ensure the saved result has the dimensions the filmmaker selected.
    if not audio_only:
        for n in list(api.values()):
            if n['class_type']=='CreateVideo':
                api['9012']={'class_type':'ImageScale','inputs':{'image':n['inputs']['images'],'upscale_method':'bilinear','width':['9000',0],'height':['9001',0],'crop':'disabled'}}
                n['inputs']['images']=['9012',0]
    api=prune(api)
    used={v[0] for n in api.values() for v in n['inputs'].values() if isinstance(v,list)}
    labels={'9000':'Width','9001':'Height','9002':'Frames (8n + 1)','9003':'FPS','9005':'Negative prompt','9006':'CFG','9007':'Seed'}
    fields=[{'label':labels[k],'source':int(k)} for k in labels if k in used]
    return api,fields

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--schemas',type=Path,default=ROOT/'.runtime/object-info.json');args=parser.parse_args();info=json.loads(args.schemas.read_text())
    catalog=json.loads((P/'workflow-catalog.json').read_text()) if (P/'workflow-catalog.json').exists() else {}
    sources=[('video_ltx2_3_flf2v','05','First and Last Frame to Video',True),('video_ltx2_3_ia2v','06','Image and Audio to Video',False)]
    for source,number,title,inject in sources:
        path=P/'upstream/official'/f'{source}.json'
        api=official.import_ui(json.loads(path.read_text()),info);api,fields=adapt(api,title,inject_distillation=inject)
        name=f'Sulphur_{source}.json';(P/'api'/name).write_text(json.dumps(api,indent=2)+'\n')
        catalog[name]={'title':title,'file':f'{number}_Sulphur_{title.replace(" ","_")}.json','prompt_id':9004,'controls':fields,'source':source}
        used={n['class_type'] for n in api.values()};existing=json.loads((P/'node-schemas.json').read_text());existing.update({k:{f:info[k][f] for f in ('input','input_order','output','output_name','output_node') if f in info[k]} for k in used});(P/'node-schemas.json').write_text(json.dumps(existing,indent=2)+'\n')
    (P/'workflow-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
