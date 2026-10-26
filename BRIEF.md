# Codex Engineering Brief
## Sulphur 2 — Runpod ComfyUI Template

### 1. Objective

Build a minimal, reliable Runpod GPU Pod template for **Sulphur 2**, using the latest compatible ComfyUI release and the official Sulphur workflows from Hugging Face.

The Docker image must be built **exclusively by GitHub Actions** and published to GitHub Container Registry.

**Required GHCR tag: `2`**

The project will be created alongside the existing `LTX-SETUP` directory, which contains our previously developed LTX 2.5 Runpod implementation.

Inspect `LTX-SETUP` before implementation and reuse its proven Docker, deployment, model-download and GitHub Actions patterns wherever appropriate.

This is a separate Sulphur project. Do not modify or disrupt `LTX-SETUP`.

### 2. Project structure

Create a sibling directory named:

`SULPHUR-SETUP`

Example:

```text
projects/
├── LTX-SETUP/
└── SULPHUR-SETUP/
```

Keep the repository straightforward:

```text
SULPHUR-SETUP/
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
├── README.md
├── .github/
│   └── workflows/
│       └── build.yml
├── scripts/
│   ├── entrypoint.sh
│   ├── download-models.sh
│   └── validate.sh
├── workflows/
│   ├── Sulphur_I2V_Base.json
│   ├── Sulphur_I2V_Distilled.json
│   ├── Sulphur_T2V_Base.json
│   └── Sulphur_T2V_Distilled.json
└── docs/
    └── RUNPOD.md
```

Add files only where necessary. Do not create redundant frameworks, services, wrappers or abstractions.

### 3. Existing reference implementation

Before writing code, inspect the sibling `LTX-SETUP` project.

Identify:

- Docker base image and version.
- CUDA and PyTorch configuration.
- ComfyUI installation.
- SageAttention implementation, if present.
- Model-download mechanisms.
- Environment-variable handling.
- GHCR publishing workflow.
- Runpod deployment configuration.
- Existing startup scripts.
- FFmpeg configuration.
- Any working S3 integration.

Reuse functioning components wherever applicable.

Do not copy incompatible LTX 2.5 model files or workflows into Sulphur.

**The existing LTX implementation is the engineering reference; the Sulphur Hugging Face repository is the model and workflow reference.**

### 4. Runpod environment

Target the official Runpod ComfyUI directory structure:

```text
/workspace/runpod-slim/
├── ComfyUI/
│   ├── models/
│   ├── input/
│   ├── output/
│   ├── custom_nodes/
│   └── user/
├── comfyui_args.txt
└── ...
```

Runpod's official ComfyUI base implementation:

https://github.com/runpod-workers/comfyui-base

Official Runpod container documentation:

https://github.com/runpod/containers/tree/main/official-templates/comfyui

Prefer extending the official Runpod ComfyUI image rather than recreating the entire environment.

Verify the current official image reference and tag from upstream before selecting a base.

Do not assume that a mutable Docker tag always represents the same software.

Pin the resolved image digest for reproducibility.

Preserve Runpod's existing startup behaviour and directory conventions unless a change is demonstrably necessary.

#### Hardware

Target:

- NVIDIA A100 SXM4 80 GB.
- 200 GB total usable storage.
- NVIDIA CUDA acceleration.
- ComfyUI HTTP port 8188.

The template should also be usable on compatible GPUs with sufficient VRAM.

#### Storage

**200 GB is the budget.**

Do not download the entire Sulphur model repository.

Download only the checkpoints and supporting components needed by the four workflows.

Keep large models on persistent Runpod storage, not inside GHCR.

Check free disk space before downloading.

Keep temporary download caches under control and avoid retaining duplicate model copies.

Use the existing Runpod directory conventions.

### 5. ComfyUI

Install or update to the latest compatible stable ComfyUI release available when implementing this project.

Requirements:

- Native LTX 2.3 support.
- Working Sulphur nodes and loaders.
- Compatible frontend.
- Compatible ComfyUI-Manager, if retained from Runpod's base image.
- Correct CUDA and PyTorch versions.

Prefer native ComfyUI functionality.

Only install additional custom nodes when required by the official Sulphur workflows.

Pin the final tested versions.

Do not run an uncontrolled `git pull` or package upgrade on every pod startup.

ComfyUI updates must be introduced through a new GitHub Actions build.

### 6. SageAttention — Required

Install and configure **SageAttention** for accelerated inference.

This is a priority because generation throughput is critical.

Requirements:

1. Inspect the Python, PyTorch and CUDA versions in the selected Runpod base image.
2. Identify a compatible SageAttention implementation.
3. Ensure compatibility with the A100, compute capability SM80.
4. Install SageAttention and any required Triton dependencies during the **GitHub Actions container build**.
5. Do not compile SageAttention during Runpod pod startup.
6. Enable SageAttention through ComfyUI's supported launch configuration.
7. Verify that ComfyUI actually selects SageAttention rather than silently falling back to PyTorch attention.

For the official Runpod layout, use:

```text
/workspace/runpod-slim/comfyui_args.txt
```

Where supported, include:

```text
--use-sage-attention
```

Validate the flag against the chosen ComfyUI release.

SageAttention installation must match the exact environment. Do not install an arbitrary precompiled wheel.

If necessary, compile it **inside the GitHub Actions Docker build**, targeting SM80.

No local compilation is permitted.

If SageAttention fails, report the problem explicitly rather than describing the environment as optimized.

If another attention backend performs better, retain SageAttention as the requested default but document the measured comparison and provide an easy switch.

### 7. Sulphur models

Primary source:

https://huggingface.co/SulphurAI/Sulphur-2-base

Install the model components required for the official workflows.

Start with the FP8 development checkpoint:

`sulphur_dev_fp8mixed.safetensors`

And the compatible LTX 2.3 distillation LoRA:

`ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors`

Verify exact filenames and paths against the Hugging Face repository.

Install the necessary LTX 2.3 text encoder, VAE, audio and related dependencies.

Use the minimum practical number of files.

Do not automatically download every precision variant.

Support optional installation of the full BF16 and native distilled checkpoints, but only if genuinely needed and within the 200 GB storage budget.

**Important:** Do not apply Sulphur's fine-tuning LoRA to a checkpoint that already incorporates that fine-tuning.

Validate checkpoint/LoRA combinations against the author's instructions.

### 8. Hugging Face downloads

Use Hugging Face Hub for model downloads.

Support:

```text
HF_TOKEN
HF_HOME
SULPHUR_MODEL_VARIANT
```

Use persistent model directories.

On first boot:

- Check which models exist.
- Download missing required files.
- Verify successful downloads.
- Install the supplied workflows.
- Start ComfyUI.

On later boots:

- Reuse models.
- Do not download existing files again.
- Preserve user workflows and generated videos.

Downloads must be resumable.

Avoid duplicate copies caused by Hugging Face caching.

Do not expose Hugging Face credentials in logs.

Model files must not be committed to GitHub or embedded in the GHCR image.

### 9. Official Sulphur workflows

Download all four official workflows from:

https://huggingface.co/SulphurAI/Sulphur-2-base/tree/main/workflows

Implement:

**01 — Image-to-Video Base**

**02 — Image-to-Video Distilled**

**03 — Text-to-Video Base**

**04 — Text-to-Video Distilled**

Use the upstream JSON files as the foundation.

Do not redesign the node graphs unnecessarily.

Repair any outdated model references.

Ensure all checkpoints, encoders, LoRAs and other required files are correctly configured.

The distilled workflows should use the author's recommended acceleration configuration.

Make the workflows readily accessible from ComfyUI's workflow browser.

Copy or install them into the appropriate ComfyUI user workflow directory without overwriting existing user-created workflows.

Preserve their full original functionality and controls.

Do not introduce additional prompt censorship, moderation services or forced prompt enhancement.

#### Workflow defaults

Use sensible initial settings:

| Setting | Default |
|---|---|
| Resolution | 960×544 |
| Frame rate | 24 fps |
| Duration | 10 seconds |
| Audio | Enabled |
| Seed | Configurable |
| Distilled workflow | Preferred |
| Upscaling | Optional |
| Negative prompt | Retain where supported |

Do not remove supported controls merely to simplify the workflow.

Verify the model's frame-count requirements.

Support longer durations where the underlying model permits them.

Do not hard-code a ten-second maximum.

### 10. FFmpeg

Install FFmpeg in the container.

Ensure it is available through `PATH`.

No additional custom video-processing UI is required.

Standard command-line FFmpeg functionality is sufficient.

### 11. Environment variables and credentials

An existing local `.env` file contains:

- Runpod API key.
- GitHub personal access token.
- Hugging Face token.

Codex may inspect the variable names and use the credentials for their intended operations.

**Never print, commit, publish or embed these secrets.**

Do not copy the `.env` file into the Docker image.

The repository must include a `.gitignore` excluding:

```text
.env
.env.*
!.env.example
*.pem
*.key
```

The example environment file must contain placeholders only.

For GitHub Actions, configure required secrets in GitHub Actions repository secrets.

Do not place credentials directly in workflow YAML files.

Prefer `GITHUB_TOKEN` for GHCR publishing when repository permissions allow it.

The existing GitHub PAT may be used for authenticated repository setup if necessary.

The Runpod API key may be used for deployment operations or testing, but should not be passed to a Docker build unless explicitly required.

Only the Hugging Face token should be made available to the running container when authenticated model downloads require it.

Do not pass unrelated credentials into the container.

If `LTX-SETUP` already has a secure and functional secrets workflow, reuse its pattern.

### 12. GitHub Actions — Exclusive build mechanism

**This is a strict requirement.**

All Docker images must be built on GitHub Actions.

Codex must NEVER execute:

```text
docker build
docker buildx build
docker compose build
podman build
buildah bud
```

on the local development machine.

No local container builds of any kind.

The local development environment may be used for:

- Editing files.
- Inspecting repositories.
- Validating JSON.
- Running lightweight static checks.
- Committing code.
- Pushing commits.
- Monitoring GitHub Actions.

GitHub Actions performs:

1. Docker image build.
2. Dependency installation.
3. SageAttention compilation, if needed.
4. Build-time validation.
5. GHCR authentication.
6. Image publishing.

Use the GitHub Actions workflow as the exclusive build-and-publish pipeline.

#### GHCR image

Use:

```text
ghcr.io/<github-owner>/sulphur-2:2
```

The GitHub owner must be derived from the actual repository.

**The required release tag is `2`.**

Do not use `latest` as the deployment reference.

If additional immutable SHA tags are useful, they may be published alongside `2`.

The Runpod template must use:

```text
ghcr.io/<github-owner>/sulphur-2:2
```

Configure `2` as the moving release tag for successfully validated builds.

A failed build must never replace it.

#### GitHub Actions verification

Codex must monitor the build and inspect its logs.

If the build fails:

- Identify the cause.
- Fix it.
- Commit.
- Push.
- Trigger another GitHub Actions build.

Do not switch to local Docker builds to troubleshoot.

Use GitHub Actions logs as the primary diagnostic source.

### 13. Runpod template

After the GHCR image is published, create or update the Runpod template using the existing API key if supported by the available tooling.

Settings:

| Parameter | Value |
|---|---|
| Container | GHCR Sulphur image |
| Tag | `2` |
| GPU | A100 80 GB |
| Storage | 200 GB |
| HTTP port | 8188 |
| Application | ComfyUI |
| Model downloads | Hugging Face |
| Attention | SageAttention |

Follow the storage arrangement already proven in `LTX-SETUP`.

Do not confuse ephemeral container disk with persistent storage.

Ensure downloaded models and user-generated content persist across normal container restarts and image updates.

Provide a documented process for upgrading the pod to a newer `:2` image.

### 14. Validation

Keep tests simple but meaningful.

#### Build validation

Verify:

- Docker build succeeds in GitHub Actions.
- ComfyUI is installed.
- CUDA and PyTorch dependencies are compatible.
- SageAttention imports successfully.
- FFmpeg is installed.
- Supplied workflows are valid JSON.
- Required Python dependencies import.
- Startup scripts are executable.

#### Runtime validation

On Runpod verify:

- ComfyUI starts.
- Port 8188 responds.
- Models are detected.
- No missing-node errors appear.
- No missing-model errors appear.
- SageAttention is active.
- The distilled I2V workflow can generate a video.
- The distilled T2V workflow can generate a video.

Test the base workflows if resources and time permit.

Do not claim successful video generation without actual GPU testing.

### 15. Performance

Prioritize inference throughput.

Our existing LTX configuration produces approximately 20-second clips at 960×544 in four minutes on an A100.

This is the performance reference.

Measure:

- Cold-start time.
- Model-load time.
- Generation time.
- Sampling performance.
- Peak VRAM.
- GPU utilization.
- Actual output duration.
- Presence of audio.

Test SageAttention against the compatible default attention backend if practical.

Do not assume SageAttention is faster without verification.

The target is a responsive environment that supports repeated rapid creative experimentation.

### 16. What not to build

Do not add:

- Other video model families.
- H3.
- WAN.
- Flux.
- A custom web application.
- A separate orchestration platform.
- A serverless inference handler.
- A database.
- A job scheduler.
- A custom prompt-enhancement system.
- New filmmaking workflows beyond the supplied four.
- Unnecessary custom ComfyUI nodes.
- Automatic upscaling pipelines.
- Unnecessary monitoring services.
- A complicated configuration framework.

Use ComfyUI itself as the interface.

Keep everything maintainable and close to upstream.

### 17. Implementation sequence

**Phase 1 — Inspect**

Study `LTX-SETUP`, the official Runpod ComfyUI base and the Sulphur Hugging Face repository.

Identify reusable implementation details and dependencies.

**Phase 2 — Implement**

Create the sibling `SULPHUR-SETUP` project.

Implement the Dockerfile, startup scripts, model downloads and official workflows.

Include SageAttention.

**Phase 3 — Publish**

Commit and push to the GitHub repository.

Build exclusively through GitHub Actions.

Publish the successfully built image as:

`ghcr.io/<github-owner>/sulphur-2:2`

**Phase 4 — Deploy**

Configure the Runpod template using the published image.

Verify boot, model downloads and UI availability.

**Phase 5 — Test**

Validate workflow operation and run short inference tests.

Fix any issues through GitHub commits and GitHub Actions rebuilds.

### 18. Completion report

When finished, provide:

1. GitHub repository URL.
2. GHCR image reference with tag `2`.
3. Published image digest.
4. GitHub Actions build result.
5. ComfyUI version.
6. CUDA and PyTorch versions.
7. SageAttention version and validation status.
8. Installed Sulphur models.
9. List of working workflows.
10. Runpod template details.
11. Storage usage.
12. Inference benchmark results, if measured.
13. Any outstanding issues.

Clearly distinguish successfully tested capabilities from features that are installed but not yet tested.

## Final Engineering Priorities

In order:

1. **Simple, reliable deployment.**
2. **GitHub Actions builds only.**
3. **SageAttention acceleration.**
4. **Correct official Sulphur workflows.**
5. **Fast distilled generation.**
6. **200 GB storage budget.**
7. **Persistent Hugging Face model caching.**
8. **Minimal maintenance overhead.**

The finished project should feel like the official Runpod ComfyUI template with Sulphur already integrated, not a new platform.

**Build the smallest practical solution that does the job well.**
