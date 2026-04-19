import base64
import os
import pprint
from typing import Any, Dict, List

import anthropic
import click


def pp(o):
    pprint.pprint(o, indent=2, compact=False, width=120, depth=10)

@click.command()
@click.option(
    "--text-file", "-t",
    required=True,
    type=click.Path(),
    help="A text file to process as part of the technical documentation.",
)
@click.option(
    "--image-file", "-i",
    multiple=True,
    type=click.Path(),
    help="An image to process as part of the technical documentation. May be called zero or more times. Does not support globs.",
)
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(),
    default="documentation.md",
    help="Where the Markdown file should be written to.",
)
@click.option(
    "--model", "-m",
    required=True,
    default="claude-sonnet-4-5",
    help="The Claude Code model to use. A typical 60m video requires a 256k context window.",
)
@click.option(
    "--system-prompt", "-p",
    required=True,
    type=click.Path(),
    default="system_prompt.txt",
    help="The system prompt to use.",
)
def main(text_file: str, image_file: List[str], output: str, model: str, system_prompt: str) -> None:
    prompt: str = ""
    text_content: str = ""
    image_content: List[str] = []

    with open(system_prompt, "r") as s:
        prompt = s.read()

    with open(text_file, "r") as t:
        text_content = t.read()

    for img in image_file:
        with open(img, "rb") as i:
            image_content.append(
                base64.b64encode(i.read()).decode('utf-8')
            )

    content: List[Dict[str, Any]] = []
    content.append({"type": "text", "text": text_content})

    for image in image_content:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": image,
            },
        })

    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )

    message = client.messages.create(
        model=model,
        max_tokens=64000,
        system=prompt,
        messages=[{"role": "user", "content": content}],
        thinking={
            "budget_tokens": 50000,
            "type": "enabled",
            "display": "omitted",
        },
        # temperature=0.2,
        # top_k=40,
        # thinking={
        #     "type": "disabled",
        # },
        stream=True,
    )

    with open(output, "wt", encoding="utf-8") as out:
        for event in message:
            if event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    print(event.delta.text)
                    out.write(event.delta.text)

if __name__ == '__main__':
    main()
