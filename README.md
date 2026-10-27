# Sulfur 2 (LTX 2.3) — ComfyUI Video One-Click

Create videos from a text prompt or a starting image, with generated audio, using **Sulphur 2** inside ComfyUI on Runpod.

This template prepares the models and four workflows for you. Use an **NVIDIA A100 80 GB** for the intended setup. The default is **960 × 544**, **24 frames per second**, and approximately **10 seconds** of video. You can change the prompt, seed, length and other settings in ComfyUI.

**Image:** `ghcr.io/acdevmedia/sulphur-comyfui:2`  
**Storage:** 200 GB container disk; no persistent volume  
**Open ComfyUI:** Runpod **Connect → ComfyUI / HTTP 8188**

## 1. Add your Hugging Face secret

Do this **before starting a pod**:

1. Sign in to [Hugging Face](https://huggingface.co/) and create a token with read access in [Access Tokens](https://huggingface.co/settings/tokens).
2. In your Runpod account, open **Secrets** and create a secret named **`HUGGINGFACE_TOKEN`**. Paste your Hugging Face token as its value.
3. The template's environment variable **`HF_TOKEN`** is already set to **`{{ RUNPOD_SECRET_HUGGINGFACE_TOKEN }}`**. Leave that reference in place so Runpod supplies the secret when the pod starts.
4. If Hugging Face asks you to accept a model's terms or request access, complete that on the relevant model page using the same account.

Do not put your token in a prompt, workflow, GitHub file or public log. GitHub and Runpod API keys are not needed inside the pod.

## 2. Deploy and open ComfyUI

1. Open the [Runpod template](https://console.runpod.io/deploy?template=b551wbs9zm).
2. Select **A100 SXM4 80 GB** and check the displayed hourly price before deploying.
3. Keep **200 GB container disk** and **no volume storage**. The only application port required is **8188 HTTP**.
4. Start the pod and watch its logs. The first start checks the GPU and SageAttention, downloads the models, verifies the files, and prepares ComfyUI. Downloads total about **40.3 GB**, so the interface will not be ready immediately.
5. Wait for **“ComfyUI is READY on port 8188”**, then use **Connect → ComfyUI / HTTP 8188**.

The log explains each stage and reports file sizes, available space and download progress. Download progress is separate from video-generation progress.

## 3. Make a video

In ComfyUI's workflow browser, look under **Sulphur → 2 → fp8**:

- **I2V Distilled:** start with an image. Upload/select your image and enter a prompt.
- **T2V Distilled:** start with a text prompt. This is a good first workflow to try.
- **I2V Base:** image-to-video with the author's longer sampling setup.
- **T2V Base:** text-to-video with the author's longer sampling setup.

**Distilled** workflows use fewer sampling steps and are the preferred starting point. The I2V distilled source is supplied in ComfyUI's API format; ComfyUI can import it and reconstruct its graph.

Set your prompt and seed, then run the workflow. Audio is connected by default. Videos are saved in ComfyUI's output folder and can be downloaded from the result preview. On the container filesystem, that folder is `/workspace/runpod-slim/ComfyUI/output`.

The default length is **241 frames**, about **10 seconds at 24 fps**. LTX uses frame counts of **8n + 1**: examples include 121, 241 and 481 frames. Longer clips are allowed, subject to available GPU memory; there is no imposed ten-second limit.

## What gets downloaded?

The default setup downloads **four files**, approximately **40.3 GB total**. Sizes below use decimal GB, as hosting services commonly do.

- **Sulphur dev FP8 checkpoint — 29.16 GB**  
  `sulphur_dev_fp8mixed.safetensors`  
  The main video model. It also supplies the video VAE, audio VAE and connector weights used by these workflows.
- **Distillation LoRA — 0.66 GB**  
  `ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors`  
  The author's compatible acceleration adapter for the dev checkpoint.
- **Gemma text encoder — 9.45 GB**  
  `gemma_3_12B_it_fp4_mixed.safetensors`  
  Converts your written prompt into the representation the video model uses.
- **LTX 2.3 spatial upscaler — 1.00 GB**  
  `ltx-2.3-spatial-upscaler-x2-1.1.safetensors`  
  Used by the author's two-stage workflow to reach the requested final size.

The main checkpoint and distillation adapter come from [SulphurAI](https://huggingface.co/SulphurAI/Sulphur-2-base). The encoder comes from [Comfy-Org](https://huggingface.co/Comfy-Org/ltx-2), and the spatial upscaler comes from [Lightricks](https://huggingface.co/Lightricks/LTX-2.3).

The template does **not** download the whole model repository, the separate Sulphur fine-tuning LoRA, prompt-enhancer models, or every precision variant. Large model files are downloaded to your pod; they are not included in the container image or GitHub repository.

## Keep your videos safe

**This template uses temporary container storage only.** The 200 GB disk holds the application, models, inputs and outputs. Model files use about 40.3 GB; the application and container also use space.

Completed downloads are reused while the same container disk remains available, and interrupted downloads can resume. **Do not rely on that disk surviving a pod stop, replacement, image upgrade or deletion.** Download important videos, images and edited workflows before those actions. A replacement container may need to download the models again.

## Changes made to the official workflows

The four graphs come from the model author's official workflows. Their sampler choices, sigma schedules, CFG settings, seed controls, negative prompts and audio connections are retained.

The setup makes these compatibility changes:

- Selects the Sulphur dev FP8 checkpoint instead of the original LTX checkpoint names.
- Bypasses the old `sulphur_final` fine-tuning LoRAs: that fine-tuning is already included in the Sulphur checkpoint and must not be applied twice.
- Repairs outdated distillation-LoRA and upscaler filenames.
- Enables SageAttention through ComfyUI's launch settings and bypasses per-graph attention patches so the backend can be changed in one place.
- Replaces two unavailable image-resize helpers with native ComfyUI nodes. Starting images are fitted and center-cropped to the requested default size.
- Uses the checkpoint VAE for the optional preview instead of downloading a separate tiny preview VAE.
- Corrects the final frame size after LTX rounds the half-resolution latent dimensions. The default saved frame is 960 × 544; this is a size correction, not an additional enhancement pipeline.
- Updates API-format video-saving inputs for the pinned ComfyUI release.

There is no added prompt enhancer, moderation service, custom video interface or additional model family. The author's two-stage latent-upscaling controls remain in the graphs; no separate output-upscaling pipeline is added.

## If something goes wrong

- **The interface is not ready:** check the pod logs. On first start, model downloads must finish before ComfyUI opens.
- **A download is denied:** check the Runpod secret name, the `HF_TOKEN` reference, your token's read permissions, and any model-access requirements on Hugging Face.
- **There is not enough space:** keep the 200 GB container allocation, remove files you no longer need, or start with a clean disk. The downloader requires 10 GB of free space beyond missing model files as an output reserve.
- **I2V reports a missing image:** upload/select your own starting image; the author's example filename is not downloaded.
- **An attention or CUDA check fails:** the log identifies the failed check. Verify that the pod has a compatible NVIDIA GPU. The setup reports SageAttention failure explicitly.

The combined startup log is `/workspace/logs/sulphur-startup.log` **inside the pod**. Existing user workflows are preserved; packaged workflows are installed only when absent.

## Technical details

**Pinned software:** ComfyUI **v0.42.1**, frontend **1.55.18**, Python **3.12**, CUDA **12.8**, PyTorch **2.10.0+cu128**, SageAttention **1.0.6**. FFmpeg is included. The image extends the official Runpod ComfyUI image, pinned by digest. KJNodes supplies the author's sampling-preview control; unrelated custom-node bundles and ComfyUI-Manager are omitted.

SageAttention uses Triton on the A100's SM80 architecture. Dependencies are installed during the GitHub Actions build. GPU-specific Triton kernel specialization occurs at runtime; no SageAttention CUDA extension or package installation is performed at pod startup. Startup executes a real kernel check. ComfyUI's own log must also confirm backend selection; installation alone does not establish a speed improvement.

### Environment settings

Names are uppercase and listed alphabetically in the template:

- **`COMFYUI_ATTENTION=sage`** — default backend when creating a new launch-arguments file. `pytorch` selects PyTorch instead.
- **`HF_HOME=/workspace/.cache/huggingface`** — Hugging Face working directory inside the container.
- **`HF_TOKEN={{ RUNPOD_SECRET_HUGGINGFACE_TOKEN }}`** — resolves your Runpod secret at deployment.
- **`SULPHUR_MODEL_VARIANT=fp8`** — default model selection; optional choices are described below.
- **`SULPHUR_VERSION=2`** — identifies this image's packaged version.

After the first launch, `/workspace/runpod-slim/comfyui_args.txt` is user-owned. To change attention, replace `--use-sage-attention` with `--use-pytorch-cross-attention`, or reverse the change, then restart ComfyUI. Changing the environment variable does not overwrite an existing arguments file.

### Optional model variants

`bf16` replaces the main checkpoint with `sulphur_dev_bf16.safetensors` (**46.14 GB**), for about **57.2 GB** of model downloads in total.

`native-distilled` uses `sulphur_distil_bf16.safetensors` (**46.14 GB**), for about **56.6 GB** total. It installs only distilled workflows and omits/disables the extra distillation LoRA, because distillation is already included.

These are optional alternatives, not additional default downloads. Each variant has a separate workflow subfolder. Changing variants keeps old model files until you remove them; the downloader checks available space before proceeding.

### Reproducibility, builds and updates

Version-specific assets live in the repository's `versions/2/` folder. That includes original workflows, repaired workflows, model byte sizes, SHA256 checksums and pinned source revisions. A future major model version belongs in a separate version folder and release tag.

All container builds run **exclusively in GitHub Actions**. Builds install dependencies, test imports, start a CPU-only ComfyUI server, check the workflow nodes/inputs, and publish only after those checks pass. No local container builds are used.

The moving release image is `ghcr.io/acdevmedia/sulphur-comyfui:2`; each published build also gets an immutable `sha-<commit>` tag. The image does not update ComfyUI or install Sulphur packages automatically at startup. To upgrade, first save your outputs and edited workflows, then deploy the newer `:2` image. Keep the previous image digest if you need to roll back.

Downloads are pinned and checked against SHA256. Files go directly into ComfyUI's model folders without keeping a second full Hub blob-cache copy. Existing verified files are reused. Full installed Python package versions are recorded inside the image at `/opt/sulphur-python-lock.txt`.

See the [validation record](https://github.com/acdevmedia/comfyui-sulphur/blob/develop/docs/VALIDATION.md) for what has actually been tested, including any GPU benchmarks or remaining limitations. Image-build success alone does not prove that video generation works.

[Source code](https://github.com/acdevmedia/comfyui-sulphur) · [Builds](https://github.com/acdevmedia/comfyui-sulphur/actions) · [Model author's instructions](https://huggingface.co/SulphurAI/Sulphur-2-base)

Model use is governed by the author's [LTX-2 Community License](https://github.com/acdevmedia/comfyui-sulphur/blob/develop/versions/2/LICENSE-model.txt). Model weights are not redistributed in the image.
