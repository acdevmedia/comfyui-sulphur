# Runpod deployment

Use `ghcr.io/acdevmedia/sulphur-2:2`. Allocate 200 GB total: 40 GB container disk and 160 GB persistent pod volume mounted at `/workspace`. The default models occupy about 40.3 GB of that volume. A pod volume survives stop/start; it is deleted when its pod is terminated. For persistence across pod replacement use a Runpod network volume mounted at `/workspace`, or back up and restore your pod volume first. Network volume billing is separate from GPU billing.

Select A100 SXM4 80 GB, HTTP port `8188`, and optionally SSH `22/tcp`. No Runpod or GitHub API credentials belong in the pod. Supply only `HF_TOKEN` when authenticated Hugging Face access is necessary. Protect access to ComfyUI using Runpod's available access controls; ComfyUI itself does not provide authentication here.

First boot verifies GPU and SageAttention, checks free space, downloads only missing pinned files, validates hashes, and installs workflows into `/workspace/runpod-slim/ComfyUI/user/default/workflows/Sulphur/2/<variant>/`. Open Connect → HTTP 8188 after the READY log. First launch includes model download time. Choose I2V distilled or T2V distilled first. Upload an image for I2V and enter your prompt.

Settings: `SULPHUR_MODEL_VARIANT=fp8` (default), `bf16`, or `native-distilled`; `HF_HOME=/workspace/.cache/huggingface`. Set `COMFYUI_ATTENTION=pytorch` on the first boot to compare attention backends. Once the launch file exists, edit `/workspace/runpod-slim/comfyui_args.txt`: replace `--use-sage-attention` with `--use-pytorch-cross-attention`, or reverse it, then restart. The file is user-owned and is never overwritten. SageAttention's kernel validation still runs so a broken installation is reported.

To upgrade: stop generation, back up workflows and outputs, record the current image digest, pull/recreate using the new `:2` image while retaining the same persistent mount. The official startup syncs baked core and KJNodes while preserving models/input/output/user. Sulphur workflows are installed only when absent; import a new version manually if an existing packaged workflow was edited. Roll back using the previous immutable image digest. Never use Manager or `git pull` as the deployment update mechanism.

Model downloads are resumable through Hugging Face local-directory metadata; there is no second Hub blob cache. The downloader checks expected size and SHA256 before recording completion. A valid completed file is reused without network access. If a file is suspect, remove its adjacent `.verified.json` marker to force full verification on restart.
