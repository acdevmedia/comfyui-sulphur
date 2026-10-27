#!/usr/bin/env python3
"""Small structural checks run locally and in Actions without model downloads."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=list((ROOT/'versions/2/workflows').glob('*.json'))
assert len(files)==4
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
assert all(len(x['sha256'])==64 and len(x['revision'])==40 for x in p['models'])
print('PASS: four workflow graphs; valid links, pinned assets, default model budget <100 GB.')
