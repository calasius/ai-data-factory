import uuid
import yaml as yaml_lib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from api.db import get_db
from api.models.project import Project, GenerationRun
from api.services import file_service, runner_service
from api.services.sse import subscribe


def _extract_num_records(config_yaml: str | None, fallback: int) -> int:
    if not config_yaml:
        return fallback
    try:
        parsed = yaml_lib.safe_load(config_yaml) or {}
    except yaml_lib.YAMLError:
        return fallback
    for key in ("general", "generation"):
        section = parsed.get(key)
        if isinstance(section, dict) and "num_records" in section:
            val = section["num_records"]
            if isinstance(val, int):
                return val
    return fallback

router = APIRouter(prefix="/projects/{project_id}/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    num_records: int = 1000
    seed: int = 42
    strategy: str = "rules"
    output_format: str = "csv"
    config_yaml: str | None = None
    save_as_default: bool = False


@router.get("")
async def list_runs(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GenerationRun).where(GenerationRun.project_id == project_id).order_by(GenerationRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [_run_dict(r) for r in runs]


@router.post("", status_code=201)
async def create_run(project_id: str, req: CreateRunRequest, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if req.save_as_default and req.config_yaml:
        if runner_service.write_default_config(project_id, req.config_yaml) is None:
            raise HTTPException(status_code=404, detail="Generator not found — cannot save as default")

    run_id = str(uuid.uuid4())
    num_records = _extract_num_records(req.config_yaml, req.num_records)
    run_config_snapshot: dict = {"general": {"num_records": num_records, "seed": req.seed}, "output": {"format": req.output_format}}
    if req.config_yaml:
        run_config_snapshot["custom_yaml"] = True

    run = GenerationRun(
        id=run_id,
        project_id=project_id,
        num_records=num_records,
        status="running",
        run_config=run_config_snapshot,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()

    bg.add_task(_execute_run, project_id, run_id, req.dict())
    return _run_dict(run)


async def _execute_run(project_id: str, run_id: str, config: dict):
    from api.db import AsyncSessionLocal
    from datetime import datetime

    start = datetime.utcnow()
    # When the user supplies a raw YAML, honor it as-is — don't layer legacy field
    # overrides on top. Those fields are defaults for the short-form request shape only.
    if config.get("config_yaml"):
        overrides: dict = {}
    else:
        overrides = {
            "general": {"num_records": config["num_records"], "seed": config["seed"]},
            "output": {"format": config["output_format"]},
        }
    result_data = await runner_service.run_generator(
        project_id,
        run_id,
        overrides,
        config_yaml=config.get("config_yaml"),
    )

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(GenerationRun).where(GenerationRun.id == run_id))
        run = res.scalar_one()
        run.completed_at = datetime.utcnow()
        run.duration_seconds = (run.completed_at - start).total_seconds()
        run.status = "success" if result_data.get("success") else "failed"
        run.validation_result = result_data.get("validation")
        run.output_path = f"{project_id}/output/{run_id}"
        await session.commit()


@router.get("/{run_id}")
async def get_run(project_id: str, run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GenerationRun).where(GenerationRun.id == run_id, GenerationRun.project_id == project_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_dict(run)


@router.get("/{run_id}/events")
async def run_events(project_id: str, run_id: str):
    async def event_stream():
        async for event in subscribe(f"run:{run_id}"):
            yield event
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{run_id}/download")
async def download_run(project_id: str, run_id: str):
    zip_path = file_service.zip_run_output(project_id, run_id)
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=404, detail="Output not found")
    return FileResponse(str(zip_path), filename=f"output_{run_id}.zip", media_type="application/zip")


def _run_dict(r: GenerationRun) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "num_records": r.num_records,
        "status": r.status,
        "run_config": r.run_config,
        "validation_result": r.validation_result,
        "duration_seconds": r.duration_seconds,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
