"""DeepSeek-based text services (OpenAI-compatible API).

Used for editing intermediate artifacts (schema, plan) where we want:
- No subprocess / opencode-server cold start
- Native token streaming

Generation and the coding agent run through opencode + DeepSeek
(see opencode_service); this path hits DeepSeek's OpenAI-compatible endpoint
directly for fast, streamed text edits.
"""

import difflib
import json
import re
from openai import AsyncOpenAI
from api.config import settings
from api.services import file_service
from api.services.sse import publish

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


EDIT_SYSTEM_PROMPT = """You are an expert data engineer editing a synthetic dataset specification.
Apply the requested changes precisely to the artifact. Preserve everything else exactly.

Return:
1. The complete updated markdown artifact.
2. Followed by a fenced JSON block describing what changed:

```json
{"summary": "one-sentence summary", "changes": ["specific change 1", "specific change 2"]}
```

Do not add any preamble, reasoning, or text before the markdown. No "Here's the updated schema:" — start directly with the markdown content."""


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not configured")
        _client = AsyncOpenAI(
            base_url=DEEPSEEK_BASE_URL,
            api_key=settings.deepseek_api_key,
        )
    return _client


async def edit_artifact(project_id: str, artifact_type: str, message: str) -> dict:
    """Edit an artifact using DeepSeek. Streams tokens to the project SSE channel."""
    filename = "data_schema_spec.md" if artifact_type == "schema" else "implementation_dataset.md"
    current = file_service.read_artifact(project_id, filename) or ""
    channel = f"project:{project_id}"

    user_content = (
        f"## Current Artifact\n\n{current}\n\n"
        f"## Requested Changes\n\n{message}"
    )

    client = _get_client()
    stream = await client.chat.completions.create(
        model=settings.deepseek_edit_model,
        messages=[
            {"role": "system", "content": EDIT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        stream=True,
    )

    chunks: list[str] = []
    async for event in stream:
        if not event.choices:
            continue
        delta = event.choices[0].delta
        if delta and delta.content:
            chunks.append(delta.content)
            await publish(channel, {"type": "stream", "step": "edit", "chunk": delta.content})

    raw = "".join(chunks)

    # Split the markdown artifact from the trailing JSON metadata block.
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
    meta = {"summary": "Changes applied", "changes": []}
    if json_match:
        try:
            meta = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
        updated = raw[: json_match.start()].strip()
    else:
        updated = raw.strip()

    diff = list(difflib.unified_diff(
        current.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    ))

    file_service.write_artifact(project_id, filename, updated)
    return {
        "diff": "".join(diff),
        "summary": meta.get("summary", ""),
        "changes": meta.get("changes", []),
    }
