# Sulphur 2 on Runpod

A small extension of the official Runpod ComfyUI image with Sulphur's four official workflow graphs, persistent models, FFmpeg and SageAttention. ComfyUI is the interface.

Deploy `ghcr.io/acdevmedia/sulphur-2:2`, expose HTTP 8188, mount persistent storage at `/workspace`, and use an NVIDIA A100 80 GB. Set `HF_TOKEN` through Runpod Secrets if required. See [deployment instructions](docs/RUNPOD.md).

## Versions and builds

Version-specific models, upstream workflow sources and packaged workflows live in `versions/2/`. A future Sulphur 3 belongs in `versions/3/` and a separate image release tag. Git release tags use `v2.x.y`. Images publish `:2` and immutable `:sha-<commit>` tags; no `latest` deployment tag. All image builds run exclusively in GitHub Actions. The build validates dependencies before publishing; failed builds do not replace `:2`.

Pinned base: `runpod/comfyui:1.4.1-comfyuiv0.35.0-cuda12.8@sha256:d411ebacf3fdbc98ded7f78f06ac12aae20c08041cde79ab08173c156d04aae5`. Its Python 3.12, CUDA 12.8, PyTorch 2.10.0+cu128 stack is retained. ComfyUI is updated in the image to v0.42.1 (frontend 1.55.18). Only KJNodes is added for the author's sampling preview controls; the base's unrelated custom nodes and Manager are omitted from this minimal bundle. Full installed package versions are recorded at `/opt/sulphur-python-lock.txt`.

SageAttention 1.0.6 is the same Triton implementation used by LTX-SETUP and supports A100 SM80. Installation happens in Actions; Triton JIT kernel specialization happens on the GPU at runtime, as in the reference setup. No CUDA extension is compiled or pip-installed at startup. A real GPU kernel test fails startup explicitly if SageAttention cannot run. ComfyUI must also log that it selects SageAttention; installation alone is not a throughput benchmark.

## Models and workflows

Default `SULPHUR_MODEL_VARIANT=fp8`: Sulphur dev FP8 checkpoint, author's compatible distillation LoRA, Gemma FP4 text encoder and LTX 2.3 spatial upscaler, about **40.3 GB** total. Video VAE, audio VAE and audio/text connector weights come from the checkpoint; separate duplicate checkpoints are unnecessary. Exact repository revisions, byte sizes and SHA256 hashes are in `versions/2/profile.json`.

Optional `bf16` replaces the dev checkpoint. Optional `native-distilled` installs the native distilled checkpoint and disables additional distillation LoRAs; only distilled workflows are installed. Free space is checked before downloading, with a 10 GB output reserve. Use one variant per volume/profile; changing variants keeps old models until you explicitly remove them. Workflow files are installed once, so each variant has its own workflow subfolder.

Official graph repairs are reproducible with `python3 scripts/package-workflows.py`; originals are retained in `versions/2/upstream`. Merged Sulphur checkpoints bypass the obsolete `sulphur_final` fine-tuning LoRAs. Old distilled LoRA and upscaler filenames are repaired. Graph attention patches are bypassed so the global backend switch works. Optional tiny preview VAE uses the checkpoint VAE instead. Two unavailable image resize helpers are replaced with native ComfyUI equivalents. Author sampler settings, CFG, sigma schedules, seeds, audio, negative prompts and two-stage controls remain available.

Defaults are 960×544 at 24 fps, 241 frames (LTX's 8n+1 requirement, approximately 10 seconds). I2V input is fitted and center-cropped to that size. Longer 8n+1 frame counts are supported subject to memory. The author's second stage uses latent upscaling from half resolution to the requested final resolution; it remains available. A native final size correction compensates for LTX rounding the half-resolution latent height; there is no separate output enhancement pipeline. Upstream I2V distilled is API format: import it into ComfyUI, which reconstructs the graph, or submit through `/prompt`. Choose an input image before running I2V.

## Logs and validation

`/workspace/logs/sulphur-startup.log` includes timestamped startup, storage estimates, per-file downloads, integrity checks, GPU details and the official Runpod service logs. Secrets are not printed by Sulphur scripts. Normal Runpod helper services retain their upstream authentication behavior; keep pod logs private.

Local checks: `python3 scripts/check-source.py`, `python3 scripts/package-workflows.py`, `bash -n scripts/*.sh`. Build checks import torch, SageAttention and Hugging Face Hub and verify FFmpeg and the launch flag. GPU testing and measured timings are documented in `docs/VALIDATION.md`; never infer generation success from an image build.

Source references: [Sulphur author instructions](https://huggingface.co/SulphurAI/Sulphur-2-base), [official Runpod template](https://github.com/runpod/containers/tree/main/official-templates/comfyui), [ComfyUI](https://github.com/Comfy-Org/ComfyUI). LTX-SETUP was inspected without modification; its persistent download, Triton SageAttention and Actions publishing patterns informed this setup. S3 backups are deliberately not enabled by default; download outputs or back up your volume before deletion.
