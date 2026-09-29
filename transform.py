import argparse
import base64
import binascii
import json
import os
import sys
import uuid
from pathlib import Path

import requests


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = "gpt-6-astra"
VALID_IMAGE_MODELS = {"gpt-image-2.5-sunburst", "gpt-image-2.5-flare"}
VALID_UPLOAD_CATEGORIES = {"split", "training", "testing"}


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate a synthetic image dataset with GPT-6 Astra."
    )
    parser.add_argument("--prompt", required=True, help="Image generation prompt")
    parser.add_argument("--label", required=True, help="Label assigned to generated images")
    parser.add_argument("--images", required=True, type=int, help="Number of images to generate")
    parser.add_argument(
        "--image-model",
        default="gpt-image-2.5-sunburst",
        choices=sorted(VALID_IMAGE_MODELS),
        help="GPT Image model invoked by GPT-6 Astra",
    )
    parser.add_argument(
        "--upload-category",
        default="split",
        choices=sorted(VALID_UPLOAD_CATEGORIES),
        help="Edge Impulse data category for generated images",
    )
    parser.add_argument(
        "--synthetic-data-job-id",
        type=int,
        help="Synthetic data job identifier supplied by Edge Impulse",
    )
    parser.add_argument(
        "--out-directory",
        default="output",
        help="Directory where generated images are retained locally",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Generate local images without uploading them to Edge Impulse",
    )
    return parser.parse_args()


def get_ingestion_url(ingestion_host):
    if ingestion_host == "host.docker.internal":
        return f"http://{ingestion_host}:4810"
    if ingestion_host.endswith(".test.edgeimpulse.com"):
        return f"http://ingestion.{ingestion_host}"
    return f"https://ingestion.{ingestion_host}"


def response_error(response):
    try:
        payload = response.json()
    except ValueError:
        return response.text

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return error.get("message") or error.get("code") or json.dumps(error)
    return json.dumps(payload)


def validate_png(image_bytes):
    png_signature = b"\x89PNG\r\n\x1a\n"
    if not image_bytes.startswith(png_signature):
        raise RuntimeError("OpenAI returned data that is not a PNG image")
    if len(image_bytes) < 33 or image_bytes[12:16] != b"IHDR":
        raise RuntimeError("OpenAI returned an invalid PNG image")
    width = int.from_bytes(image_bytes[16:20], "big")
    height = int.from_bytes(image_bytes[20:24], "big")
    if width < 1 or height < 1:
        raise RuntimeError("OpenAI returned a PNG with invalid dimensions")


def generate_image(openai_api_key, prompt, image_model):
    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "input": prompt,
            "tools": [
                {
                    "type": "image_generation",
                    "model": image_model,
                    "action": "generate",
                }
            ],
        },
        timeout=180,
    )
    if not response.ok:
        raise RuntimeError(
            f"OpenAI image generation failed ({response.status_code}): {response_error(response)}"
        )

    payload = response.json()
    outputs = payload.get("output", []) if isinstance(payload, dict) else []
    image_calls = [
        output
        for output in outputs
        if isinstance(output, dict)
        and output.get("type") == "image_generation_call"
        and output.get("result")
    ]
    if not image_calls:
        raise RuntimeError("OpenAI response did not contain an image_generation_call result")

    image_call = image_calls[0]
    try:
        image_bytes = base64.b64decode(image_call["result"], validate=True)
    except (KeyError, ValueError, binascii.Error) as error:
        raise RuntimeError("OpenAI returned invalid base64 image data") from error

    if not image_bytes:
        raise RuntimeError("OpenAI returned an empty image")
    validate_png(image_bytes)

    return image_bytes, image_call.get("revised_prompt")


def upload_image(ingestion_url, project_api_key, upload_category, label, filename, image_bytes, metadata, job_id):
    response = requests.post(
        f"{ingestion_url}/api/{upload_category}/files",
        headers={
            "x-api-key": project_api_key,
            "x-label": label,
            "x-metadata": json.dumps(metadata),
            "x-synthetic-data-job-id": str(job_id),
        },
        files={"data": (filename, image_bytes, "image/png")},
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(
            f"Edge Impulse upload failed ({response.status_code}): {response_error(response)}"
        )

    payload = response.json()
    files = payload.get("files", []) if isinstance(payload, dict) else []
    if (
        not isinstance(payload, dict)
        or payload.get("success") is not True
        or not isinstance(files, list)
        or not files
        or not isinstance(files[0], dict)
        or files[0].get("success") is not True
    ):
        raise RuntimeError(f"Edge Impulse upload failed: {json.dumps(payload)}")


def main():
    args = parse_arguments()
    prompt = args.prompt.replace("\\n", "\n").strip()
    if not prompt:
        raise RuntimeError("--prompt must not be empty")
    label = args.label.strip()
    if not label:
        raise RuntimeError("--label must not be empty")
    if any(character in label for character in "\r\n"):
        raise RuntimeError("--label must not contain newlines")
    if args.images < 1:
        raise RuntimeError("--images must be at least 1")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")

    project_api_key = os.getenv("EI_PROJECT_API_KEY")
    if not args.skip_upload and not project_api_key:
        raise RuntimeError("Missing EI_PROJECT_API_KEY")
    if not args.skip_upload and args.synthetic_data_job_id is None:
        raise RuntimeError("Missing --synthetic-data-job-id")

    output_directory = Path(args.out_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    ingestion_url = get_ingestion_url(os.getenv("EI_INGESTION_HOST", "edgeimpulse.com"))
    for image_index in range(args.images):
        print(f"Generating image {image_index + 1} of {args.images}...", flush=True)
        image_bytes, revised_prompt = generate_image(
            openai_api_key, prompt, args.image_model
        )
        filename = f"astra.{uuid.uuid4().hex}.{image_index}.png"
        output_path = output_directory / filename
        output_path.write_bytes(image_bytes)

        if args.skip_upload:
            print(f"Saved {output_path}")
            continue

        metadata = {
            "generated_by": OPENAI_MODEL,
            "image_model": args.image_model,
            "prompt": prompt,
        }
        if revised_prompt:
            metadata["revised_prompt"] = revised_prompt

        upload_image(
            ingestion_url,
            project_api_key,
            args.upload_category,
            label,
            filename,
            image_bytes,
            metadata,
            args.synthetic_data_job_id,
        )
        print(f"Uploaded {filename}")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, RuntimeError, ValueError) as error:
        print(f"Astra synthetic data generation failed: {error}", file=sys.stderr)
        sys.exit(1)