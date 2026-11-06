"""Size the render frame from the input image, so a portrait upload is never sliced to fit."""

FIT_WIDTH = 'max(64,round(sqrt(a*b*c/d)/32)*32)'
FIT_HEIGHT = 'max(64,round(sqrt(a*b*d/c)/32)*32)'
# With Exact Frame on, e is true and the typed size stands.
WIDTH = 'a if e else ' + FIT_WIDTH
HEIGHT = 'b if e else ' + FIT_HEIGHT
EXACT_NODE = '9101'


def fit_frame(api):
    """Point every size consumer at a frame with the panel's area and the image's proportions; idempotent.

    Width and Height set the area, and so the render cost. A typed size that already matches the image
    comes back unchanged; anything else follows the image, and the first frame leads when there are two.
    add_exact_frame then adds the switch that puts the typed size back in charge.
    """
    images = [key for key, node in api.items() if node['class_type'] == 'LoadImage']
    if not images or any(node['inputs'].get('expression') in (WIDTH, FIT_WIDTH) for node in api.values()):
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
    values = {'values.a': [width, 0], 'values.b': [height, 0], 'values.c': [size, 0], 'values.d': [size, 1]}
    api[size] = {'inputs': {'image': [image, 0]}, 'class_type': 'GetImageSize', '_meta': {'title': 'Size of your image'}}
    api[fit_w] = {'inputs': {'expression': FIT_WIDTH, **values}, 'class_type': 'ComfyMathExpression', '_meta': {'title': 'Fit Frame Width'}}
    api[fit_h] = {'inputs': {'expression': FIT_HEIGHT, **values}, 'class_type': 'ComfyMathExpression', '_meta': {'title': 'Fit Frame Height'}}
    return api


def add_exact_frame(api):
    """Add the Exact Frame switch to a fitted graph, off by default; idempotent.

    On, the typed Width and Height stand and the image is centre-cropped to them. Off, the crop only
    trims rounding from a frame that already has the image's shape, so the same resize serves both.
    """
    fits = [node for node in api.values() if node['inputs'].get('expression') in (FIT_WIDTH, FIT_HEIGHT)]
    if not fits:
        return api
    for node in fits:
        node['inputs'].update(expression=WIDTH if node['inputs']['expression'] == FIT_WIDTH else HEIGHT, **{'values.e': [EXACT_NODE, 0]})
    api[EXACT_NODE] = {'inputs': {'value': False}, 'class_type': 'PrimitiveBoolean', '_meta': {'title': 'Exact Frame'}}
    getter = next((node for node in api.values() if node.get('_meta', {}).get('title') == 'Size of your image'), None)
    for node in api.values():
        if getter and node['inputs'].get('image', node['inputs'].get('input')) == getter['inputs'].get('image'):
            for key in ('crop', 'resize_type.crop'):
                if key in node['inputs']:
                    node['inputs'][key] = 'center'
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
