# Runpod setup

The [main README](https://github.com/acdevmedia/comfyui-sulphur#readme) is the deployment guide for both GitHub and the Runpod template. It covers secrets, GPU selection, model downloads, workflows, storage, troubleshooting and technical settings.

Template ID: `b551wbs9zm`  
Image: `ghcr.io/acdevmedia/sulphur-comyfui:2`  
Storage: 200 GB container disk, no persistent volume  
Application port: 8188 HTTP

The template uses `HF_TOKEN={{ RUNPOD_SECRET_HUGGINGFACE_TOKEN }}`. Add a Runpod Secret named `HUGGINGFACE_TOKEN` before deployment.
