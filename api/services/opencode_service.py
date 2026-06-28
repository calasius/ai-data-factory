"""opencode + DeepSeek coding agent — runs the implement step only.

Schema and plan are single-shot DeepSeek calls (see llm_service) — much faster
than an agent loop. Only the coding step needs a real agent: it writes many
files and runs uv/pytest. opencode runs IN this container (binary baked into the
image); its filesystem tools operate in the directory the server was started in,
so we spin up a short-lived `opencode serve` rooted at the project directory,
drive one agentic turn with DeepSeek, and tear it down.

The implement template lives in `.claude/commands/implement.md`; its body is the
prompt. The agent resolves relative paths against the server root (= project
dir), where file_service.link_templates symlinks `.claude` and `tools`.
"""

import asyncio
import os
import re
from pathlib import Path

from api.config import settings
from api.services import file_service
from api.services.sse import publish

try:  # SDK is a prerelease; fail loudly only when actually invoked.
    from opencode_ai import AsyncOpencode
except ImportError:  # pragma: no cover
    AsyncOpencode = None


# Coding step needs the full toolkit: read specs, write/edit files, run uv/pytest.
# (Schema/plan are single-shot DeepSeek calls in llm_service — they don't use opencode.)
_CODING_TOOLS = {
    "read": True, "write": True, "edit": True, "bash": True, "grep": True,
    "glob": True, "list": True, "patch": True, "webfetch": True,
    "todowrite": True, "todoread": True,
}

_LISTEN_RE = re.compile(r"listening on (http://\S+)")
_SERVER_START_TIMEOUT = 30      # seconds to wait for the "listening on" line
_CODING_TIMEOUT = 1800.0        # 30 min — the coding step writes and runs code


def _server_env() -> dict:
    """Environment for the server: discoverable binary, app-owned config
    (DeepSeek provider), and the API key."""
    env = {**os.environ}
    env["PATH"] = f"{Path.home()}/.opencode/bin:" + env.get("PATH", "")
    env["OPENCODE_CONFIG"] = settings.opencode_config_path
    env["DEEPSEEK_API_KEY"] = settings.deepseek_api_key
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "1"
    return env


def _read_template(name: str) -> str:
    """Load a command template body (e.g. 'generate-schema') from commands_dir."""
    return (Path(settings.commands_dir) / f"{name}.md").read_text(encoding="utf-8")


async def _start_server(cwd: Path) -> tuple[asyncio.subprocess.Process, str]:
    """Spawn `opencode serve` rooted at cwd on an ephemeral port. Tools execute
    in cwd, so this is what gives per-project isolation. Returns (proc, base_url)."""
    proc = await asyncio.create_subprocess_exec(
        "opencode", "serve", "--hostname", "127.0.0.1", "--port", "0",
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=_server_env(),
    )
    try:
        async with asyncio.timeout(_SERVER_START_TIMEOUT):
            while True:
                line = await proc.stdout.readline()
                if not line:
                    raise RuntimeError("opencode serve exited before it started listening")
                match = _LISTEN_RE.search(line.decode("utf-8", "replace"))
                if match:
                    asyncio.create_task(_devnull_drain(proc))  # keep the pipe drained
                    return proc, match.group(1).rstrip("/")
    except BaseException:
        await _stop_server(proc)
        raise


async def _devnull_drain(proc: asyncio.subprocess.Process) -> None:
    try:
        while await proc.stdout.readline():
            pass
    except Exception:
        pass


async def _stop_server(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        proc.kill()


async def _collect_text(client, session_id: str) -> str:
    """Best-effort: pull assistant text parts from the session transcript.
    The chat() return (AssistantMessage) carries metadata, not the text parts.
    Cosmetic — the real outputs are the files the agent wrote to disk."""
    try:
        messages = await client.session.messages(session_id)
    except Exception:
        return ""
    out: list[str] = []
    for m in messages or []:
        # Only the assistant's text — never the user message (which is the prompt
        # template itself). Handle both response shapes: {info, parts} or flat.
        info = getattr(m, "info", m)
        if getattr(info, "role", None) != "assistant":
            continue
        parts = getattr(m, "parts", None) or getattr(info, "parts", None) or []
        for p in parts:
            if getattr(p, "type", None) == "text":
                out.append(getattr(p, "text", "") or "")
    return "".join(out)


async def _run_opencode_command(
    template_name: str,
    cwd: Path,
    tools: dict[str, bool],
    channel: str | None = None,
    step: str | None = None,
    model: str | None = None,
    timeout: float = _CODING_TIMEOUT,
) -> str:
    """Run a command template as one opencode turn (DeepSeek) in an isolated
    server rooted at `cwd`. Blocks until the turn (including all tool calls)
    completes; returns the assistant text. Raises on turn error."""
    if AsyncOpencode is None:
        raise RuntimeError("opencode-ai SDK not installed — run `uv add --prerelease=allow opencode-ai`")

    prompt = _read_template(template_name)
    proc, base_url = await _start_server(cwd)
    try:
        client = AsyncOpencode(base_url=base_url, timeout=timeout)
        session = await client.session.create(extra_body={})
        result = await client.session.chat(
            session.id,
            provider_id="deepseek",
            model_id=model or settings.deepseek_model,
            parts=[{"type": "text", "text": prompt}],
            tools=tools,
        )
        error = getattr(result, "error", None)
        if error is not None:
            raise RuntimeError(f"opencode turn failed: {error}")
        return await _collect_text(client, session.id)
    finally:
        await _stop_server(proc)


async def run_coding_agent(project_id: str) -> dict:
    """Run the implement step with the full toolkit. Builds the generator."""
    channel = f"project:{project_id}"
    project_path = file_service.project_dir(project_id)
    await publish(channel, {"type": "step_progress", "step": "coding", "status": "running", "message": "opencode + DeepSeek implementing generator..."})

    try:
        output = await _run_opencode_command("implement", project_path, _CODING_TOOLS, channel, "coding")
        success = True
    except Exception as e:
        output = str(e)
        success = False

    await publish(channel, {
        "type": "step_done",
        "step": "coding",
        "status": "done" if success else "error",
        "exit_code": 0 if success else 1,
    })

    return {"success": success, "output": output, "exit_code": 0 if success else 1}
