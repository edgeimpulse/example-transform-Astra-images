# Astra Synthetic Data Block Instructions

This repository implements an Edge Impulse custom synthetic data block. It is a standalone transformation block that generates samples and uploads them through the Ingestion API. Read [synthetic_blocks_tutorial.md](synthetic_blocks_tutorial.md) before implementing a provider adapter.

## Setup Gate

Before editing block code or testing a provider, complete these checks and report the result:

1. Confirm `edge-impulse-blocks` is installed and on `PATH`.
2. Confirm Docker Desktop is installed and the Docker daemon responds.
3. Confirm `parameters.json` declares `"type": "synthetic-data"`.
4. If `.ei-block-config` is absent, run `edge-impulse-blocks init` from the repository root and choose a standalone synthetic data block. Do not reinitialize an existing block.

Do not request credentials in chat. The user must enter keys directly in the terminal or configure them in Studio.

## Provider Adapter Rules

The Astra provider contract is documented. Send `POST` requests to OpenAI's Responses API with `model: "gpt-6-astra"` and an `image_generation` tool using `gpt-image-2.5-sunburst` or `gpt-image-2.5-flare`. The response contains base64 PNG bytes in the first `image_generation_call.result`. Authenticate with `OPENAI_API_KEY`.

For a different provider or an undocumented GPT Image setting, find the facts in the provider documentation or ask the user before changing the adapter.

For each model/provider implementation:

1. Add a user-facing parameter to `parameters.json` for every runtime option the user must choose.
2. Parse every parameter in the Docker entry-point script with the same `param` name as its command-line flag.
3. Use the existing `OPENAI_API_KEY` `secret` parameter for the OpenAI credential. Use a `secret` parameter for a new per-job credential, or `info.requiredEnvVariables` for a block-level value supplied during `edge-impulse-blocks push`.
4. Read `EI_PROJECT_API_KEY` and `EI_INGESTION_HOST` from the environment. Never hard-code an Edge Impulse endpoint, API key, or provider secret.
5. Parse `--synthetic-data-job-id` and send it as the `x-synthetic-data-job-id` Ingestion API request header for every uploaded sample.
6. Include provider, model/version, prompt, and generation settings in upload metadata when available.
7. Fail clearly on invalid parameters, missing required environment variables, unsupported image output, provider errors, and unsuccessful ingestion responses.

## Test and Publish

Synthetic data blocks cannot be tested with `edge-impulse-blocks runner`. Build and run the Docker image directly. The user sets `OPENAI_API_KEY` and `EI_PROJECT_API_KEY` in their shell, and `-e NAME` passes them through:

```bash
docker build -t astra-synthetic-data .
docker run --rm -e EI_PROJECT_API_KEY -e OPENAI_API_KEY \
  astra-synthetic-data --synthetic-data-job-id 123456789 --prompt 'test' \
  --label test --images 1 --image-model gpt-image-2.5-sunburst \
  --upload-category training
```

Use Docker's default network when calling an external generation provider. Do not add `--network=none` to an integration test that must reach the provider and Edge Impulse.

After a successful local test, `edge-impulse-blocks push` publishes the current block. Only push when the user has explicitly asked to publish or approved that side effect.
