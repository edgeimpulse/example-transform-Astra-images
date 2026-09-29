![GPT-6 Astra](gpt-6-astra.png)

# Astra Synthetic Data Block

An Edge Impulse custom synthetic data block that generates images with GPT-6 Astra and GPT Image 2.5 and uploads them to your project. In Studio it appears as **Astra Synthetic Data**.

Custom synthetic data blocks require the Edge Impulse Enterprise plan. They run without input files: Studio passes parameters and environment variables to the container, and the container uploads what it generates through the Ingestion API.

[transform.py](transform.py) calls the OpenAI Responses API with `gpt-6-astra` and the `image_generation` tool, using `gpt-image-2.5-sunburst` or `gpt-image-2.5-flare`. It checks that each result is a valid PNG, then uploads it to Edge Impulse. [synthetic_blocks_tutorial.md](synthetic_blocks_tutorial.md) walks through the code and how to extend it.

## Requirements

- [Edge Impulse CLI](https://docs.edgeimpulse.com/tools/clis/edge-impulse-cli/installation)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- An OpenAI API key with access to GPT-6 Astra and GPT Image
- An Edge Impulse project API key, from **Dashboard > Keys**

Check the tools are installed:

```bash
edge-impulse-blocks --version
docker version
```

## Parameters

| Studio field | Passed as | Default |
| --- | --- | --- |
| OpenAI API Key | `OPENAI_API_KEY` environment variable | none |
| Prompt | `--prompt` | `A photo of a factory worker wearing a hard hat` |
| Label | `--label` | `hard_hat` |
| Number of images | `--images` | `3` |
| Image model | `--image-model` | `gpt-image-2.5-sunburst` |
| Upload to category | `--upload-category` (`split`, `training`, `testing`) | `split` |

Studio also passes `--synthetic-data-job-id`. The block sends it as the `x-synthetic-data-job-id` header on every upload, which is what makes samples preview on the **Synthetic data** tab.

Each sample is uploaded with `generated_by`, `image_model`, and `prompt` metadata, plus `revised_prompt` when OpenAI returns one.

## Test Locally

Synthetic data blocks don't work with `edge-impulse-blocks runner`, so build and run the container directly. Set `OPENAI_API_KEY` and `EI_PROJECT_API_KEY` in your shell first. `-e NAME` with no value passes each key through without writing it into the command.

```bash
docker build -t astra-synthetic-data .
```

Generate one image without uploading it. It is saved to `output/`:

```bash
docker run --rm \
  -e OPENAI_API_KEY \
  -v "$PWD/output:/app/output" \
  astra-synthetic-data \
  --prompt 'A photo of a factory worker wearing a hard hat' \
  --label hard_hat \
  --images 1 \
  --skip-upload
```

Generate one image and upload it to your project:

```bash
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

The job ID here is a placeholder, so check the sample in **Data acquisition** rather than the Synthetic data tab.

## Publish

`.ei-block-config` is gitignored. On a fresh clone, run `edge-impulse-blocks init` first and choose the synthetic data block type. Then push:

```bash
edge-impulse-blocks push
```

In an Enterprise project, open **Data acquisition > Synthetic data**, pick **Astra Synthetic Data**, and generate a small batch to check the previews and labels.

## Agent Skill

[.github/skills/create-synthetic-data-block/SKILL.md](.github/skills/create-synthetic-data-block/SKILL.md) is a GitHub Copilot skill for extending this block. Copilot loads skills from `.github/skills` when this folder is open. Run `/create-synthetic-data-block` in Copilot Chat, or name the skill in a prompt:

```text
Use the create-synthetic-data-block skill to add a quality option to the Astra block.
Keep the GPT-6 Astra Responses API call and the synthetic data job ID header.
```

[AGENTS.md](AGENTS.md) holds the rules that apply to any change in this repository.

## Further Reading

- [Custom synthetic data blocks](https://docs.edgeimpulse.com/studio/organizations/custom-blocks/custom-synthetic-data-blocks)
- [parameters.json reference](https://docs.edgeimpulse.com/tools/specifications/files/parameters-json)
- [Ingestion API](https://docs.edgeimpulse.com/apis/ingestion)
- [GPT-6 Astra model](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [OpenAI image generation](https://developers.openai.com/api/docs/guides/image-generation)
- [Install and write Agent Skills](https://docs.edgeimpulse.com/tutorials/topics/ai-agents/create-edge-impulse-skill)
