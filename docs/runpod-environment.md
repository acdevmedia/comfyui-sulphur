# Runpod template environment

Synced from account template **Sulfur 2 LTX 2.3 ComfyUI Video One-Click** (`b551wbs9zm`) on 2026-10-30.

[Open template](https://console.runpod.io/deploy?template=b551wbs9zm)

Image: `ghcr.io/acdevmedia/sulphur-comyfui:2`. Container disk: **200 GB**. Workspace: `/workspace`. Template service: `8188/http`. No persistent volume is requested by the repository template configuration.

`config/runpod-template.json` holds the Pod defaults. `.runpod/template-source.json` records the account source. `.runpod/hub.json` exposes the same values through Hub inputs or fixed values. `.runpod/tests.json` uses the same defaults for readiness tests.

## Credentials

Create Runpod Secret `HUGGINGFACE_TOKEN` with a Hugging Face read token and accept the gated model terms. Secret references are passed through unchanged; no credential values are stored here. Optional S3 credentials are only needed when backup is enabled.

## Template variables

### `COMFYUI_ATTENTION`

Default: `sage`.

Attention backend used when the launch settings are first created. Existing user launch settings are preserved.

### `HF_HOME`

Default: `/workspace/.cache/huggingface`.

Hugging Face cache directory on container storage.

### `HF_TOKEN`

Default: `{{ RUNPOD_SECRET_HUGGINGFACE_TOKEN }}`.

Hugging Face read token supplied through the Runpod Secret HUGGINGFACE_TOKEN. Accept gated model terms before deployment.

### `SULPHUR_MODEL_VARIANT`

Default: `fp8`.

Checkpoint precision: fp8 (template default) or bf16. Selects model downloads and newly installed workflow checkpoint names.

### `SULPHUR_VERSION`

Default: `2`.

Baked Sulphur version profile. Keep 2; this image does not switch profiles at runtime.

## Hub additions and differences

The Pod template uses the root image and HTTP 8188. The Hub builds `.runpod/Dockerfile`, retaining ComfyUI internally on 8188 and exposing its gateway on HTTP 8000. Readiness uses HTTP 8001. The original Pod template keeps its existing image and ports.

- `PORT=8000`: Hub gateway HTTP/WebSocket port. This is separate from the template ComfyUI port 8188.
- `PORT_HEALTH=8001`: Hub readiness port; /ping returns 503 until ComfyUI is ready.

Template defaults are preserved, including optional placeholders. Update optional settings before enabling their feature. Workflow defaults apply to newly installed workflow files; existing user edits are preserved. A Serverless browser session requires a single active worker and authenticated HTTP/WebSocket access as described in `.runpod/README.md`.

## Account template metadata

Visibility: public. No custom entrypoint or start command is set in the account template.

The account API leaves `startJupyter` and `startSsh` unset. Its explicit service ports list only `8188/http`.
