#!/usr/bin/env python3
"""Small structural checks run locally and in Actions without model downloads."""
import json,subprocess,sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=list((ROOT/'versions/2/workflows').glob('*.json'))
catalog=json.loads((ROOT/'versions/2/workflow-catalog.json').read_text())
# Four author workflows plus the adapted official LTX 2.3 examples listed in the catalog.
assert sorted(p.name for p in files)[4:]==sorted(e['file'] for e in catalog.values())
for path in files:
    d=json.loads(path.read_text())
    if 'nodes' in d:
        ids={n['id'] for n in d['nodes']}
        assert len(ids)==len(d['nodes'])
        assert all(l[1] in ids and l[3] in ids for l in d['links'])
        for sg in d.get('definitions',{}).get('subgraphs',[]):
            inner={n['id'] for n in sg['nodes']}|{-10,-20}
            assert all(l['origin_id'] in inner and l['target_id'] in inner for l in sg['links'])
        for n in d['nodes']:
            if n['type']=='LoraLoaderModelOnly' and 'sulphur' in str(n.get('widgets_values',[])):assert n['mode']==4
    else:
        for n in d.values():
            for v in n['inputs'].values():
                if isinstance(v,list):assert v[0] in d
p=json.loads((ROOT/'versions/2/profile.json').read_text())
assert sum(x['size'] for x in p['models'] if x['variant'] in ('fp8','all'))<100e9
# Hugging Face hides a gated file's hash without an accepted licence; scripts/pin-gated-models.py fetches it.
assert all(len(x['revision'])==40 and len(x['sha256'] or '')==64 for x in p['models'])
assert not any(x.get('gated') and x['variant']!='all' for x in p['models'])
gated_loras={x['file'] for x in p['models'] if x.get('gated')}
print(f'PASS: {len(files)} workflow graphs; valid links, pinned assets, default model budget <100 GB.')

# Nothing runs here, so prove each IC-LoRA graph is wired correctly: its API source and the packaged panel alike.
sys.path.insert(0,str(ROOT/'scripts'))
verify=SourceFileLoader('verify_runtime',str(ROOT/'scripts/verify-runtime.py')).load_module()
schema=json.loads((ROOT/'versions/2/node-schemas.json').read_text())
def check_wiring(name,prompt):
    for key,node in prompt.items():
        spec=schema[node['class_type']]['input'];inputs=node['inputs']
        for field in spec.get('required',{}):
            assert field in inputs or any(k.startswith(field+'.') for k in inputs),(name,key,field,'missing input')
        for field,value in inputs.items():
            if not (isinstance(value,list) and len(value)==2 and isinstance(value[0],str)):continue
            source=schema[prompt[value[0]]['class_type']]
            assert value[1]<len(source['output']),(name,key,field,'no such output')
            got=source['output'][value[1]]
            want=next((s[0] for group in spec.values() for f,s in group.items() if f==field),None)
            # Autogrow sockets such as values.a accept either number type, and an INT may feed a FLOAT.
            assert want is None or isinstance(want,list) or got in want.split(',') or (got,want)==('INT','FLOAT'),(name,key,field,got,want)
def reaches(prompt,start,target):
    seen=set();todo=[start]
    while todo:
        key=todo.pop()
        if key==target:return True
        if key not in seen:
            seen.add(key);todo+=[v[0] for v in prompt[key]['inputs'].values() if isinstance(v,list) and len(v)==2 and isinstance(v[0],str)]
    return False
loras={'crossview':(x:=next(m for m in p['models'] if 'CrossView' in m['file']))['file'],'ingredients':'ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors','relight':'ltx-2.3-22b-ic-lora-relight-1.0.safetensors','day_to_night':'ltx-2.3-22b-ic-lora-day-to-night-0.9.safetensors'}
assert set(loras.values())-{x['file']}==gated_loras and not x.get('gated')
for name,lora in loras.items():
    api_name='Sulphur_ic_lora_'+name+'.json'
    api=json.loads((ROOT/'versions/2/api'/api_name).read_text())
    panel=json.loads((ROOT/'versions/2/workflows'/catalog[api_name]['file']).read_text())
    for prompt in (api,verify.convert(panel,{})):
        check_wiring(api_name,prompt)
        of=lambda typ:[k for k,n in prompt.items() if n['class_type']==typ]
        guide,crop,guider=prompt[of('LTXAddVideoICLoRAGuide')[0]],prompt[of('LTXVCropGuides')[0]],prompt[of('CFGGuider')[0]]
        ic=prompt[of('LTXICLoRALoaderModelOnly')[0]]
        assert ic['inputs']['lora_name']==lora,api_name
        # The adapter sits under the IC-LoRA, the guided model samples, and the guide is cropped back out.
        assert prompt[ic['inputs']['model'][0]]['class_type']=='LoraLoaderModelOnly'
        assert guider['inputs']['model'][0]==of('LTXICLoRALoaderModelOnly')[0]
        assert guider['inputs']['positive'][0]==of('LTXAddVideoICLoRAGuide')[0]==crop['inputs']['positive'][0]
        assert prompt[crop['inputs']['latent'][0]]['class_type']=='LTXVSeparateAVLatent'
        assert prompt[prompt[of('VAEDecodeTiled')[0]]['inputs']['samples'][0]]['class_type']=='LTXVCropGuides'
        if name=='ingredients':
            assert prompt[guide['inputs']['image'][0]]['class_type']=='RepeatImageBatch' and not of('LoadVideo')
            assert reaches(prompt,guide['inputs']['image'][0],of('LoadImage')[0])
        else:
            # Same take: the clip guides the picture and its sound is muxed back unchanged.
            assert reaches(prompt,guide['inputs']['image'][0],of('LoadVideo')[0]) and not of('LoadImage')
            assert prompt[prompt[of('CreateVideo')[0]]['inputs']['audio'][0]]['class_type']=='TrimAudioDuration'
            if name!='relight':
                assert prompt[of('CreateVideo')[0]]['inputs']['audio']==prompt[of('LTXVAudioVAEEncode')[0]]['inputs']['audio']
                assert prompt[of('SetLatentNoiseMask')[0]]['inputs']['samples'][0]==of('LTXVAudioVAEEncode')[0]
        if name=='relight':
            ball=prompt[guide['inputs']['image'][0]]
            assert ball['class_type']=='ImageCompositeMasked' and reaches(prompt,guide['inputs']['image'][0],of('SphereLightManualNode')[0])
            # These follow Lightricks' workflow, and the default ball must agree with the default words.
            assert prompt[ball['inputs']['source'][0]]['inputs']['upscale_method']=='area'
            sphere=prompt[of('SphereLightManualNode')[0]]['inputs']
            assert (sphere['rotation'],sphere['elevation'],sphere['intensity'])==(90.0,15.0,2.0)
            assert any('low-angle sunlight from the right' in str(n['inputs'].get('text')) or 'low-angle sunlight from the right' in str(n['inputs'].get('value')) for n in prompt.values())
            assert prompt[of('LTXVConcatAVLatent')[0]]['inputs']['audio_latent'][0]==of('LTXVEmptyLatentAudio')[0] and not of('SetLatentNoiseMask')
    # Regenerating these graphs must not lose a control the packager adds.
    assert (name!='ingredients')==any(f['label']=='Exact Frame' for f in catalog[api_name]['controls']),api_name
    canvas={n['type'] for n in panel['nodes']}
    assert {n.get('title') for n in panel['nodes']}>=set(catalog[api_name]['input_labels'].values()),api_name
    assert 'LoadImage' in canvas or 'LoadVideo' in canvas,api_name
    if name=='relight':assert 'SphereLightManualNode' in canvas,'the browser only renders the ball for a node on the canvas'
    assert (lora in gated_loras)==('This one needs a licence first' in catalog[api_name]['note']),api_name
assert p['sphere_light_commit'] in (ROOT/'Dockerfile').read_text() and p['sphere_light_commit'] in (ROOT/'.runpod/Dockerfile').read_text()
assert catalog['Sulphur_ic_lora_crossview.json']['controls'][-1]['label']=='IC-LoRA strength'
print(f'PASS: {len(loras)} IC-LoRA graphs wired correctly.')

# Exercise quota-aware thread sizing without importing torch or requiring a GPU.
subprocess.run(["bash",str(ROOT/"scripts/test-cpu-threads.sh")],check=True)
subprocess.run(["python3",str(ROOT/"scripts/test_workflow_frame.py")],check=True)

# The seed extension must be present in the whitelisted Docker build context.
assert "!frontend/**" in (ROOT / ".dockerignore").read_text()
