#!/usr/bin/env python3
"""Check that every image-driven workflow sizes its frame from the image and crops nothing."""
import json
import math
from pathlib import Path
from workflow_frame import HEIGHT, WIDTH
ROOT=Path(__file__).resolve().parents[1];P=next(p for p in (ROOT/'versions').iterdir() if p.is_dir())

def fitted(width,height,image_width,image_height):
    names=dict(a=width,b=height,c=image_width,d=image_height,max=max,round=round,sqrt=math.sqrt)
    return tuple(eval(e,{'__builtins__':{}},names) for e in (WIDTH,HEIGHT))

assert fitted(960,544,1920,1080)==(960,544)
assert fitted(544,960,1080,1920)==(544,960)
assert fitted(960,544,1024,1536)==(576,896)
assert fitted(960,544,3000,3000)==(736,736)

count=0
for path in sorted((P/'api').glob('*.json')):
    api=json.loads(path.read_text())
    if not any(n['class_type']=='LoadImage' for n in api.values()):continue
    fits={k for k,n in api.items() if n['inputs'].get('expression') in (WIDTH,HEIGHT)}
    assert len(fits)==2,path.name
    sizers=[n for n in api.values() if n['class_type'] in ('EmptyLTXVLatentVideo','ImageScale','SolidMask')]
    for n in api.values():
        for name,value in n['inputs'].items():
            if name in ('width','height','resize_type.width','resize_type.height'):
                # Straight from a fit, through the half-size first pass, or read back from the fitted image.
                source=api[value[0]]
                assert value[0] in fits or source['class_type']=='GetImageSize' or any(v[0] in fits for v in source['inputs'].values() if isinstance(v,list)),(path.name,n['class_type'],name)
    first=next(k for k,n in api.items() if n['class_type']=='GetImageSize' and n.get('_meta',{}).get('title')=='Size of your image')
    image=api[first]['inputs']['image'][0]
    for n in api.values():
        if n['inputs'].get('image',n['inputs'].get('input'))==[image,0]:
            assert n['inputs'].get('crop',n['inputs'].get('resize_type.crop','disabled'))=='disabled',(path.name,n['class_type'])
    count+=1
print('PASS: %d image-driven workflows fit the frame to the image and crop nothing.'%count)
