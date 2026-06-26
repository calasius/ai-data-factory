import os
import shutil
import hashlib
import zipfile
from pathlib import Path
from api.config import settings


def project_dir(project_id: str) -> Path:
    return Path(settings.projects_dir) / project_id


def ensure_project_dir(project_id: str) -> Path:
    d = project_dir(project_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "output").mkdir(exist_ok=True)
    (d / "logs").mkdir(exist_ok=True)
    return d


def write_artifact(project_id: str, filename: str, content: str) -> str:
    d = ensure_project_dir(project_id)
    path = d / filename
    path.write_text(content, encoding="utf-8")
    return str(path)


def read_artifact(project_id: str, filename: str) -> str | None:
    path = project_dir(project_id) / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def artifact_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def delete_project_dir(project_id: str) -> bool:
    d = project_dir(project_id)
    if not d.exists():
        return False
    shutil.rmtree(d)
    return True


def link_templates(project_id: str) -> None:
    """Symlink .claude/ and tools/ into the project dir so that opencode
    running with cwd=project_dir can resolve command templates and strategy
    templates as if they were project-local."""
    d = ensure_project_dir(project_id)
    for name, target in (
        (".claude", "/app/.claude"),
        ("tools", "/app/tools"),
    ):
        link = d / name
        if link.is_symlink() or link.exists():
            continue
        try:
            link.symlink_to(target)
        except OSError:
            pass


def zip_run_output(project_id: str, run_id: str) -> Path | None:
    run_dir = project_dir(project_id) / "output" / run_id
    if not run_dir.exists():
        return None
    zip_path = project_dir(project_id) / "output" / f"{run_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in run_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(run_dir))
    return zip_path


_PROJECT_ZIP_EXCLUDE_DIRS = {
    ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", ".mypy_cache", ".git",
}


def zip_project(project_id: str) -> Path | None:
    src = project_dir(project_id)
    if not src.exists():
        return None
    zip_path = src / f"{project_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(src)
            if rel == Path(zip_path.name):
                continue
            if any(part in _PROJECT_ZIP_EXCLUDE_DIRS for part in rel.parts):
                continue
            if rel.parts and rel.parts[0] == "output" and rel.suffix == ".zip":
                continue
            if rel.suffix in (".pyc", ".pyo"):
                continue
            zf.write(f, rel)
    return zip_path
