#!/usr/bin/env python3
"""Build the IC-LoRA workflows as API sources: a reference clip or sheet in, one guided pass out.

An IC-LoRA only works through its own guide, so these follow Lightricks' single-stage examples at the
pinned ComfyUI-LTXVideo commit (LTX-2.3_V2V_ICLoRA and LTX-2.3_ICLoRA_Ingredients) with this bundle's
checkpoint, adapter and sampling. package-workflows.py folds them like every other API source.
"""
import json
from pathlib import Path
from workflow_frame import FIT_HEIGHT as HEIGHT, FIT_WIDTH as WIDTH
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'versions/2'
SCHEMA=json.loads((P/'node-schemas.json').read_text())
PREFIX='Sulphur';MODEL='sulphur_dev_fp8mixed.safetensors';ENCODER='gemma_3_12B_it_fp4_mixed.safetensors'
ADAPTER='ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors';ADAPTER_STRENGTH=0.5
SAMPLER='euler';SIGMAS='1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0'
CROSSVIEW='LTX2.3-22B_IC-LoRA-CrossView-Prompt_v0.9_13700.safetensors'
INGREDIENTS='ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors'
RELIGHT='ltx-2.3-22b-ic-lora-relight-1.0.safetensors'
DAY_TO_NIGHT='ltx-2.3-22b-ic-lora-day-to-night-0.9.safetensors'
IC_LORA='9100'
# Relight's training geometry at 1280 x 704: a 143 px patch, 22 px from the top and right edges.
BALL_SCALE='sqrt(a*b/901120)'
SHAPE='''

**Width** and **Height** set the frame's area, and your clip sets its shape. **Frames** sets the length, and the shot stops at the end of your clip.'''
FETCH='''

**This one needs a licence first.** Accept the LTX-2 Community License at [{repo}](https://huggingface.co/{repo}) with the Hugging Face account behind `HF_TOKEN`, then restart the Pod or run `python3 /opt/sulphur/scripts/download-models.py` in its terminal. Until then this workflow reports a missing LoRA; nothing else is affected.'''
CROSSVIEW_NOTE='''## How to move the camera

This re-shoots your clip from a new position, like a second camera on the same take, and keeps your clip's sound so it lines up in the edit.

1. Upload **Your source video**. No opening image is needed.
2. Write only the camera move, in these exact words:

`crossview. new camera angle: to the left, higher, closer.`

- **Side:** same angle · slightly to the left · slightly to the right · to the left · to the right · far to the left · far to the right
- **Height:** lower · same height · higher
- **Distance:** closer · same distance · further

3. Run. For a big move, feed the result back in and make another small one.

Small moves are the most reliable. The range is about 60° either side of the front, so a view from behind is out of reach. **IC-LoRA strength** starts at 1.5 because the effect is weaker on fast sampling; 1.2 to 1.5 is the useful range. This is a v0.9 proof of concept, and it was trained on the plain LTX-2.3 model.'''
INGREDIENTS_NOTE='''## How to keep a character across shots

1. Upload one **Reference sheet** on a black background with no text: a face close-up and a full-body view of each person, each important prop, and a clean panel of the location. Bigger panels carry over better.
2. Keep the prompt's two parts. **Reference sheet:** names each panel by its position. **Generated video:** describes the action and shot.
3. Run. Reuse the same sheet and the same descriptions for every shot of the scene.

The sheet guides the shot and is never seen in the result. It is stretched to the frame, so make it the same shape. 768 x 448, 121 frames at 24 fps is what the model was trained on; other sizes and longer clips drift. Lightricks tuned **IC-LoRA strength** at 1.4 and start their examples at 1.0.'''
RELIGHT_NOTE='''## How to relight a shot

1. Upload **Your source video**. It must be an exterior: this model is for sunlight.
2. Set **Light direction**. The ball is added to the corner of the frame the model reads, and is not in the result.
3. Keep the prompt's first sentence and match its end to the ball:

`relight the video to match the light-direction ball. hard directional sunlight from the right`

- **From:** front · front-right · right · back-right · behind · back-left · left · front-left
- **Looks:** hard directional sunlight · hard high-angle sunlight · hard low-angle sunlight · soft diffused daylight · soft warm afternoon light · cool soft daylight · dim overcast light · strong backlight with rim light · soft hazy backlight · warm golden low front sun · warm golden low side sun · frontal sunlight

Describe the light only, not the scene. If the words and the ball disagree, the ball wins. Your clip's sound is kept. 1280 x 704, 121 frames at 24 fps is what the model was trained on, and it works in a single pass only.'''
DAY_TO_NIGHT_NOTE='''## How to turn day into night

1. Upload **Your source video**, shot in daylight at 24 fps.
2. Describe the night look and keep the last sentence, which holds the shot still. Steer the colour with phrases such as warm tungsten light or cool white LED light.
3. Run. Composition, camera and motion come from your clip, and its sound is kept.

768 x 448, 97 frames at 24 fps is what the model was trained on; longer clips drift towards the end. On the fast settings here **CFG** stays at 1. Lightricks' own recipe is 30 steps at CFG 3 to 4, where higher is darker.'''

class Graph:
    """API prompt with stable ids: the shared panel controls first, then nodes from 100 in build order."""
    def __init__(self,prompt,negative,width,height,frames,cfg=1.0):
        self.api={};self.next=100
        for key,typ,value in (('9000','PrimitiveInt',width),('9001','PrimitiveInt',height),('9002','PrimitiveInt',frames),('9004','PrimitiveStringMultiline',prompt),('9005','PrimitiveStringMultiline',negative),('9006','PrimitiveFloat',cfg),('9007','PrimitiveInt',42)):
            self.api[key]={'class_type':typ,'inputs':{'value':value}}
    def add(self,typ,title=None,key=None,**inputs):
        assert typ in SCHEMA,typ
        if key is None:key=str(self.next);self.next+=1
        self.api[key]={'class_type':typ,'inputs':inputs}
        if title:self.api[key]['_meta']={'title':title}
        return key
    def math(self,expression,title,**values):
        return self.add('ComfyMathExpression',title,expression=expression,**{'values.'+k:v for k,v in values.items()})

def models(g,lora,strength):
    checkpoint=g.add('CheckpointLoaderSimple',ckpt_name=MODEL)
    adapter=g.add('LoraLoaderModelOnly',model=[checkpoint,0],lora_name=ADAPTER,strength_model=ADAPTER_STRENGTH)
    g.add('LTXICLoRALoaderModelOnly','IC-LoRA',IC_LORA,model=[adapter,0],lora_name=lora,strength_model=strength)
    return checkpoint,g.add('LTXAVTextEncoderLoader',text_encoder=ENCODER,ckpt_name=MODEL,device='default'),g.add('LTXVAudioVAELoader',ckpt_name=MODEL)

def conditioning(g,encoder,frame_rate):
    positive=g.add('CLIPTextEncode',text=['9004',0],clip=[encoder,0]);negative=g.add('CLIPTextEncode',text=['9005',0],clip=[encoder,0])
    return g.add('LTXVConditioning',positive=[positive,0],negative=[negative,0],frame_rate=frame_rate)

def generate(g,checkpoint,conditions,guide,width,height,length,sound):
    """The IC-LoRA guide joins the empty frames, then is cropped back out after sampling."""
    latent=g.add('EmptyLTXVLatentVideo',width=width,height=height,length=length,batch_size=1)
    guided=g.add('LTXAddVideoICLoRAGuide','Reference guide',positive=[conditions,0],negative=[conditions,1],vae=[checkpoint,2],latent=[latent,0],image=guide,frame_idx=0,strength=1.0,latent_downscale_factor=[IC_LORA,1],crop='disabled',use_tiled_encode=False,tile_size=256,tile_overlap=64,use_streaming=False,tile_frames=97)
    joined=g.add('LTXVConcatAVLatent',video_latent=[guided,2],audio_latent=sound)
    noise=g.add('RandomNoise',noise_seed=['9007',0]);sampler=g.add('KSamplerSelect',sampler_name=SAMPLER);sigmas=g.add('ManualSigmas',sigmas=SIGMAS)
    guider=g.add('CFGGuider',cfg=['9006',0],model=[IC_LORA,0],positive=[guided,0],negative=[guided,1])
    sampled=g.add('SamplerCustomAdvanced',noise=[noise,0],guider=[guider,0],sampler=[sampler,0],sigmas=[sigmas,0],latent_image=[joined,0])
    parts=g.add('LTXVSeparateAVLatent',av_latent=[sampled,0])
    cropped=g.add('LTXVCropGuides',positive=[guided,0],negative=[guided,1],latent=[parts,0])
    return g.add('VAEDecodeTiled',tile_size=768,overlap=64,temporal_size=4096,temporal_overlap=4,samples=[cropped,2],vae=[checkpoint,2]),parts

def save(g,images,fps,audio,title):
    video=g.add('CreateVideo',fps=fps,bit_depth='auto',color_space='sRGB',codec='none',images=[images,0],audio=audio)
    g.add('SaveVideo',filename_prefix=f'video/{PREFIX}_'+title.replace(' ','_'),format='auto',**{'format.codec':'auto'},video=[video,0])

def from_clip(g,title,lora,strength,paint=None):
    """Same take, new picture: the clip guides every frame and its own sound is held and kept."""
    clip=g.add('LoadVideo',file='');parts=g.add('GetVideoComponents',video=[clip,0]);size=g.add('GetImageSize','Size of your clip',image=[parts,0])
    width=g.math(WIDTH,'Fit Frame Width',a=['9000',0],b=['9001',0],c=[size,0],d=[size,1])
    height=g.math(HEIGHT,'Fit Frame Height',a=['9000',0],b=['9001',0],c=[size,0],d=[size,1])
    frames=g.math('1+floor((min(a,b)-1)/8)*8','Frames (8n + 1, up to your clip)',a=['9002',0],b=[size,2])
    trimmed=g.add('ImageFromBatch',image=[parts,0],batch_index=0,length=[frames,1])
    fitted=g.add('ImageScale',image=[trimmed,0],upscale_method='lanczos',width=[width,1],height=[height,1],crop='center')
    guide=paint(g,fitted,width,height) if paint else fitted
    checkpoint,encoder,audio_vae=models(g,lora,strength)
    conditions=conditioning(g,encoder,[parts,2])
    seconds=g.math('a/b','Shot length (seconds)',a=[frames,0],b=[parts,2])
    silence=g.add('EmptyAudio','Silence, for a clip with no sound',duration=[seconds,0],sample_rate=44100,channels=2)
    merged=g.add('AudioMerge',audio1=[parts,1],audio2=[silence,0],merge_method='add')
    sound=g.add('TrimAudioDuration',start_index=0,duration=[seconds,0],audio=[merged,0])
    encoded=g.add('LTXVAudioVAEEncode',audio=[sound,0],audio_vae=[audio_vae,0])
    mask=g.add('SolidMask',value=0,width=[width,1],height=[height,1])
    held=g.add('SetLatentNoiseMask','Hold your clip\'s sound',samples=[encoded,0],mask=[mask,0])
    images,_=generate(g,checkpoint,conditions,[guide,0],[width,1],[height,1],[frames,1],[held,0])
    save(g,images,[parts,2],[sound,0],title)
    return clip

def add_ball(g,fitted,width,height):
    ball=g.add('SphereLightManualNode','Light direction',rotation=0.0,elevation=45.0,intensity=1.5,render_b64='')
    scale=dict(a=[width,1],b=[height,1])
    patch=g.math(f'round(143*{BALL_SCALE})','Ball patch size',**scale);margin=g.math(f'round(22*{BALL_SCALE})','Ball margin',**scale)
    corner=g.math('a-b-c','Ball patch left edge',a=[width,1],b=[patch,1],c=[margin,1])
    sized=g.add('ImageScale',image=[ball,0],upscale_method='lanczos',width=[patch,1],height=[patch,1],crop='disabled')
    return g.add('ImageCompositeMasked','Ball in the top-right corner',destination=[fitted,0],source=[sized,0],x=[corner,1],y=[margin,1],resize_source=False)

def crossview():
    g=Graph('crossview. new camera angle: to the left, higher, closer.','text, subtitles, logo, watermark, signature',960,544,121)
    clip=from_clip(g,'New Camera Angle',CROSSVIEW,1.5)
    return g,clip,{'note':CROSSVIEW_NOTE+SHAPE}

def ingredients():
    prompt=('Reference sheet: Top Left (Character): [name and describe the first person]. Top Right (Character): [the second person]. Bottom (Setting): [the location].\n\n'
            'Generated video: [the action, framing, camera movement and sound].')
    g=Graph(prompt,'worst quality, inconsistent motion, blurry, jittery, distorted',768,448,121)
    g.api['9003']={'class_type':'PrimitiveInt','inputs':{'value':24}}
    sheet=g.add('LoadImage',image='')
    fitted=g.add('ImageScale',image=[sheet,0],upscale_method='lanczos',width=['9000',0],height=['9001',0],crop='disabled')
    held=g.add('RepeatImageBatch','Hold the sheet for the whole shot',image=[fitted,0],amount=['9002',0])
    checkpoint,encoder,audio_vae=models(g,INGREDIENTS,1.0)
    conditions=conditioning(g,encoder,['9003',0])
    silence=g.add('LTXVEmptyLatentAudio',frames_number=['9002',0],frame_rate=['9003',0],batch_size=1,audio_vae=[audio_vae,0])
    images,parts=generate(g,checkpoint,conditions,[held,0],['9000',0],['9001',0],['9002',0],[silence,0])
    sound=g.add('LTXVAudioVAEDecode',samples=[parts,1],audio_vae=[audio_vae,0])
    save(g,images,['9003',0],[sound,0],'Recurring Characters')
    return g,sheet,{'note':INGREDIENTS_NOTE+FETCH.format(repo='Lightricks/LTX-2.3-22b-IC-LoRA-Ingredients'),'fps':True}

def relight():
    g=Graph('relight the video to match the light-direction ball. hard directional sunlight from the right','worst quality, inconsistent motion, blurry, jittery, distorted',1280,704,121)
    clip=from_clip(g,'Relight',RELIGHT,1.0,add_ball)
    return g,clip,{'note':RELIGHT_NOTE+SHAPE+FETCH.format(repo='Lightricks/LTX-2.3-22b-IC-LoRA-Relight')}

def day_to_night():
    prompt=('A realistic nighttime scene lit by street lamps and warm windows, with a dark sky and deep soft shadows. '
            'Only the lighting changes from day to night; identical composition, framing, camera movement and motion.')
    g=Graph(prompt,'daytime, bright sunlight, blue sky, overexposed, worst quality, inconsistent motion, blurry, jittery, distorted',768,448,97)
    clip=from_clip(g,'Day to Night',DAY_TO_NIGHT,1.0)
    return g,clip,{'note':DAY_TO_NIGHT_NOTE+SHAPE+FETCH.format(repo='Lightricks/LTX-2.3-22b-IC-LoRA-Day-To-Night')}

WORKFLOWS=[('crossview','07','New Camera Angle',crossview,'Your source video'),('ingredients','08','Recurring Characters',ingredients,'Reference sheet'),('relight','09','Relight',relight,'Your source video'),('day_to_night','10','Day to Night',day_to_night,'Your source video')]

if __name__=='__main__':
    catalog=json.loads((P/'workflow-catalog.json').read_text())
    for name,number,title,build,label in WORKFLOWS:
        g,source,extra=build()
        api=f'{PREFIX}_ic_lora_{name}.json';(P/'api'/api).write_text(json.dumps(g.api,indent=2)+'\n')
        fields=[{'label':'Width','source':9000},{'label':'Height','source':9001},{'label':'Frames (8n + 1)','source':9002}]
        if extra.get('fps'):fields.append({'label':'FPS','source':9003})
        fields+=[{'label':'Negative prompt','source':9005},{'label':'CFG','source':9006},{'label':'Seed','source':9007},{'label':'IC-LoRA strength','kind':'PrimitiveFloat','targets':[[int(IC_LORA),'strength_model']]}]
        labels={source:label}
        labels.update({k:n['_meta']['title'] for k,n in g.api.items() if n['class_type']=='SphereLightManualNode'})
        catalog[api]={'title':title,'file':f'{number}_{PREFIX}_{title.replace(" ","_")}.json','prompt_id':9004,'controls':fields,'source':'ic_lora','input_labels':labels,'note':extra['note']}
    (P/'workflow-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
