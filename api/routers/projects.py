from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from api.db import get_db
from api.models.project import Project, Artifact, PipelineStep
from api.services import file_service, opencode_service, runner_service, jobs_service, llm_service, profile_service
from api.services.sse import subscribe
from fastapi.responses import StreamingResponse, FileResponse
import asyncio

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str


class UpdateArtifactRequest(BaseModel):
    content: str


class EditArtifactRequest(BaseModel):
    message: str


@router.get("")
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return [_project_dict(p) for p in projects]


@router.post("", status_code=201)
async def create_project(req: CreateProjectRequest, db: AsyncSession = Depends(get_db)):
    project = Project(name=req.name, description=req.description, status="pending")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    file_service.ensure_project_dir(project.id)
    file_service.write_artifact(project.id, "dataset_description.md", req.description)
    runner_service.ensure_default_config(project.id)
    file_service.link_templates(project.id)

    return _project_dict(project)


@router.post("/{project_id}/data", status_code=201)
async def upload_data(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a real source file (CSV) for the data_driven flow. It's saved to
    the project's data/ dir, and a note is appended to the description so the
    pipeline profiles it and matches its structure/distributions."""
    await _get_or_404(project_id, db)
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    rel_path = file_service.save_data_file(project_id, file.filename, content)

    # Deterministic statistical profile (best-effort) — grounds schema/plan/implement.
    try:
        profile_rel = profile_service.profile_project_file(project_id, rel_path)
    except Exception:
        profile_rel = None  # profiling is best-effort; the CSV is still usable

    # Steer the pipeline into the data_driven strategy.
    current = file_service.read_artifact(project_id, "dataset_description.md") or ""
    if "## Source data" not in current:
        profile_line = (
            f" A precomputed statistical profile is in `{profile_rel}` — read it for "
            f"the real dtypes, distributions, and correlations."
            if profile_rel else ""
        )
        note = (
            f"\n\n## Source data\n"
            f"A real source file exists at `{rel_path}`. Base the schema on its "
            f"actual columns and dtypes, and generate synthetic data that "
            f"statistically matches its structure and distributions (use the "
            f"data_driven strategy).{profile_line}\n"
        )
        file_service.write_artifact(project_id, "dataset_description.md", current + note)

    return {"status": "uploaded", "path": rel_path, "size": len(content), "profile": profile_rel}


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await _get_or_404(project_id, db)
    artifacts = await db.execute(select(Artifact).where(Artifact.project_id == project_id))
    steps = await db.execute(select(PipelineStep).where(PipelineStep.project_id == project_id).order_by(PipelineStep.started_at))

    schema_content = file_service.read_artifact(project_id, "data_schema_spec.md")
    plan_content = file_service.read_artifact(project_id, "implementation_dataset.md")

    return {
        **_project_dict(project),
        "artifacts": [{"id": a.id, "type": a.type, "path": a.path} for a in artifacts.scalars().all()],
        "pipeline_steps": [_step_dict(s) for s in steps.scalars().all()],
        "schema_content": schema_content,
        "plan_content": plan_content,
    }


@router.post("/{project_id}/pipeline/start")
async def start_pipeline(project_id: str, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    project = await _get_or_404(project_id, db)
    project.status = "schema_running"
    await db.commit()

    description = file_service.read_artifact(project_id, "dataset_description.md") or project.description
    bg.add_task(_run_schema_step, project_id, description, db)
    return {"status": "started"}


async def _run_schema_step(project_id: str, description: str, db: AsyncSession):
    from api.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        step = PipelineStep(project_id=project_id, step="schema", status="running")
        session.add(step)
        await session.commit()

        try:
            schema = await opencode_service.generate_schema(project_id, description)
            step.status = "done"
            step.output = schema[:500]

            artifact = Artifact(project_id=project_id, type="schema", path=f"{project_id}/data_schema_spec.md")
            session.add(artifact)

            result = await session.execute(select(Project).where(Project.id == project_id))
            proj = result.scalar_one()
            proj.status = "schema_review"
            await session.commit()
        except Exception as e:
            step.status = "error"
            step.output = str(e)
            result = await session.execute(select(Project).where(Project.id == project_id))
            proj = result.scalar_one()
            proj.status = "error"
            await session.commit()


@router.get("/{project_id}/schema")
async def get_schema(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_or_404(project_id, db)
    content = file_service.read_artifact(project_id, "data_schema_spec.md")
    return {"content": content}


@router.patch("/{project_id}/schema")
async def update_schema(project_id: str, req: UpdateArtifactRequest, db: AsyncSession = Depends(get_db)):
    await _get_or_404(project_id, db)
    file_service.write_artifact(project_id, "data_schema_spec.md", req.content)
    return {"status": "saved"}


@router.post("/{project_id}/schema/edit", status_code=202)
async def edit_schema(project_id: str, req: EditArtifactRequest, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await _get_or_404(project_id, db)
    job_id = jobs_service.create_job()
    bg.add_task(_run_edit_job, job_id, project_id, "schema", req.message)
    return {"job_id": job_id}


@router.patch("/{project_id}/schema/approve")
async def approve_schema(project_id: str, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    project = await _get_or_404(project_id, db)
    project.status = "plan_running"
    await db.commit()

    schema = file_service.read_artifact(project_id, "data_schema_spec.md") or ""
    bg.add_task(_run_plan_step, project_id, schema)
    return {"status": "approved"}


async def _run_plan_step(project_id: str, schema: str):
    from api.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        step = PipelineStep(project_id=project_id, step="plan", status="running")
        session.add(step)
        await session.commit()

        try:
            plan = await opencode_service.generate_plan(project_id, schema)
            step.status = "done"

            artifact = Artifact(project_id=project_id, type="plan", path=f"{project_id}/implementation_dataset.md")
            session.add(artifact)

            result = await session.execute(select(Project).where(Project.id == project_id))
            proj = result.scalar_one()
            proj.status = "plan_review"
            await session.commit()
        except Exception as e:
            step.status = "error"
            step.output = str(e)
            result = await session.execute(select(Project).where(Project.id == project_id))
            proj = result.scalar_one()
            proj.status = "error"
            await session.commit()


@router.get("/{project_id}/plan")
async def get_plan(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_or_404(project_id, db)
    content = file_service.read_artifact(project_id, "implementation_dataset.md")
    return {"content": content}


@router.patch("/{project_id}/plan")
async def update_plan(project_id: str, req: UpdateArtifactRequest, db: AsyncSession = Depends(get_db)):
    await _get_or_404(project_id, db)
    file_service.write_artifact(project_id, "implementation_dataset.md", req.content)
    return {"status": "saved"}


@router.post("/{project_id}/plan/edit", status_code=202)
async def edit_plan(project_id: str, req: EditArtifactRequest, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await _get_or_404(project_id, db)
    job_id = jobs_service.create_job()
    bg.add_task(_run_edit_job, job_id, project_id, "plan", req.message)
    return {"job_id": job_id}


async def _run_edit_job(job_id: str, project_id: str, artifact_type: str, message: str):
    try:
        result = await llm_service.edit_artifact(project_id, artifact_type, message)
        jobs_service.set_result(job_id, result)
    except Exception as e:
        jobs_service.set_error(job_id, str(e))


@router.patch("/{project_id}/plan/approve")
async def approve_plan(project_id: str, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    project = await _get_or_404(project_id, db)
    project.status = "coding_running"
    await db.commit()

    bg.add_task(_run_coding_step, project_id)
    return {"status": "approved"}


async def _run_coding_step(project_id: str):
    from api.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        step = PipelineStep(project_id=project_id, step="coding", status="running")
        session.add(step)
        await session.commit()

        try:
            result_data = await opencode_service.run_coding_agent(project_id)
            step.status = "done" if result_data["success"] else "error"
            step.output = result_data.get("output", "")[:500]

            res = await session.execute(select(Project).where(Project.id == project_id))
            proj = res.scalar_one()
            proj.status = "ready" if result_data["success"] else "error"
            await session.commit()
        except Exception as e:
            step.status = "error"
            step.output = str(e)
            res = await session.execute(select(Project).where(Project.id == project_id))
            proj = res.scalar_one()
            proj.status = "error"
            await session.commit()


@router.get("/{project_id}/config")
async def get_config(project_id: str, db: AsyncSession = Depends(get_db)):
    await _get_or_404(project_id, db)
    content, path = runner_service.read_default_config(project_id)
    if content is None:
        raise HTTPException(status_code=404, detail="No generation config found for this project")
    return {"content": content, "path": path}


@router.patch("/{project_id}/config")
async def update_config(project_id: str, req: UpdateArtifactRequest, db: AsyncSession = Depends(get_db)):
    await _get_or_404(project_id, db)
    path = runner_service.write_default_config(project_id, req.content)
    if path is None:
        raise HTTPException(status_code=404, detail="Generator not found — run the pipeline first")
    return {"status": "saved", "path": path}


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await _get_or_404(project_id, db)
    await db.delete(project)
    await db.commit()
    file_service.delete_project_dir(project_id)
    return None


@router.get("/{project_id}/download")
async def download_project(project_id: str):
    await _get_project_or_404(project_id)
    zip_path = file_service.zip_project(project_id)
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=404, detail="Project files not found")
    return FileResponse(str(zip_path), filename=f"project_{project_id}.zip", media_type="application/zip")


@router.get("/{project_id}/events")
async def project_events(project_id: str):
    await _get_project_or_404(project_id)

    async def event_stream():
        async for event in subscribe(f"project:{project_id}"):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def _get_project_or_404(project_id: str):
    from api.db import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project


async def _get_or_404(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _project_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "status": p.status,
        "strategy": p.strategy,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _step_dict(s: PipelineStep) -> dict:
    return {
        "id": s.id,
        "step": s.step,
        "status": s.status,
        "output": s.output,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }
