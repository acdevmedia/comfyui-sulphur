# Official Runpod image, resolved from upstream comfyui-v1.4.1. No local builds.
FROM runpod/comfyui:1.4.1-comfyuiv0.35.0-cuda12.8@sha256:d411ebacf3fdbc98ded7f78f06ac12aae20c08041cde79ab08173c156d04aae5
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
ENV SULPHUR_VERSION=2 SULPHUR_MODEL_VARIANT=fp8 \
    HF_HOME=/workspace/.cache/huggingface HF_HUB_DISABLE_TELEMETRY=1 \
    COMFYUI_ATTENTION=sage PYTHONUNBUFFERED=1
# System torch/CUDA remain exactly those provided by the pinned official image.
RUN curl -fsSL https://github.com/Comfy-Org/ComfyUI/archive/63be2f9b82ad0dac88a7ceaa28a9cf3154125a18.tar.gz -o /tmp/comfy.tar.gz && \
    rm -rf /opt/comfyui-baked && mkdir /opt/comfyui-baked && \
    tar xzf /tmp/comfy.tar.gz --strip-components=1 -C /opt/comfyui-baked && rm /tmp/comfy.tar.gz && \
    mkdir -p /opt/comfyui-baked/custom_nodes/ComfyUI-KJNodes && \
    curl -fsSL https://github.com/kijai/ComfyUI-KJNodes/archive/92783f23cf9df6a57ca4c5e035b4714ac0e2bcb4.tar.gz | \
    tar xz --strip-components=1 -C /opt/comfyui-baked/custom_nodes/ComfyUI-KJNodes && \
    python3 -m pip install --no-cache-dir -c /opt/comfyui-runtime-constraints.txt \
    -r /opt/comfyui-baked/requirements.txt \
    -r /opt/comfyui-baked/custom_nodes/ComfyUI-KJNodes/requirements.txt \
    'sageattention==1.0.6' 'huggingface_hub==0.36.0' && \
    printf 'COMFYUI_VERSION=v0.42.1\nSULPHUR_VERSION=2\n' > /opt/comfyui-baked/.runpod-bundle-version && \
    python3 -m pip freeze > /opt/sulphur-python-lock.txt
COPY scripts /opt/sulphur/scripts
COPY versions /opt/sulphur/versions
RUN chmod +x /opt/sulphur/scripts/*.sh && /opt/sulphur/scripts/validate.sh build && python3 /opt/sulphur/scripts/check-build-server.py
EXPOSE 8188
ENTRYPOINT ["/opt/sulphur/scripts/entrypoint.sh"]
