#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p /workspace/logs /workspace/runpod-slim
exec > >(tee -a /workspace/logs/sulphur-startup.log) 2>&1
trap 'echo "[ERROR] Setup failed at line $LINENO (exit $?). See /workspace/logs/sulphur-startup.log. Fix the reported issue and restart; completed downloads are retained."' ERR
echo "[startup] Sulphur 2 — $(date -Is)"
echo '[startup] Steps: GPU check → attention kernel check → models → workflows → official Runpod startup → ComfyUI.'
echo '[storage] Models, workflows, inputs and videos live under /workspace/runpod-slim on 200 GB container storage. There is no persistent volume. Download important outputs before stop/redeploy/delete; container replacement loses local data.'
echo '[versions] ComfyUI v0.42.1; CUDA 12.8; PyTorch 2.10.0+cu128; SageAttention 1.0.6. No package installs or updates are performed by Sulphur at boot.'
# Pods see every host CPU (nproc 192 on A100 hosts) but get a ~20-CPU CFS quota. PyTorch then
# starts 96 threads and is throttled: CPU nodes such as ImageScale and SaveVideo ran ~10x slower.
if [[ -z "${OMP_NUM_THREADS:-}" ]]; then
  if { read -r quota period < /sys/fs/cgroup/cpu.max; } 2>/dev/null; then :; else
    quota=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us 2>/dev/null || echo max)
    period=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us 2>/dev/null || echo 100000)
  fi
  if [[ "$quota" =~ ^[0-9]+$ && "$period" =~ ^[0-9]+$ ]] && (( quota / period >= 1 )); then
    export OMP_NUM_THREADS=$(( quota / period )); else export OMP_NUM_THREADS=$(nproc); fi
fi
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-$OMP_NUM_THREADS}
echo "[cpu] Using $OMP_NUM_THREADS CPU threads (container CPU quota). Set OMP_NUM_THREADS to override."
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
