#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p /workspace/logs /workspace/runpod-slim
exec > >(tee -a /workspace/logs/sulphur-startup.log) 2>&1
trap 'echo "[ERROR] Setup failed at line $LINENO (exit $?). See /workspace/logs/sulphur-startup.log. Fix the reported issue and restart; completed downloads are retained."' ERR
echo "[startup] Sulphur 2 — $(date -Is)"
echo '[startup] Steps: GPU check → attention kernel check → models → workflows → official Runpod startup → ComfyUI.'
echo '[storage] Models, workflows, inputs and videos live under /workspace/runpod-slim. Keep the volume when replacing the pod. Deleting a pod volume deletes its data.'
echo '[versions] ComfyUI v0.42.1; CUDA 12.8; PyTorch 2.10.0+cu128; SageAttention 1.0.6. No package installs or updates are performed by Sulphur at boot.'
/opt/sulphur/scripts/validate.sh runtime
/opt/sulphur/scripts/download-models.sh
args=/workspace/runpod-slim/comfyui_args.txt
if [[ ! -f "$args" ]]; then
  case "${COMFYUI_ATTENTION:-sage}" in
    sage) printf '%s\n' '--use-sage-attention' > "$args" ;;
    pytorch) printf '%s\n' '--use-pytorch-cross-attention' > "$args" ;;
    *) echo '[attention] ERROR: COMFYUI_ATTENTION must be sage or pytorch.'; exit 1 ;;
  esac
fi
echo '[attention] Launch settings are in /workspace/runpod-slim/comfyui_args.txt. Existing user settings are preserved.'
if ! grep -q '^--use-sage-attention' "$args"; then echo '[attention] NOTICE: SageAttention is installed but your launch file selects another backend. No SageAttention performance claim applies.'; fi
echo '[startup] Starting the official Runpod services. Wait for "ComfyUI is READY on port 8188", then use Connect → HTTP 8188.'
exec /start.sh "$@"
