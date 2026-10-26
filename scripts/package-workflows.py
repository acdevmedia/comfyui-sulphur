#!/usr/bin/env python3
"""Apply documented compatibility repairs; preserve author graphs and controls."""
import copy
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'versions/2'
CKPT = 'sulphur_dev_fp8mixed.safetensors'
LORA = 'ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors'

def repair_ui(d):
    for n in d['nodes']:
        typ = n['type']; w = n.get('widgets_values', [])
        if typ in ('CheckpointLoaderSimple', 'LTXVAudioVAELoader'): w[0] = CKPT
        if typ == 'LTXAVTextEncoderLoader': w[1] = CKPT
        if typ == 'LoraLoaderModelOnly':
            if 'sulphur' in w[0]: n['mode'] = 4
            w[0] = LORA
        if typ == 'LatentUpscaleModelLoader': w[0] = 'ltx-2.3-spatial-upscaler-x2-1.1.safetensors'
        if typ == 'PathchSageAttentionKJ': n['mode'] = 4
        if typ == 'VAELoader' and w[0] == 'taeltx2_3.safetensors':
            n['mode'] = 2  # unused tiny preview VAE; full VAE remains available below
        if typ == 'PrimitiveInt' and n['id'] in (25,40):
            w[0] = 544 if n['id'] == 25 else 960
        if typ == 'ResizeImageResolution':
            n['type'] = 'ImageScale'; n['widgets_values'] = ['lanczos',960,544,'center']
        if typ == 'ImageScaleDownBy':
            n['type'] = 'ImageScaleBy'; n['widgets_values'] = ['lanczos',0.5]
            n['inputs'][0]['name'] = 'image'
        if typ == 'LTX2SamplingPreviewOverride':
            for slot in n.get('inputs',[]):
                if slot['name'] == 'vae' and slot.get('link') is not None:
                    for link in d['links']:
                        if link[0] == slot['link']: link[1:3] = [44,2]
    # LTX floors half-height 272 to 256 internally. Normalize decoded frames
    # to the requested final size without adding a separate upscaling pipeline.
    nid=max(n['id'] for n in d['nodes'])+1
    lid=max(l[0] for l in d['links'])+1
    incoming=next(l for l in d['links'] if l[3]==38 and l[4]==0)
    incoming[3:5]=[nid,0]
    d['nodes'].append({'id':nid,'type':'ImageScale','pos':[2600,500],'size':[300,180],
        'flags':{},'order':len(d['nodes']),'mode':0,'title':'Requested final dimensions',
        'inputs':[{'name':'image','type':'IMAGE','link':incoming[0]},
                  {'name':'width','type':'INT','widget':{'name':'width'},'link':lid+1},
                  {'name':'height','type':'INT','widget':{'name':'height'},'link':lid+2}],
        'outputs':[{'name':'IMAGE','type':'IMAGE','links':[lid]}],
        'properties':{'Node name for S&R':'ImageScale'},
        'widgets_values':['lanczos',960,544,'disabled']})
    d['links'].extend([[lid,nid,0,38,0,'IMAGE'],[lid+1,40,0,nid,1,'INT'],[lid+2,25,0,nid,2,'INT']])
    next(n for n in d['nodes'] if n['id']==38)['inputs'][0]['link']=lid
    d['last_node_id']=nid;d['last_link_id']=lid+2
    # Rebuild output link lists after rewiring the optional preview VAE.
    for n in d['nodes']:
        for i,o in enumerate(n.get('outputs',[])):
            o['links'] = [l[0] for l in d['links'] if l[1] == n['id'] and l[2] == i]
    return d

for name in ('i2v base','t2v base','t2v distilled'):
    d=repair_ui(json.loads((P/'upstream'/f'{name}.json').read_text()))
    (P/'workflows'/('Sulphur_'+name.replace(' ','_').upper()+'.json')).write_text(json.dumps(d,indent=2)+'\n')
# Upstream I2V distilled is an API graph. Keep that format and its complete inputs.
d=json.loads((P/'upstream/i2v distilled.json').read_text())
for k,n in d.items():
    typ=n['class_type']; i=n['inputs']
    for key in ('ckpt_name',):
        if key in i:i[key]=CKPT
    if typ=='LatentUpscaleModelLoader':i['model_name']='ltx-2.3-spatial-upscaler-x2-1.1.safetensors'
    if typ=='ResizeImageResolution':
        n['class_type']='ImageScale'; n['inputs']={'image':i['image'],'upscale_method':'lanczos','width':960,'height':544,'crop':'center'}
    if typ=='ImageScaleDownBy':
        n['class_type']='ImageScaleBy';n['inputs']={'image':i['images'],'upscale_method':'lanczos','scale_by':0.5}
# Bypass baked-in fine tuning and graph attention overrides; global CLI selects backend.
for key in ('46','60','74'):
    source=d[key]['inputs']['model']
    for node in d.values():
        for field,val in node['inputs'].items():
            if val==[key,0]:node['inputs'][field]=copy.deepcopy(source)
    del d[key]
# An unused, incomplete decode node is exported by upstream; API validation rejects it.
for key in ('43','58','65'):d.pop(key,None)
d['75']={'class_type':'ImageScale','inputs':{'image':d['38']['inputs']['images'],'upscale_method':'lanczos','width':['40',0],'height':['25',0],'crop':'disabled'}}
d['38']['inputs']['images']=['75',0]
(P/'workflows/Sulphur_I2V_DISTILLED.json').write_text(json.dumps(d,indent=2)+'\n')
