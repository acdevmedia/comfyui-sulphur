#!/usr/bin/env python3
"""CPU-only boot smoke check inside the Actions build; no models or GPU needed."""
import json
import subprocess
import time
import urllib.request
from pathlib import Path
from importlib.machinery import SourceFileLoader
verify=SourceFileLoader('verify_runtime','/opt/sulphur/scripts/verify-runtime.py').load_module()
with open('/tmp/comfy-build-check.log','w') as log:
    proc=subprocess.Popen(['python3','main.py','--cpu','--listen','127.0.0.1','--port','18188'],cwd='/opt/comfyui-baked',stdout=log,stderr=subprocess.STDOUT)
    try:
        for _ in range(120):
            if proc.poll() is not None:raise RuntimeError('ComfyUI exited before readiness')
            try:
                info=verify.request('http://127.0.0.1:18188','/object_info');break
            except Exception:time.sleep(1)
        else:raise RuntimeError('ComfyUI CPU smoke check timed out')
        for path in Path('/opt/sulphur/versions/2/workflows').glob('*.json'):
            prompt=verify.convert(json.loads(path.read_text()),info)
            for key,node in prompt.items():
                assert node['class_type'] in info,(path.name,node['class_type'])
                required=info[node['class_type']]['input'].get('required',{})
                assert all(k in node['inputs'] or any(i.startswith(k+'.') for i in node['inputs']) for k in required),(path.name,key,set(required)-set(node['inputs']))
            print('[build] CPU server started; workflow nodes and required inputs verified:',path.name,flush=True)
    finally:
        proc.terminate()
        try:proc.wait(timeout=20)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        print(Path('/tmp/comfy-build-check.log').read_text())
