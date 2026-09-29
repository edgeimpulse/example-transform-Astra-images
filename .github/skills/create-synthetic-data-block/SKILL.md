---
name: create-synthetic-data-block
description: "Create, adapt, test, or document an Edge Impulse standalone synthetic data block, including Astra image generation, parameters.json, Docker entry points, Ingestion API uploads, synthetic job IDs, and publishing readiness. Use when adding a synthetic data provider or model to this repository."
argument-hint: "Describe the provider/model and its documented API contract"
---

# Create a Synthetic Data Block

Use this skill to add or change a provider-backed synthetic data block in this repository. The active block is the workspace root.

## Required Facts

The Astra implementation has a confirmed provider contract: use `OPENAI_API_KEY`, call OpenAI's Responses API with `model: "gpt-6-astra"`, request the `image_generation` tool with `gpt-image-2.5-sunburst` or `gpt-image-2.5-flare`, and base64-decode `image_generation_call.result`. Obtain provider documentation before adding any other model, tool setting, or provider.

Read [AGENTS.md](../../../AGENTS.md) and [synthetic_blocks_tutorial.md](../../../synthetic_blocks_tutorial.md) before editing. For current platform details, first consult `https://docs.edgeimpulse.com/llms.txt`, then retrieve the relevant pages for custom synthetic data blocks, `parameters.json`, and the Ingestion API.

## Procedure

1. Confirm `edge-impulse-blocks` is installed, Docker is responding, and root `parameters.json` has `"type": "synthetic-data"`.
2. If the block has not been initialized, run `edge-impulse-blocks init` in the repository root and choose standalone synthetic data. Do not reinitialize an existing block.
3. Define the Studio form in `parameters.json` before implementing code. Keep normal user settings as parameter items, use `secret` for a per-job credential, and use `info.requiredEnvVariables` for a block-level credential configured on push.
4. Keep the Docker entry point on `transform.py`; use the existing HTTP implementation unless a documented dependency simplifies a required provider feature.
5. Parse every declared non-secret parameter plus `--synthetic-data-job-id`. Validate inputs and `OPENAI_API_KEY` before calling the provider.
6. Generate and validate base64-decoded image bytes. Upload each image through the Ingestion API using `EI_PROJECT_API_KEY`, `EI_INGESTION_HOST`, label, provenance metadata, and `x-synthetic-data-job-id`.
7. Build and test with Docker directly. Synthetic data blocks do not support `edge-impulse-blocks runner`. Do not use `--network=none` when the test calls an external provider.
8. Report the generated image, upload result, and any remaining provider-specific limitation. Push only after the user explicitly requests it.

## Security

Never ask the user to paste an API key into chat, source files, `parameters.json`, commit messages, or logs. Have the user enter secrets directly into the terminal or configure them in Studio. Keep `.env`, `.ei-block-config`, and generated output out of version control.