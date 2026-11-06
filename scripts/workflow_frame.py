"""Size the render frame from the input image, so a portrait upload is never sliced to fit."""

WIDTH = 'max(64,round(sqrt(a*b*c/d)/32)*32)'
HEIGHT = 'max(64,round(sqrt(a*b*d/c)/32)*32)'


def fit_frame(api):
    """Point every size consumer at a frame with the panel's area and the image's proportions; idempotent.

    Width and Height set the area, and so the render cost. A typed size that already matches the image
    comes back unchanged; anything else follows the image, and the first frame leads when there are two.
    """
    images = [key for key, node in api.items() if node['class_type'] == 'LoadImage']
    if not images or any(node['inputs'].get('expression') == WIDTH for node in api.values()):
        return api
    image = '130' if '130' in images else images[0]
    width, height = ('40', '25') if '40' in api else ('9000', '9001')
    size, fit_w, fit_h = (str(max(map(int, api)) + offset) for offset in (1, 2, 3))
    for node in api.values():
        for name, value in node['inputs'].items():
            if value == [width, 0]:
                node['inputs'][name] = [fit_w, 1]
            elif value == [height, 0]:
                node['inputs'][name] = [fit_h, 1]
        # The frame already has the image's proportions, so its resize has nothing left to crop.
        source = node['inputs'].get('image', node['inputs'].get('input'))
        if source == [image, 0]:
            for key in ('crop', 'resize_type.crop'):
                if key in node['inputs']:
                    node['inputs'][key] = 'disabled'
    values = {'values.a': [width, 0], 'values.b': [height, 0], 'values.c': [size, 0], 'values.d': [size, 1]}
    api[size] = {'inputs': {'image': [image, 0]}, 'class_type': 'GetImageSize', '_meta': {'title': 'Size of your image'}}
    api[fit_w] = {'inputs': {'expression': WIDTH, **values}, 'class_type': 'ComfyMathExpression', '_meta': {'title': 'Fit Frame Width'}}
    api[fit_h] = {'inputs': {'expression': HEIGHT, **values}, 'class_type': 'ComfyMathExpression', '_meta': {'title': 'Fit Frame Height'}}
    return api


TRANSITION = 'ltx2.3-transition.safetensors'
TRANSITION_NODE = '9100'


def add_transition_lora(api):
    """Add the scene transition LoRA after the model's own, off at strength 0; idempotent."""
    if TRANSITION_NODE in api:
        return api
    tail = next(key for key, node in api.items() if node['class_type'] == 'LoraLoaderModelOnly')
    for node in api.values():
        if node['inputs'].get('model') == [tail, 0]:
            node['inputs']['model'] = [TRANSITION_NODE, 0]
    api[TRANSITION_NODE] = {'inputs': {'model': [tail, 0], 'lora_name': TRANSITION, 'strength_model': 0.0},
                            'class_type': 'LoraLoaderModelOnly', '_meta': {'title': 'Scene transition LoRA'}}
    return api
