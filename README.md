# Sulphur 2 for ComfyUI on Runpod

Turn a prompt, a picture or a soundtrack into a video with sound. This is **Sulphur 2**, a fine-tune of LTX 2.3, ready to run in ComfyUI on a Runpod GPU.

Start a pod, wait for the models to download, and open a workflow. Each workflow is a tidy canvas: a box for your prompt, a box for your image if the workflow uses one, a **Shot settings** panel, and the finished video. You don't need to touch any wiring.

| | |
|---|---|
| **GPU** | NVIDIA A100 80 GB (other GPUs with enough VRAM can work too) |
| **Default shot** | 960 × 544, 24 fps, 241 frames (about 10 seconds), with audio |
| **Speed** | About 40 seconds for a 10-second clip once the models are loaded (A100, Text to Video Distilled) |
| **Storage** | 200 GB container disk. About 40 GB of it is models |
| **Image** | `ghcr.io/acdevmedia/sulphur-comyfui:2` |
| **Template** | [Deploy on Runpod](https://console.runpod.io/deploy?template=b551wbs9zm) |

---

## Getting started

### 1. Add your Hugging Face token (one time)

The models download from Hugging Face, so the pod needs your token.

1. Create a **read** token in your [Hugging Face access tokens](https://huggingface.co/settings/tokens).
2. In Runpod, open **Secrets** and add one named **`HUGGINGFACE_TOKEN`**. Paste the token as its value.
3. That's all. The template already reads it through `HF_TOKEN={{ RUNPOD_SECRET_HUGGINGFACE_TOKEN }}`, so leave that line as it is.

If Hugging Face asks you to accept a model's terms, accept them with the same account. Keep the token out of prompts, workflows and screenshots.

### 2. Start a pod

1. Open the [Runpod template](https://console.runpod.io/deploy?template=b551wbs9zm).
2. Pick **A100 SXM4 80 GB** and check the hourly price.
3. Keep the **200 GB container disk**. You don't need a volume.
4. Deploy, then open the pod's logs.

The first start checks the GPU, downloads about 40 GB of models and verifies each file. On our test pod this took about a minute and a half. When you see **"ComfyUI is READY on port 8188"**, click **Connect → HTTP 8188**.

### 3. Make your first video

Open the **Workflows** sidebar in ComfyUI. The Sulphur workflows are numbered:

| Workflow | You provide | Good for |
|---|---|---|
| **01 Image to Video — Distilled** | an image and a prompt | Bringing a still to life, fast. **Start here** if you have an image |
| **02 Text to Video — Distilled** | a prompt | A shot from words alone, fast. **Start here** otherwise |
| **03 Image to Video — Base** | an image and a prompt | The author's full-length sampling: slower, for when you want more steps |
| **04 Text to Video — Base** | a prompt | Same as 03, from text |
| **05 First and Last Frame to Video** | two images and a prompt | Animating the move between a start frame and an end frame |
| **06 Image and Audio to Video** | an image, an audio clip and a prompt | Making a picture move in time with your own sound |

Type your prompt, upload any images or audio, and click **Run**. The video and its audio appear in the **Finished video** box, where you can play or download it.

**Distilled** workflows use the author's speed-up adapter and only a few sampling steps, so they're the quickest way to try ideas. **Base** workflows take longer.

### Tips

- **Clip length:** set **Frames** in Shot settings. LTX wants **8n + 1** frames: 121 is about 5 seconds, 241 about 10 and 481 about 20 at 24 fps. There's no ten-second cap; longer clips just need more GPU memory and time.
- **Seeds:** change the **Seed** for a new take of the same prompt. Keep it fixed when you only want to adjust the prompt.
- **Changing the prompt is cheap:** re-reading a new prompt takes about 2 seconds. Most of each run is the video itself.
- **The first run is slower** because it loads the models into GPU memory. Later runs reuse them.
- **Negative prompt:** describes what you don't want, such as blur or flicker. Each workflow ships with a sensible one.

---

## Save your work

**This template uses temporary storage only.** The 200 GB disk holds the models, your uploads and your videos, and it may not survive a pod stop, replacement, image upgrade or deletion.

**Download any videos and edited workflows you want to keep before you stop the pod.** If the disk is lost, a new pod downloads the models again automatically.

Videos are saved in `/workspace/runpod-slim/ComfyUI/output` inside the pod.

---

## What's been done to make this work well

### Fixes to the original workflows

The four Sulphur workflows started as the author's official files on [Hugging Face](https://huggingface.co/SulphurAI/Sulphur-2-base). The samplers, sigma schedules, CFG values, negative prompts and audio connections are kept exactly as the author set them. These changes were needed to make them run properly here:

- **The right model.** They load the Sulphur dev FP8 checkpoint instead of the original LTX checkpoint names.
- **No double fine-tuning.** The old `sulphur_final` LoRA is switched off, because the Sulphur checkpoint already includes that training. Applying it again would overcook the result.
- **Fixed file names.** The distillation LoRA and spatial upscaler point to files that actually exist.
- **No missing nodes.** Two image-resize helpers from custom nodes that aren't installed were replaced with native ComfyUI nodes. Your starting image is fitted and centre-cropped to the shot size.
- **No extra downloads.** The sampling preview uses the VAE inside the checkpoint instead of a separate preview VAE.
- **The size you asked for.** LTX rounds the half-size first pass, so the final frames are resized slightly to land exactly on your chosen width and height.
- **Works with current ComfyUI.** The video-save settings were updated for the pinned ComfyUI release.
- **One attention switch.** The per-workflow attention patches are bypassed, so SageAttention (below) is controlled in one place for every workflow.
- **A cleaner canvas.** The node graph is folded into a single **Shot settings** panel, with only the prompt, inputs and finished video left on the canvas. Everything is still there: open the panel to see the full graph.

Workflows **05** and **06** are adapted from Lightricks' official LTX 2.3 examples and set up the same way, with the Sulphur model and the same Shot settings panel.

### Speed

- **SageAttention.** ComfyUI starts with `--use-sage-attention`, a faster attention kernel. At every start, the pod runs a real SageAttention kernel on the GPU and says plainly in the log if it fails, rather than quietly falling back.
- **CPU threads that fit the pod.** Runpod pods report every CPU on the host (192 on A100 machines) but only let a container use about 20. Left alone, PyTorch started 96 threads and was constantly throttled, so saving the video and resizing frames ran about 10× too slowly. The pod now sizes its thread pools to the real limit. With the same workflow and settings, a 10-second Text to Video Distilled clip went from **124 seconds to about 40**, and the video save step alone went from **62 seconds to 2**.
- **Faster final resize.** The last resize before saving uses bilinear scaling on the whole clip, instead of resizing each frame one by one with Lanczos on the CPU.
- **Quick, safe downloads.** Models download straight into ComfyUI's folders, with no second cached copy. Each file is checked against a SHA256 checksum, interrupted downloads resume, and verified files are never downloaded twice.
- **Nothing updates at boot.** ComfyUI and its packages are built into the image, so starts are predictable and nothing changes under you.

---

## What gets downloaded

Four files, about **40.3 GB** in total:

| File | Size | What it does |
|---|---|---|
| `sulphur_dev_fp8mixed.safetensors` | 29.16 GB | The Sulphur video model. It also contains the video VAE, audio VAE and connector weights |
| `gemma_3_12B_it_fp4_mixed.safetensors` | 9.45 GB | The text encoder that reads your prompt |
| `ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | 1.00 GB | Doubles the first, half-size pass up to full size |
| `ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors` | 0.66 GB | The author's speed-up adapter for the Distilled workflows |

They come from [SulphurAI](https://huggingface.co/SulphurAI/Sulphur-2-base), [Comfy-Org](https://huggingface.co/Comfy-Org/ltx-2) and [Lightricks](https://huggingface.co/Lightricks/LTX-2.3). The whole model repository, other precisions and prompt-enhancer models are **not** downloaded. Model weights are never stored in the container image or in this repository.

---

## If something goes wrong

All startup messages are saved to `/workspace/logs/sulphur-startup.log` inside the pod.

- **ComfyUI isn't ready yet:** on first start, the models must finish downloading first. The log shows progress, and download progress isn't video progress.
- **A download is refused:** check that the Runpod secret is named `HUGGINGFACE_TOKEN`, that your token has read access, and that you've accepted any model terms on Hugging Face.
- **Not enough space:** keep the 200 GB disk. The downloader also keeps 10 GB free for your videos.
- **"Missing image" on an Image to Video workflow:** upload your own image. The author's example image isn't included.
- **An attention or CUDA check fails:** the log names the failed check. Make sure the pod has an NVIDIA GPU.
- **You updated the image but a workflow looks old:** your existing workflows are never overwritten. Rename or delete the old file, then restart the pod to get the new version.

---

## Settings

You can change these in the template's environment variables:

| Variable | Default | What it does |
|---|---|---|
| `COMFYUI_ATTENTION` | `sage` | Attention backend for a fresh pod. Set `pytorch` to use PyTorch's built-in attention instead |
| `HF_TOKEN` | `{{ RUNPOD_SECRET_HUGGINGFACE_TOKEN }}` | Your Hugging Face token, read from the Runpod secret |
| `HF_HOME` | `/workspace/.cache/huggingface` | Hugging Face working folder |
| `OMP_NUM_THREADS` | the pod's CPU limit | CPU threads for PyTorch. Set it only to override the automatic value |
| `SULPHUR_MODEL_VARIANT` | `fp8` | Which main model to download (see below) |

**Switching attention on a running pod:** after the first start, ComfyUI's launch options live in `/workspace/runpod-slim/comfyui_args.txt`, and that file is yours. Swap `--use-sage-attention` for `--use-pytorch-cross-attention` (or back), then restart ComfyUI. Changing the environment variable later doesn't overwrite this file.

**Other model variants:**

- `bf16`: the full-precision dev model (46.14 GB, about 57.2 GB of downloads in total).
- `native-distilled`: the author's fully distilled model (46.14 GB, about 56.6 GB in total). Distillation is already built in, so the extra speed-up LoRA is switched off and the Base workflows aren't installed.

Old model files stay on disk when you switch variants until you delete them, and the downloader checks for free space first.

---

## For maintainers

- **Pinned versions:** ComfyUI v0.42.1, frontend 1.55.18, Python 3.12, CUDA 12.8, PyTorch 2.10.0+cu128, SageAttention 1.0.6, with FFmpeg included. The image extends the official Runpod ComfyUI image, pinned by digest. Sulphur adds only two custom node packs, KJNodes and ComfyUI-LTXVideo. The full package list is in the image at `/opt/sulphur-python-lock.txt`.
- **Builds run only on GitHub Actions.** Each build installs everything, starts a CPU-only ComfyUI and checks every workflow's nodes and inputs. It publishes `:2` plus an immutable `sha-<commit>` tag only if all of that passes, so a failed build never replaces `:2`.
- **Where things live:** everything for this model version is in `versions/2/`: the author's original workflows, the repaired workflows, model sizes, checksums and pinned revisions. A future model version gets its own folder and tag.
- **Upgrading a pod:** save your outputs, then redeploy with the newer `:2` image. Keep the previous digest if you might want to roll back.
- **What's been tested:** see the [validation record](https://github.com/acdevmedia/comfyui-sulphur/blob/develop/docs/VALIDATION.md). A successful build doesn't prove that video generation works; only a GPU run does.

[Source](https://github.com/acdevmedia/comfyui-sulphur) · [Builds](https://github.com/acdevmedia/comfyui-sulphur/actions) · [Model author's notes](https://huggingface.co/SulphurAI/Sulphur-2-base)

Model use is governed by the author's [LTX-2 Community License](https://github.com/acdevmedia/comfyui-sulphur/blob/develop/versions/2/LICENSE-model.txt). Model weights aren't redistributed in the image.
