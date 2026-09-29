# Adding a Model to a Synthetic Data Block

This guide explains how the Astra block works and how to extend it. The block uses OpenAI's Responses API: GPT-6 Astra calls the `image_generation` tool, which returns a base64 PNG that the block uploads to Edge Impulse.

## What You Are Building

A synthetic data block is a transformation block that runs in standalone mode. Studio starts the container with environment variables and the arguments defined in `parameters.json`. The entry point generates samples and uploads them with the Ingestion API.

Studio also passes `--synthetic-data-job-id`. Each upload must send that value in the `x-synthetic-data-job-id` header. Without it, samples are not linked to the job and don't appear in the live preview.

## 1. Check the Development Environment

Install the [Edge Impulse CLI](https://docs.edgeimpulse.com/tools/clis/edge-impulse-cli/installation) and Docker Desktop, then run:

```bash
edge-impulse-blocks --version
docker version
```

`.ei-block-config` is gitignored, so on a fresh clone or a new block, run this from the repository root:

```bash
edge-impulse-blocks init
```

Choose the synthetic data block type. Only mount a storage bucket if generation needs files from it. The initializer creates `.ei-block-config` and, if missing, a starter `parameters.json`.

## 2. Record the Model Contract

Before editing code, write down these provider-specific facts:

| Question | Example decision |
| --- | --- |
| How is the provider called? | `POST https://api.openai.com/v1/responses` with `model: "gpt-6-astra"` |
| What credential is required? | `OPENAI_API_KEY`, supplied as an environment variable |
| What inputs does a user control? | Prompt, label, image count, image model, and upload category |
| What does a response contain? | Base64 PNG data in `image_generation_call.result` |
| Which image tools are available? | `gpt-image-2.5-sunburst` and `gpt-image-2.5-flare` |
| How is model provenance exposed? | GPT-6 Astra, image model, prompt, and revised prompt metadata |

For a new provider or GPT Image setting, confirm the API, credential, output format, and supported options in the provider's documentation first. Don't add placeholder endpoints or settings you haven't verified.

## 3. Define the Studio Interface

`parameters.json` holds block metadata in `info` and the Studio form in `parameters`. Each non-secret parameter is passed to the entry point as `--<param>`. A `secret` parameter is passed as an environment variable named after its `param`.

The block already exposes `OPENAI_API_KEY`, prompt, label, image count, image model, and upload category. A new setting follows the same pattern. For example, a GPT Image quality option:

```json
{
  "name": "Quality",
  "value": "auto",
  "type": "select",
  "valid": ["low", "medium", "high", "xhigh", "max", "auto"],
  "help": "Rendering quality passed to GPT Image.",
  "param": "quality"
}
```

The `param` must match the `argparse` flag exactly: `"quality"` maps to `--quality`.

Keep `OPENAI_API_KEY` as a per-job `secret`. For a block-level value, add `"requiredEnvVariables": ["VARIABLE_NAME"]` under `info`. `edge-impulse-blocks push` prompts for it, and it can be changed later in Studio.

Never put a real key in `parameters.json`, a committed `.env` file, source code, or a chat prompt.

## 4. Container Files

| File | Responsibility |
| --- | --- |
| `Dockerfile` | Python 3.11 slim image. Installs dependencies and runs `transform.py` as the `ENTRYPOINT`. |
| `requirements.txt` | Pins `requests`, the only dependency. |
| `transform.py` | Parses arguments, calls OpenAI, checks the image, and uploads it. |
| `.dockerignore` | Keeps local output, virtual environments, `.env` files, and block config out of the build context. |

The block calls the Responses API over plain HTTP, not through the OpenAI SDK or the older DALL-E Image API.

## 5. How `transform.py` Works

1. Parses every non-secret parameter plus `--synthetic-data-job-id`, `--out-directory`, and `--skip-upload`.
2. Checks the prompt, label, and image count, and stops if `OPENAI_API_KEY` is missing. Unless `--skip-upload` is set, it also requires `EI_PROJECT_API_KEY` and a job ID.
3. For each image, calls the Responses API with `gpt-6-astra` and an `image_generation` tool set to `action: "generate"`, then base64-decodes the first `image_generation_call.result`.
4. Checks the bytes are a PNG with valid dimensions and writes a copy to `output/` for inspection.
5. Uploads the PNG to `https://ingestion.<EI_INGESTION_HOST>/api/<category>/files` with the project key, label, metadata, and `x-synthetic-data-job-id`.
6. Stops on an HTTP error or on `success: false` in the response body. The Ingestion API can return HTTP 200 while rejecting a file, so the body is always checked.

Each sample gets this metadata:

```json
{
  "generated_by": "gpt-6-astra",
  "image_model": "gpt-image-2.5-sunburst",
  "prompt": "<submitted prompt>",
  "revised_prompt": "<prompt as rewritten by GPT-6 Astra, when returned>"
}
```

To wire in the quality example from step 3, add `--quality` to `parse_arguments()`, pass it as `"quality"` in the `image_generation` tool, and add it to the metadata so samples stay traceable.

## 6. Build and Run the Container

Synthetic data blocks are not supported by `edge-impulse-blocks runner`. Build and run the image yourself, with `OPENAI_API_KEY` and `EI_PROJECT_API_KEY` set in your shell:

```bash
docker build -t astra-synthetic-data .
docker run --rm \
  -e OPENAI_API_KEY \
  -e EI_PROJECT_API_KEY \
  astra-synthetic-data \
  --synthetic-data-job-id 123456789 \
  --prompt 'A photo of a factory worker wearing a hard hat' \
  --label hard_hat \
  --images 1 \
  --image-model gpt-image-2.5-sunburst \
  --upload-category training
```

To generate without uploading, drop `EI_PROJECT_API_KEY` and the job ID, add `--skip-upload`, and mount `-v "$PWD/output:/app/output"` to keep the image. The test needs network access to OpenAI and the Ingestion API, so don't use `--network=none`.

Before publishing, check that:

- The image looks right and has the expected dimensions.
- The label and category are correct in the project.
- The metadata shows the model, image model, and prompt.
- OpenAI and Ingestion API errors are readable and don't print keys.

The job ID above is a placeholder, so the live preview can only be checked after publishing.

## 7. Publish and Verify in Studio

```bash
edge-impulse-blocks push
```

In an Enterprise project, open **Data acquisition > Synthetic data**, select the block, enter a prompt and label, and generate a small batch. Check the preview, labels, metadata, and split. If samples upload but no preview appears, check that the upload header carries the job ID Studio passed to the container.

## 8. Use an Agent

The skill at [.github/skills/create-synthetic-data-block/SKILL.md](.github/skills/create-synthetic-data-block/SKILL.md) covers this workflow. In GitHub Copilot Chat, run `/create-synthetic-data-block`, or mention the provider and "synthetic data block" in your request.

Give the agent the provider documentation or the contract table from step 2, and ask for one focused change:

```text
Use the create-synthetic-data-block skill. Add the GPT Image quality setting to
the Astra block as a select parameter with a matching --quality argument. Keep
the GPT-6 Astra Responses API call and the synthetic data job ID header.
Do not push the block.
```

The skill tells the agent to ask for missing API details and to run the Docker test before calling the work done.

## Troubleshooting

| Symptom | First check |
| --- | --- |
| Studio form value is ignored | Check that the `parameters.json` `param` and the `argparse` flag match exactly. |
| Provider reports a missing key | Set the `OPENAI_API_KEY` secret in Studio, or export it in your shell and pass it with `-e OPENAI_API_KEY`. |
| OpenAI returns a permission error | Your OpenAI organization may need [API Organization Verification](https://help.openai.com/en/articles/10910291-api-organization-verification) before it can use GPT Image models. |
| OpenAI response has no image | Confirm the request uses `gpt-6-astra` with an `image_generation` tool and a supported GPT Image 2.5 model. |
| Upload fails with `success: false` | Read the `files[].error` message in the printed response. The Ingestion API reports per-file errors with HTTP 200. |
| Samples are ingested but no synthetic preview appears | Confirm every ingestion request includes `x-synthetic-data-job-id`. |
| Local Docker test cannot reach a provider | Remove `--network=none` and confirm the Docker daemon has network access. |
| A secret appeared in output or source control | Revoke it, create a replacement, remove it from history as appropriate, and keep future values in environment variables or Studio. |

For the authoritative platform contract, use the [custom synthetic data blocks](https://docs.edgeimpulse.com/studio/organizations/custom-blocks/custom-synthetic-data-blocks), [parameters.json](https://docs.edgeimpulse.com/tools/specifications/files/parameters-json), and [Ingestion API](https://docs.edgeimpulse.com/apis/ingestion) documentation.