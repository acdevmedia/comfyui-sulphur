# Validation status

Implementation checks: workflow JSON, graph references, model source revisions, model SHA256 metadata, storage budget and shell syntax validated locally. No local image builds are permitted or performed.

GitHub Actions build and Runpod GPU validation are pending. Image import checks do not prove inference works. No cold-start, generation throughput, VRAM, GPU utilization, output duration or audio measurements are claimed until an actual GPU run completes.


Workflows 07 to 10 have only been checked statically. `scripts/check-source.py` verifies each API source and packaged panel against the node schemas: required inputs, output slots, link types, the guide reaching the sampler and being cropped back out, and the clip's sound being held and kept. Schemas for the LTXVideo and Sphere Light nodes were read from source at their pinned commits, because the saved `object_info` predates them. The Actions CPU build confirms the nodes load and the inputs resolve. Relight was compared with Lightricks' official workflow at the pinned revision. Its ball patch, position, scaling, intensity and free-running audio latent now match. It keeps this bundle's checkpoint, adapter and sampling. The workflow names the older `SphereLightNode`, and the pinned Manual node's scene, camera and light formula are unchanged from it. Nothing has generated on a GPU. The three gated LoRA hashes are pinned, and `scripts/pin-gated-models.py` confirmed them against Hugging Face with an account that has accepted their licences.
