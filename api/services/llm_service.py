"""DeepSeek-based text services (OpenAI-compatible API).

Schema/plan generation and artifact edits are single-shot text generation, so
they hit DeepSeek directly (one streamed call) instead of the opencode agent —
much faster (no agent loop / huge system prompt / tool round-trips) and the file
is written here. Only the coding step needs opencode (it writes many files,
runs uv/pytest, builds its own tools); see opencode_service.
"""

import difflib
import json
import re
from pathlib import Path
from openai import AsyncOpenAI
from api.config import settings
from api.services import file_service
from api.services.sse import publish

DEEPSEEK_BASE_URL = "https://api.deepseek.com"

GEN_SYSTEM_PROMPT = (
    "You are an expert data engineer. Follow the instructions and produce ONLY "
    "the requested markdown artifact — no preamble, no explanations, no code-fence "
    "wrapper. Start directly with the markdown (a top-level '# ' heading)."
)


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


# ---------------------------------------------------------------------------
# Single-shot generation (schema, plan) — direct DeepSeek, no opencode agent.
# ---------------------------------------------------------------------------

def _read_command(name: str) -> str:
    return (Path(settings.commands_dir) / f"{name}.md").read_text(encoding="utf-8")


def _read_strategy_templates() -> str:
    d = Path(settings.templates_dir)
    blocks = [f"### {f.name}\n\n{f.read_text(encoding='utf-8')}" for f in sorted(d.glob('*.md'))]
    return "\n\n".join(blocks)


def _has_source_data(project_id: str) -> bool:
    d = file_service.project_dir(project_id) / "data"
    return d.is_dir() and any(p.is_file() for p in d.iterdir())


def _clean(text: str) -> str:
    """Strip any preamble before the first markdown header / fence and peel an
    outer code-fence wrapper (defensive — the system prompt asks for clean md)."""
    lines = text.strip().splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith(("#", "```"))), 0)
    lines = lines[start:]
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
        for j in range(len(lines) - 1, -1, -1):
            if lines[j].strip() == "```":
                lines = lines[:j]
                break
    return "\n".join(lines).strip()


async def _stream(user_content: str, channel: str, step: str) -> str:
    """One streamed DeepSeek completion; pushes deltas to the SSE channel."""
    client = _get_client()
    stream = await client.chat.completions.create(
        model=settings.deepseek_authoring_model,
        messages=[
            {"role": "system", "content": GEN_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        stream=True,
    )
    chunks: list[str] = []
    async for event in stream:
        if not event.choices:
            continue
        delta = event.choices[0].delta
        if delta and delta.content:
            chunks.append(delta.content)
            await publish(channel, {"type": "stream", "step": step, "chunk": delta.content})
    return "".join(chunks)


async def generate_schema(project_id: str, description: str) -> str:
    """Generate data_schema_spec.md in one direct DeepSeek call."""
    channel = f"project:{project_id}"
    await publish(channel, {"type": "step_progress", "step": "schema", "status": "running", "message": "Generating schema (DeepSeek)..."})

    desc = file_service.read_artifact(project_id, "dataset_description.md") or description
    profile = file_service.read_artifact(project_id, "data_profile.md")
    parts = [_read_command("generate-schema"), f"\n\n---\n\n## dataset_description.md\n\n{desc}"]
    if profile:
        parts.append(f"\n\n## data_profile.md (precomputed statistics of the real source data)\n\n{profile}")

    schema = _clean(await _stream("\n".join(parts), channel, "schema"))
    if not schema:
        raise RuntimeError("schema generation returned empty output")

    file_service.write_artifact(project_id, "data_schema_spec.md", schema)
    await publish(channel, {"type": "step_done", "step": "schema", "status": "reviewing"})
    return schema


async def generate_plan(project_id: str, schema: str) -> str:
    """Generate implementation_dataset.md in one direct DeepSeek call."""
    channel = f"project:{project_id}"
    await publish(channel, {"type": "step_progress", "step": "plan", "status": "running", "message": "Generating plan (DeepSeek)..."})

    schema_md = file_service.read_artifact(project_id, "data_schema_spec.md") or schema
    profile = file_service.read_artifact(project_id, "data_profile.md")
    has_data = _has_source_data(project_id)

    parts = [
        _read_command("generate-plan"),
        f"\n\n---\n\n## data_schema_spec.md\n\n{schema_md}",
        f"\n\n## Strategy templates (tools/templates/)\n\n{_read_strategy_templates()}",
    ]
    if profile:
        parts.append(f"\n\n## data_profile.md\n\n{profile}")
    parts.append(
        "\n\n## Source data present in data/: "
        + ("YES — you MUST use the data_driven strategy." if has_data else "no.")
    )

    plan = _clean(await _stream("\n".join(parts), channel, "plan"))
    if not plan:
        raise RuntimeError("plan generation returned empty output")

    file_service.write_artifact(project_id, "implementation_dataset.md", plan)
    await publish(channel, {"type": "step_done", "step": "plan", "status": "reviewing"})
    return plan
