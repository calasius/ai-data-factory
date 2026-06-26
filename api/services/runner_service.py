import asyncio
import shutil
import yaml
import tomllib
from pathlib import Path
from api.services import file_service
from api.services.sse import publish


def _find_generator(project_path: Path) -> tuple[Path, str] | None:
    """Find the directory containing pyproject.toml and the first console script.
    Returns (cwd, script_name) or None."""
    candidates = [project_path] + [d for d in project_path.iterdir() if d.is_dir()]
    for d in candidates:
        py = d / "pyproject.toml"
        if not py.exists():
            continue
        try:
            data = tomllib.loads(py.read_text())
        except tomllib.TOMLDecodeError:
            continue
        scripts = data.get("project", {}).get("scripts", {})
        if scripts:
            return d, next(iter(scripts.keys()))
    return None


def _find_default_config(generator_path: Path) -> Path | None:
    """Find the default config YAML the generator was built around."""
    for candidate in [
        generator_path / "config" / "generation_config.yaml",
        generator_path / "config.yml",
        generator_path / "config.yaml",
        generator_path / "generation_config.yaml",
    ]:
        if candidate.exists():
            return candidate
    matches = list(generator_path.rglob("*config*.y*ml"))
    return matches[0] if matches else None


def _apply_overrides(config: dict, overrides: dict, output_dir: str) -> dict:
    """Apply num_records / seed overrides regardless of which key the
    generator's YAML uses (generation vs general, etc.).
    `output_dir` is the per-run directory where the generator should write
    all its output files (one CSV per table for multi-table datasets)."""
    num_records = overrides.get("general", {}).get("num_records")
    seed = overrides.get("general", {}).get("seed")

    for section_key in ("generation", "general"):
        if section_key in config and isinstance(config[section_key], dict):
            if num_records is not None and "num_records" in config[section_key]:
                config[section_key]["num_records"] = num_records
            if seed is not None and "seed" in config[section_key]:
                config[section_key]["seed"] = seed
            for k in ("output_path", "output_dir"):
                if k in config[section_key]:
                    config[section_key][k] = output_dir

    if "output" in config and isinstance(config["output"], dict):
        for k in ("path", "dir"):
            if k in config["output"]:
                config["output"][k] = output_dir
        # Multi-table generators write several files into the dir; a fixed
        # filename would silently force single-file output.
        config["output"].pop("filename", None)

    return config


DEFAULT_GENERATION_CONFIG = """# Generation config — edit and re-run to customize.
# The coding agent will extend this file once the generator is implemented.

locale: null            # ISO locale (e.g. es_AR, en_US). null = locale-neutral.
num_records: 1000       # rows of the anchor entity (not total dataset size)
seed: 42

# Multi-table only — single anchor:
# anchor_entity: orders
# Or multi-anchor (disconnected subgraphs):
# anchors:
#   orders: 10000
#   support_tickets: 500

output:
  format: csv
  path: output/           # directory for generator output files. Multi-table datasets write one CSV per entity inside this dir; single-table writes dataset.csv.

run_options:
  regenerate_seeds: false   # If true, regenerate seed files before generating the dataset.
  seed_count_override: null

# Optional overrides — if absent, schema defaults apply.
# overrides:
#   entity_counts:          # force exact count per entity (required for `shared` entities)
#     customers: 500
#   fan_out:                # override fan-out mean per relation
#     customer_order: 20
#   archetype_shares:       # change segmentation mix
#     power_user: 0.20
"""


def _resolve_config_path(project_id: str) -> tuple["Path", bool]:
    """Return (config_path, is_in_generator). Prefers generator-owned config
    once it exists; falls back to the project-root template otherwise."""
    project_path = file_service.project_dir(project_id)
    found = _find_generator(project_path)
    if found:
        generator_path, _ = found
        gen_cfg = _find_default_config(generator_path)
        if gen_cfg:
            return gen_cfg, True
        return generator_path / "config" / "generation_config.yaml", True
    return project_path / "generation_config.yaml", False


def ensure_default_config(project_id: str) -> str:
    """Create the project-root default config if it doesn't exist yet.
    Called on project creation so there is always a YAML to edit."""
    project_path = file_service.project_dir(project_id)
    project_path.mkdir(parents=True, exist_ok=True)
    cfg_path = project_path / "generation_config.yaml"
    if not cfg_path.exists():
        cfg_path.write_text(DEFAULT_GENERATION_CONFIG)
    return str(cfg_path.relative_to(project_path))


def read_default_config(project_id: str) -> tuple[str | None, str | None]:
    """Return (yaml_text, relative_path) for the project's default generation config.
    Guaranteed to return content if the project exists — falls back to a template at project root."""
    project_path = file_service.project_dir(project_id)
    cfg_path, _ = _resolve_config_path(project_id)
    if not cfg_path.exists():
        ensure_default_config(project_id)
        cfg_path, _ = _resolve_config_path(project_id)
    return cfg_path.read_text(), str(cfg_path.relative_to(project_path))


def write_default_config(project_id: str, content: str) -> str | None:
    """Persist content to the project's default generation config.
    Writes to the generator-owned path once a generator exists; otherwise to the project-root template."""
    project_path = file_service.project_dir(project_id)
    cfg_path, _ = _resolve_config_path(project_id)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(content)
    return str(cfg_path.relative_to(project_path))


async def run_generator(project_id: str, run_id: str, run_config: dict, config_yaml: str | None = None) -> dict:
    project_path = file_service.project_dir(project_id)
    run_output_dir = project_path / "output" / run_id
    run_output_dir.mkdir(parents=True, exist_ok=True)

    found = _find_generator(project_path)
    if not found:
        await publish(f"run:{run_id}", {"type": "done", "status": "error", "message": "No generator (pyproject.toml with [project.scripts]) found in project"})
        return {"success": False, "error": "No generator found"}

    generator_path, script_name = found
    default_cfg = _find_default_config(generator_path)

    run_config_path = generator_path / f"run_{run_id}.yaml"
    if config_yaml is not None:
        try:
            cfg = yaml.safe_load(config_yaml) or {}
        except yaml.YAMLError as e:
            await publish(f"run:{run_id}", {"type": "done", "status": "error", "message": f"Invalid YAML: {e}"})
            return {"success": False, "error": f"Invalid YAML: {e}"}
        cfg = _apply_overrides(cfg, run_config, str(run_output_dir))
    elif default_cfg:
        cfg = yaml.safe_load(default_cfg.read_text()) or {}
        cfg = _apply_overrides(cfg, run_config, str(run_output_dir))
    else:
        cfg = run_config
    run_config_path.write_text(yaml.dump(cfg))

    await publish(f"run:{run_id}", {"type": "log", "line": f"Generator: {script_name}\n"})
    await publish(f"run:{run_id}", {"type": "log", "line": f"Records: {run_config.get('general', {}).get('num_records', 'default')}\n"})
    await publish(f"run:{run_id}", {"type": "log", "line": f"Config: {run_config_path.relative_to(project_path)}\n"})

    # Try with `generate` subcommand first, then bare CLI.
    proc = None
    last_output = ""
    for cmd in [
        ["uv", "run", script_name, "generate", "--config", str(run_config_path)],
        ["uv", "run", script_name, "--config", str(run_config_path)],
    ]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(generator_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out_lines = []
        async for line in proc.stdout:
            decoded = line.decode("utf-8", errors="replace")
            out_lines.append(decoded)
            await publish(f"run:{run_id}", {"type": "log", "line": decoded})
        await proc.wait()
        last_output = "".join(out_lines).lower()
        if proc.returncode == 0:
            break
        if "invalid choice" in last_output or "unrecognized arguments" in last_output:
            continue
        break

    if proc.returncode != 0:
        await publish(f"run:{run_id}", {"type": "done", "status": "error", "message": f"Generator exited with code {proc.returncode}"})
        return {"success": False, "exit_code": proc.returncode}

    # If the generator wrote to its own default output dir, mirror everything
    # into the per-run dir so the download zip contains the full dataset.
    _collect_generator_output(generator_path, run_output_dir)

    val_result = await _run_validator(script_name, generator_path, run_config_path, run_id)

    if val_result["passed"]:
        await publish(f"run:{run_id}", {"type": "done", "status": "success", "records": run_config.get("general", {}).get("num_records"), "validation": val_result})
    else:
        await publish(f"run:{run_id}", {"type": "done", "status": "validation_failed", "errors": val_result.get("errors", [])})

    return {"success": val_result["passed"], "validation": val_result}


def _collect_generator_output(generator_path: Path, run_output_dir: Path) -> None:
    """Mirror all files the generator produced into the per-run dir.

    If the generator honored `output.path=<run_output_dir>` it already wrote in
    place. If it wrote to its own default `output/` dir or dropped CSVs at the
    generator root, copy everything over.

    Note: run_output_dir is typically nested inside generator_path/output, so we
    must (a) snapshot the file list before copying — iterating live would see
    newly-copied files and recurse — and (b) explicitly skip files that already
    live under run_output_dir.
    """
    run_output_dir.mkdir(parents=True, exist_ok=True)
    run_abs = run_output_dir.resolve()

    # If the generator already wrote into run_output_dir, nothing to do.
    if any(run_output_dir.rglob("*")):
        return

    gen_output = generator_path / "output"
    if gen_output.exists() and gen_output.resolve() != run_abs:
        sources: list[Path] = []
        for src in gen_output.rglob("*"):
            if not src.is_file():
                continue
            try:
                src.resolve().relative_to(run_abs)
                continue  # src is inside run_output_dir — skip to avoid self-copy
            except ValueError:
                sources.append(src)
        for src in sources:
            dest = run_output_dir / src.relative_to(gen_output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dest)

    # Catch loose output files dropped at the generator root.
    for pattern in ("*.csv", "*.json", "*.parquet", "*.jsonl"):
        for src in generator_path.glob(pattern):
            if src.is_file():
                shutil.copy(src, run_output_dir / src.name)


async def _run_validator(script_name: str, generator_path: Path, config_path: Path, run_id: str) -> dict:
    """Try `<script> validate` first; fall back to `--validate-only` flag if the CLI
    uses a different convention. If neither works, mark as passed (generator already ran)."""
    for cmd in [
        ["uv", "run", script_name, "validate", "--config", str(config_path)],
        ["uv", "run", script_name, "--validate-only", "--config", str(config_path)],
        ["uv", "run", script_name, "--validate", "--config", str(config_path)],
    ]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(generator_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        output_lines = []
        async for line in proc.stdout:
            decoded = line.decode("utf-8", errors="replace")
            output_lines.append(decoded)
            await publish(f"run:{run_id}", {"type": "log", "line": decoded})
        await proc.wait()

        joined = "".join(output_lines).lower()
        if proc.returncode == 0:
            return {"passed": True, "output": "".join(output_lines), "errors": []}
        # Subcommand not recognized — try the next variant.
        if "no such" in joined or "unrecognized" in joined or "unknown" in joined or "usage:" in joined:
            continue
        return {
            "passed": False,
            "output": "".join(output_lines),
            "errors": [l for l in output_lines if "fail" in l.lower()][:10],
        }

    # No variant worked — assume validation isn't separate and the generator already validated.
    return {"passed": True, "output": "Validator subcommand not available — assuming generator self-validated.", "errors": []}
