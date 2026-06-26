# Synthetic Data Generator Platform — Architecture

A web platform that lets users describe a dataset and automatically generates a fully functional synthetic data generator using opencode + DeepSeek as the AI backbone.

---

## System Overview

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph TB
    subgraph UI["🖥️ Frontend (Next.js)"]
        A[Dataset Description Form]
        B[Schema Review & Edit]
        C[Implementation Plan Review]
        D[Generation Progress]
        E[Download Output]
    end

    subgraph API["⚙️ API (FastAPI)"]
        F[Project Manager]
        G[Pipeline Orchestrator]
        H[File Manager]
        I[WebSocket Events]
    end

    subgraph AI["🤖 AI Layer (opencode + DeepSeek)"]
        J[Schema Agent]
        K[Planner Agent]
        L[Coding Agent]
    end

    subgraph Workers["🔧 Background Workers"]
        M[Generation Runner]
        N[Validation Runner]
    end

    subgraph Storage["💾 Storage"]
        O[(PostgreSQL\nProjects / Runs)]
        P[File System\nTemplates / Output]
    end

    A -->|POST /projects| F
    F --> G
    G -->|Step 1| J
    J -->|data_schema_spec.md| B
    B -->|Approve / Edit| G
    G -->|Step 2| K
    K -->|implementation_dataset.md| C
    C -->|Approve / Edit| G
    G -->|Step 3| L
    L -->|Generated code| M
    M -->|Run generator| N
    N -->|Validation result| D
    D --> E
    G <--> O
    H <--> P
    I -->|SSE / WS| D
```

---

## Three-Step Pipeline (Sequence)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif', 'actorBkg': '#D97757', 'actorBorder': '#b85e3a', 'actorTextColor': '#ffffff', 'actorLineColor': '#D97757', 'signalColor': '#D97757', 'signalTextColor': '#ffffff', 'labelBoxBkgColor': '#2D2D3E', 'labelBoxBorderColor': '#4A4A6A', 'labelTextColor': '#ffffff', 'loopTextColor': '#ffffff', 'noteBorderColor': '#7B5EA7', 'noteBkgColor': '#3D2D5E', 'noteTextColor': '#ffffff', 'activationBorderColor': '#D97757', 'activationBkgColor': '#3D2D2E'}}}%%
sequenceDiagram
    actor User
    participant UI
    participant API
    participant Agent
    participant FS as File System
    participant Runner

    User->>UI: Describe dataset
    UI->>API: POST /projects {description}
    API->>FS: Save dataset_description.md
    API-->>UI: {project_id, status: pending}

    Note over API,Agent: Step 1 — Schema Generation
    API->>Agent: generate_schema(description)
    Agent-->>API: data_schema_spec.md
    API->>FS: Save data_schema_spec.md
    API-->>UI: SSE: schema_ready
    UI->>User: Show schema for review
    User->>UI: Approve / Edit schema
    UI->>API: PATCH /projects/{id}/schema

    Note over API,Agent: Step 2 — Implementation Plan
    API->>Agent: generate_plan(schema, templates)
    Agent-->>API: implementation_dataset.md
    API->>FS: Save implementation_dataset.md
    API-->>UI: SSE: plan_ready
    UI->>User: Show plan + strategy selected
    User->>UI: Approve / Edit plan
    UI->>API: PATCH /projects/{id}/plan

    Note over API,Agent: Step 3 — Code Generation
    API->>Agent: implement(schema, plan)
    Agent-->>FS: Write generator code
    API-->>UI: SSE: coding_started
    Agent-->>API: implementation_complete
    API->>Runner: run_generator(project_id)
    Runner-->>API: generation_result
    API->>Runner: run_validator(project_id)
    Runner-->>API: validation_result
    API-->>UI: SSE: done {records, validation}
    UI->>User: Show results + download link
```

---

## Data Model

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif', 'attributeBackgroundColorEven': '#2D2D3E', 'attributeBackgroundColorOdd': '#3D3D50', 'attributeColor': '#ffffff'}}}%%
erDiagram
    PROJECT {
        uuid id PK
        string name
        string status
        string strategy
        timestamp created_at
        timestamp updated_at
    }

    ARTIFACT {
        uuid id PK
        uuid project_id FK
        string type
        string path
        string content_hash
        timestamp created_at
    }

    GENERATION_RUN {
        uuid id PK
        uuid project_id FK
        int num_records
        string status
        string output_path
        json validation_result
        float duration_seconds
        timestamp started_at
        timestamp completed_at
    }

    PIPELINE_STEP {
        uuid id PK
        uuid project_id FK
        string step
        string status
        text prompt_used
        text output
        int tokens_used
        timestamp started_at
        timestamp completed_at
    }

    PROJECT ||--o{ ARTIFACT : has
    PROJECT ||--o{ GENERATION_RUN : produces
    PROJECT ||--o{ PIPELINE_STEP : tracks
```

---

## Component Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph LR
    subgraph Frontend
        UI1[Dataset Form]
        UI2[Schema Editor\nMonaco Editor]
        UI3[Plan Viewer]
        UI4[Progress Dashboard]
        UI5[Output Explorer]
    end

    subgraph Backend
        subgraph FastAPI
            R1[POST /projects]
            R2[GET /projects/:id]
            R3[PATCH /projects/:id/schema]
            R4[PATCH /projects/:id/plan]
            R5[POST /projects/:id/generate]
            R6[GET /projects/:id/download]
            R7[GET /projects/:id/events SSE]
        end

        subgraph Services
            S1[ProjectService]
            S2[PipelineService]
            S3[OpencodeService]
            S4[RunnerService]
            S5[FileService]
        end

        subgraph AI_Agents["AI Agents"]
            AG1[SchemaAgent\ndeepseek-v4-pro]
            AG2[PlannerAgent\ndeepseek-v4-pro]
            AG3[CodingAgent\ndeepseek-v4-pro]
        end
    end

    subgraph Infrastructure
        DB[(PostgreSQL)]
        FS[File System\n/projects/:id/]
        Q[Task Queue\nCelery + Redis]
    end

    Frontend --> FastAPI
    FastAPI --> Services
    S2 --> AI_Agents
    S3 --> AG1 & AG2 & AG3
    AG3 -->|per-step opencode serve rooted at project dir| AG3
    Services --> DB
    Services --> FS
    S4 --> Q
```

---

## opencode Integration

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph TB
    subgraph OpencodeService["OpencodeService (opencode SDK)"]
        direction TB
        C1["schema_agent(description)\n→ stream response\n→ write data_schema_spec.md"]
        C2["planner_agent(schema, templates)\n→ stream response\n→ write implementation_dataset.md"]
        C3["coding_agent(schema, plan)\n→ per-step opencode serve\n→ implements generator"]
    end

    subgraph Prompts["Prompt Sources"]
        P1[.claude/commands/generate-schema.md]
        P2[.claude/commands/generate-plan.md]
        P3[.claude/commands/implement.md]
        T1[tools/templates/strategy_*.md]
    end

    subgraph Models["DeepSeek Models"]
        M1["deepseek-v4-pro\nSchema + Plan agents\n(structured output)"]
        M2["deepseek-v4-pro\nCoding agent\n(agentic, file writes)"]
    end

    P1 --> C1
    P2 --> C2
    P3 --> C3
    T1 --> C2
    C1 --> M1
    C2 --> M1
    C3 --> M2
```

---

## Project Folder Structure (per project)

```
/projects/{project_id}/
  dataset_description.md       ← user input
  data_schema_spec.md          ← Step 1 output (editable)
  implementation_dataset.md    ← Step 2 output (editable)
  {generator_name}/            ← Step 3 output (full generator code)
    config/
    src/
    tests/
    pyproject.toml
  output/
    {run_id}/
      dataset.csv
      validation_report.json
  logs/
    pipeline.log
    generation.log
```

---

## API Endpoints

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph LR
    subgraph Projects
        E1["POST /projects\nCreate project + upload description"]
        E2["GET /projects/:id\nGet project status + artifacts"]
        E3["GET /projects\nList all projects"]
    end

    subgraph Pipeline
        E4["POST /projects/:id/pipeline/start\nStart full pipeline"]
        E5["PATCH /projects/:id/schema\nUpdate schema spec"]
        E6["PATCH /projects/:id/plan\nUpdate implementation plan"]
        E7["POST /projects/:id/generate\nRun generator only"]
        E8["POST /projects/:id/validate\nRun validator only"]
    end

    subgraph Artifacts
        E9["GET /projects/:id/download\nDownload output zip"]
        E10["GET /projects/:id/events\nSSE stream for live progress"]
        E11["GET /projects/:id/logs\nGet pipeline logs"]
    end
```

---

## Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Frontend | Next.js + Tailwind | Fast UI, SSE support, Monaco editor for MD editing |
| API | FastAPI | Async, SSE, auto OpenAPI docs |
| AI | opencode + opencode Python SDK | DeepSeek deepseek-v4-pro for schema/plan/coding; deepseek-chat (OpenAI-compatible) for edits |
| Task queue | Celery + Redis | Async generator runs, progress tracking |
| Database | PostgreSQL | Project and run metadata |
| File storage | Local FS (or S3) | Generated code and output CSVs |
| Containerization | Docker Compose | API + worker + Redis + Postgres |
| Package manager | uv | Consistent with all generators |

---

## Deployment

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph TB
    subgraph DockerCompose["Docker Compose"]
        WEB["next.js\n:3000"]
        API["fastapi\n:8000"]
        WORKER["celery worker"]
        REDIS["redis\n:6379"]
        PG["postgres\n:5432"]
    end

    subgraph Volumes
        V1["/projects\n(generated code + output)"]
        V2["/templates\n(strategy templates)"]
        V3["/commands\n(.claude/commands)"]
    end

    WEB --> API
    API --> REDIS
    WORKER --> REDIS
    API --> PG
    WORKER --> PG
    API --> V1
    WORKER --> V1
    API -.->|read| V2
    API -.->|read| V3
```

---

## Dataset Generation from UI

Once the generator is built and tested, users can generate datasets on demand from the UI without touching code.

### Run Flow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif', 'actorBkg': '#D97757', 'actorBorder': '#b85e3a', 'actorTextColor': '#ffffff', 'actorLineColor': '#D97757', 'signalColor': '#D97757', 'signalTextColor': '#ffffff', 'labelBoxBkgColor': '#2D2D3E', 'labelBoxBorderColor': '#4A4A6A', 'labelTextColor': '#ffffff', 'loopTextColor': '#ffffff', 'noteBorderColor': '#7B5EA7', 'noteBkgColor': '#3D2D5E', 'noteTextColor': '#ffffff', 'activationBorderColor': '#D97757', 'activationBkgColor': '#3D2D2E'}}}%%
sequenceDiagram
    actor User
    participant UI
    participant API
    participant ConfigParser
    participant Runner
    participant FS as File System

    User->>UI: Open project (generator ready)
    UI->>API: GET /projects/:id/run-config
    API->>ConfigParser: Parse generation_config.yaml
    ConfigParser-->>API: config schema (fields + types + defaults)
    API-->>UI: RunConfigSchema

    UI->>User: Show dynamic generation form\n(num_records, seed, strategy, output_format)
    User->>UI: Fill form + click Generate
    UI->>API: POST /projects/:id/runs\n{num_records, seed, strategy, ...}

    API->>FS: Write run-specific config YAML
    API-->>UI: {run_id, status: running}

    API->>Runner: subprocess uv run generate-{name} generate\n--config run_{run_id}.yaml
    loop stdout streaming
        Runner-->>API: log line
        API-->>UI: SSE: {type: log, line: "..."}
    end
    Runner-->>API: exit code

    alt exit code 0
        API->>Runner: subprocess uv run generate-{name} validate\n--config run_{run_id}.yaml
        Runner-->>API: validation result JSON
        alt validation passed
            API-->>UI: SSE: {type: done, status: success, records: N, path: ...}
            UI->>User: ✅ Show results + Download button
        else validation failed
            API-->>UI: SSE: {type: done, status: validation_failed, errors: [...]}
            UI->>User: ❌ Show validation errors
        end
    else exit code != 0
        API-->>UI: SSE: {type: done, status: error, message: ...}
        UI->>User: ❌ Show error + logs
    end

    User->>UI: Click Download
    UI->>API: GET /projects/:id/runs/:run_id/download
    API->>FS: zip output/{run_id}/
    API-->>User: output_{run_id}.zip
```

---

### Dynamic Config Form

The UI generates the form automatically by reading `generation_config.yaml` from the project. No hardcoded fields — the form adapts to each generator.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph LR
    subgraph YAML["generation_config.yaml"]
        Y1["general:\n  seed: 42\n  num_records: 1000"]
        Y2["llm:\n  strategy: llm\n  batch_size: 10\n  model: deepseek-chat"]
        Y3["output:\n  filename: dataset_1k.csv\n  format: csv"]
    end

    subgraph ConfigParser["API: ConfigParser"]
        P1[Parse YAML schema]
        P2[Infer field types]
        P3[Extract defaults + ranges]
    end

    subgraph RunForm["UI: Dynamic Form"]
        F1["num_records — number input\ndefault: 1000, min: 1, max: 100000"]
        F2["seed — number input\ndefault: 42"]
        F3["strategy — select\noptions: llm | rules"]
        F4["model — select\noptions: deepseek-chat | deepseek-v4-pro"]
        F5["filename — text input\ndefault: dataset_1k.csv"]
    end

    Y1 --> P1
    Y2 --> P1
    Y3 --> P1
    P1 --> P2 --> P3
    P3 --> F1 & F2 & F3 & F4 & F5
```

---

### Run Management

Each generation run is stored independently. Users can trigger multiple runs with different configs and compare results.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph TB
    subgraph Project["Project: insurance_claims"]
        GEN["Generator code\n(built once)"]

        subgraph Runs["Generation Runs"]
            R1["Run 1\n1k records, seed=42, strategy=rules\n✅ PASSED"]
            R2["Run 2\n5k records, seed=42, strategy=llm\n✅ PASSED"]
            R3["Run 3\n10k records, seed=99, strategy=rules\n❌ FAILED validation"]
        end

        subgraph Outputs["Output Files"]
            O1["output/run_1/dataset.csv\n1 000 rows — ⬇ Download"]
            O2["output/run_2/dataset.csv\n5 000 rows — ⬇ Download"]
            O3["output/run_3/ — unavailable"]
        end
    end

    GEN --> R1 & R2 & R3
    R1 --> O1
    R2 --> O2
    R3 --> O3
```

---

### New API Endpoints for Generation

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph LR
    subgraph RunMgmt["Run Management"]
        RE1["GET /projects/:id/run-config\nReturns parsed config schema for dynamic form"]
        RE2["POST /projects/:id/runs\nStart a new generation run"]
        RE3["GET /projects/:id/runs\nList all runs with status + summary"]
        RE4["GET /projects/:id/runs/:run_id\nGet run details + validation result"]
        RE5["GET /projects/:id/runs/:run_id/events\nSSE stream: log lines + done event"]
        RE6["GET /projects/:id/runs/:run_id/download\nDownload output as zip"]
        RE7["GET /projects/:id/runs/:run_id/logs\nFull generation + validation logs"]
        RE8["DELETE /projects/:id/runs/:run_id\nDelete run output"]
    end
```

---

### UI Screens

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph LR
    subgraph Pages
        PG1["/ Projects list\n(name, status, last run)"]
        PG2["/projects/:id\nProject overview\n+ pipeline status"]
        PG3["/projects/:id/schema\nMonaco editor\nfor data_schema_spec.md"]
        PG4["/projects/:id/plan\nMonaco editor\nfor implementation_dataset.md"]
        PG5["/projects/:id/runs\nRun history\n+ new run form"]
        PG6["/projects/:id/runs/:run_id\nLive log stream\n+ validation result\n+ download"]
    end

    PG1 --> PG2
    PG2 --> PG3
    PG2 --> PG4
    PG2 --> PG5
    PG5 --> PG6
```

---

### Runner Implementation (API side)

The `RunnerService` executes the generator as a subprocess and streams stdout line-by-line to the SSE channel:

```python
async def run_generator(project_id: str, run_id: str, config: RunConfig):
    run_config_path = write_run_config(project_id, run_id, config)
    generator_path = get_generator_path(project_id)

    cmd = [
        "uv", "run", f"generate-{config.generator_name}",
        "generate", "--config", str(run_config_path),
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=generator_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async for line in process.stdout:
        await publish_event(run_id, {"type": "log", "line": line.decode()})

    await process.wait()
    return process.returncode
```

---

## Pipeline Step UI & AI-Assisted Editing

Each pipeline step produces an artifact that the user must review before the pipeline continues. Instead of editing markdown by hand, the user can chat with DeepSeek directly in the UI to request changes. DeepSeek edits the artifact, shows a diff, and waits for approval.

### Pipeline Step States

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
stateDiagram-v2
    [*] --> running : pipeline starts step
    running --> reviewing : Agent finishes artifact
    reviewing --> editing : user requests changes\n(manual or via DeepSeek chat)
    editing --> reviewing : DeepSeek applies edits\nshows diff
    reviewing --> approved : user clicks Approve
    reviewing --> rejected : user clicks Reject + reason
    rejected --> running : pipeline reruns step\nwith rejection context
    approved --> [*] : pipeline continues\nto next step
```

---

### AI-Assisted Editing Flow (Schema & Plan)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif', 'actorBkg': '#D97757', 'actorBorder': '#b85e3a', 'actorTextColor': '#ffffff', 'actorLineColor': '#D97757', 'signalColor': '#D97757', 'signalTextColor': '#ffffff', 'labelBoxBkgColor': '#2D2D3E', 'labelBoxBorderColor': '#4A4A6A', 'labelTextColor': '#ffffff', 'loopTextColor': '#ffffff', 'noteBorderColor': '#7B5EA7', 'noteBkgColor': '#3D2D5E', 'noteTextColor': '#ffffff', 'activationBorderColor': '#D97757', 'activationBkgColor': '#3D2D2E'}}}%%
sequenceDiagram
    actor User
    participant UI
    participant API
    participant LLM as llm_service
    participant FS as File System

    Note over UI: Step 1 done — schema shown in review panel
    UI->>User: Show data_schema_spec.md\n+ chat panel on the right

    User->>UI: "add an email field, make age range 25-65,\nchange fraud rate to 3-7%"
    UI->>API: POST /projects/:id/schema/edit\n{message, current_artifact}

    API->>LLM: edit_artifact(current_schema, user_message)
    Note over LLM: DeepSeek reads current schema\napplies requested changes\nreturns updated markdown + summary
    LLM-->>API: {updated_artifact, summary, changes[]}

    API->>FS: Save updated data_schema_spec.md
    API-->>UI: {diff, summary, changes[]}

    UI->>User: Show side-by-side diff\n+ change summary
    Note over UI: "Added: email (string, RFC5321)\nModified: age range 18→70 to 25→65\nModified: fraud_rate 3%-8% to 3%-7%"

    alt User approves
        User->>UI: Click Approve
        UI->>API: PATCH /projects/:id/schema/approve
        API-->>UI: SSE: step1_approved → starting step 2
    else User wants more changes
        User->>UI: "also add a phone field"
        Note over UI: loops back — DeepSeek edits again
    else User edits manually
        User->>UI: Edit in Monaco editor
        UI->>API: PATCH /projects/:id/schema\n{content}
        User->>UI: Click Approve
    end
```

---

### UI Layout — Review Panel

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph LR
    subgraph ReviewPanel["Review Panel — Step 1: Schema"]
        subgraph Left["Left — Artifact Viewer (60%)"]
            AV1["Monaco Editor\n(editable markdown)"]
            AV2["Diff View\n(before / after AI edit)"]
        end

        subgraph Right["Right — DeepSeek Chat (40%)"]
            CH1["Chat history\n(user ↔ DeepSeek)"]
            CH2["Change summary\nafter each edit"]
            CH3["Message input\n'add email field...'"]
        end

        subgraph Bottom["Bottom Bar"]
            BTN1["✅ Approve & Continue"]
            BTN2["🔄 Regenerate from scratch"]
            BTN3["✏️ Edit manually"]
        end
    end
```

---

### AI-Assisted Editing of Generator Code (Step 3)

After the coding agent implements the generator, the user can also chat with opencode to fix issues, add fields, or adjust logic — without leaving the UI.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif', 'actorBkg': '#D97757', 'actorBorder': '#b85e3a', 'actorTextColor': '#ffffff', 'actorLineColor': '#D97757', 'signalColor': '#D97757', 'signalTextColor': '#ffffff', 'labelBoxBkgColor': '#2D2D3E', 'labelBoxBorderColor': '#4A4A6A', 'labelTextColor': '#ffffff', 'loopTextColor': '#ffffff', 'noteBorderColor': '#7B5EA7', 'noteBkgColor': '#3D2D5E', 'noteTextColor': '#ffffff', 'activationBorderColor': '#D97757', 'activationBkgColor': '#3D2D2E'}}}%%
sequenceDiagram
    actor User
    participant UI
    participant API
    participant Opencode as opencode
    participant Runner

    Note over UI: Step 3 done — generator code ready
    UI->>User: Show file tree + code viewer\n+ chat panel

    User->>UI: "the fraud rate in the validator\nis too strict, loosen it to ±10%"
    UI->>API: POST /projects/:id/code/edit\n{message, file_hint: "validator.py"}

    API->>Opencode: per-step opencode serve, rooted at project dir\n"{message} Context: {schema} {plan}"
    Note over Opencode: opencode reads the codebase\nedits the relevant file(s)\nruns tests to verify
    Opencode-->>API: {files_changed[], test_result, summary}

    API-->>UI: {diff_per_file, test_result, summary}
    UI->>User: Show file diffs\n+ test result (pass/fail)

    alt tests pass
        User->>UI: Approve changes
        UI->>API: PATCH /projects/:id/code/approve
    else tests fail
        UI->>User: ❌ Show test failures
        User->>UI: "fix the test failures"
        Note over UI: loops back — opencode fixes
    end

    User->>UI: Click Run Generator
    UI->>API: POST /projects/:id/runs
    API->>Runner: uv run generate-{name} generate
```

---

### Edit API Endpoints

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph LR
    subgraph SchemaEdit["Schema Editing"]
        SE1["POST /projects/:id/schema/edit\nAI edit via chat message → returns diff"]
        SE2["PATCH /projects/:id/schema\nManual save from Monaco editor"]
        SE3["PATCH /projects/:id/schema/approve\nApprove + trigger Step 2"]
        SE4["POST /projects/:id/schema/regenerate\nRerun Step 1 with rejection context"]
    end

    subgraph PlanEdit["Plan Editing"]
        PE1["POST /projects/:id/plan/edit\nAI edit via chat message → returns diff"]
        PE2["PATCH /projects/:id/plan\nManual save from Monaco editor"]
        PE3["PATCH /projects/:id/plan/approve\nApprove + trigger Step 3"]
        PE4["POST /projects/:id/plan/regenerate\nRerun Step 2 with rejection context"]
    end

    subgraph CodeEdit["Code Editing"]
        CE1["POST /projects/:id/code/edit\nAI edit via chat → opencode edits files + runs tests"]
        CE2["GET /projects/:id/code/files\nList generator files"]
        CE3["GET /projects/:id/code/files/:path\nGet file content"]
        CE4["PATCH /projects/:id/code/approve\nMark code as approved"]
        CE5["POST /projects/:id/code/test\nRun pytest + return results"]
    end
```

---

### Edit Service — DeepSeek as Inline Editor

```python
# For schema and plan artifacts (markdown files)
async def edit_artifact(project_id: str, artifact_type: str, message: str) -> EditResult:
    current_content = read_artifact(project_id, artifact_type)

    # llm_service is an AsyncOpenAI client pointed at DeepSeek (api.deepseek.com, OpenAI-compatible)
    response = await llm_service.chat.completions.create(
        model="deepseek-chat",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": """You are an expert data engineer editing a synthetic dataset specification.
The user will ask you to modify the artifact. Apply the changes precisely.
Return the complete updated artifact followed by a JSON summary of changes made."""},
            {"role": "user", "content": f"Current artifact:\n\n{current_content}\n\nRequested changes: {message}"}
        ],
    )

    updated_content, changes = parse_edit_response(response.choices[0].message.content)
    diff = compute_diff(current_content, updated_content)

    save_artifact(project_id, artifact_type, updated_content)
    return EditResult(diff=diff, changes=changes, summary=summarize_changes(changes))


# For generator code — opencode runs with full autonomy via a per-step server
async def edit_code(project_id: str, message: str) -> CodeEditResult:
    generator_path = get_generator_path(project_id)

    # Spawn a short-lived `opencode serve` rooted at the project dir (filesystem isolation),
    # create a session, send the prompt, let the agent work with tools, then tear it down.
    # The agent has full control: reads files, writes files, runs tests, fixes errors.
    async with opencode_serve(cwd=generator_path) as server:
        client = AsyncOpencode(base_url=server.url)        # opencode Python SDK (opencode_ai)
        session = await client.session.create()
        result = await client.session.prompt(
            session_id=session.id,
            model="deepseek-v4-pro",
            text=f"{message}\nRun tests after editing: uv run pytest --tb=short. Fix any failures automatically.",
        )

    files_changed = detect_changed_files(generator_path)
    test_result = parse_test_output(result.output)

    return CodeEditResult(
        files_changed=files_changed,
        test_result=test_result,
        summary=extract_summary(result.output),
    )
```

---

## Control Model — Agent Autonomy vs User Checkpoints

opencode runs with **full autonomy** inside each pipeline step. The user never sees individual file edits, tool calls, or intermediate states. Control is returned to the user only at the three pipeline checkpoints.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph TB
    subgraph UserControl["👤 User has control"]
        U1["Describe dataset\n→ submit"]
        U2["Review schema\n→ chat edits or approve"]
        U3["Review plan\n→ chat edits or approve"]
        U4["Review result\n→ run generator or chat edit"]
    end

    subgraph AgentControl["🤖 Agent has full control (no interruptions)"]
        C1["Step 1: Generate schema\nReads description\nWrites data_schema_spec.md\nNo user prompts"]
        C2["Step 2: Generate plan\nReads schema + templates\nSelects strategy\nWrites implementation_dataset.md\nNo user prompts"]
        C3["Step 3: Implement generator\nWrites all files\nRuns uv sync\nRuns generator\nRuns tests\nFixes errors automatically\nNo user prompts"]
        C4["Edit request\nReads codebase\nEdits files\nRuns tests\nFixes failures\nNo user prompts"]
    end

    U1 -->|pipeline starts| C1
    C1 -->|artifact ready| U2
    U2 -->|approved| C2
    U2 -->|edit request| C4
    C4 -->|edits applied| U2
    C2 -->|artifact ready| U3
    U3 -->|approved| C3
    U3 -->|edit request| C4
    C4 -->|edits applied| U3
    C3 -->|generator ready + tests pass| U4
    U4 -->|edit request| C4
    C4 -->|edits applied| U4
```

---

### How opencode runs without interruptions

Each pipeline step spawns a short-lived `opencode serve` rooted at the project directory; the backend creates a session via the opencode SDK and sends the step's command template as the prompt, so the agent runs fully autonomously and the server is torn down when done:

```bash
# Step 3 — implement generator (full autonomy)
# Spawn a per-step opencode server rooted at the project dir (cwd), then drive it via the SDK.
# Provider/model configured in api/opencode.json (DeepSeek, base URL https://api.deepseek.com).
cd /projects/{project_id}
opencode serve --port 0 &
# backend: create session → send .claude/commands/implement.md as the prompt (model deepseek-v4-pro)
#          with implementation_dataset.md + data_schema_spec.md as context → tear down server
```

Inside a single opencode session, the agent can:
- Read any file in the project folder
- Write and overwrite any file
- Run shell commands (`uv sync`, `uv run pytest`, `uv run generate-{name} generate`)
- Fix errors from test output and retry — all without asking

The only thing the API streams to the UI during this phase is **progress logs** (stdout), not tool call prompts. The user sees a live log panel, not a permission dialog.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif', 'actorBkg': '#D97757', 'actorBorder': '#b85e3a', 'actorTextColor': '#ffffff', 'actorLineColor': '#D97757', 'signalColor': '#D97757', 'signalTextColor': '#ffffff', 'labelBoxBkgColor': '#2D2D3E', 'labelBoxBorderColor': '#4A4A6A', 'labelTextColor': '#ffffff', 'loopTextColor': '#ffffff', 'noteBorderColor': '#7B5EA7', 'noteBkgColor': '#3D2D5E', 'noteTextColor': '#ffffff', 'activationBorderColor': '#D97757', 'activationBkgColor': '#3D2D2E'}}}%%
sequenceDiagram
    participant API
    participant Opencode as opencode\n(per-step serve)
    participant FS as File System
    participant UI

    API->>Opencode: per-step opencode serve, rooted at project dir\n"implement the generator..."
    Note over Opencode: opencode reads schema + plan
    Opencode->>FS: write src/generators/main.py
    Opencode->>FS: write src/validators/validator.py
    Opencode->>FS: write tests/test_generator.py
    Opencode->>FS: write pyproject.toml
    Note over Opencode: No permission prompts — full autonomy
    Opencode->>Opencode: run uv sync
    Opencode->>Opencode: run uv run pytest
    Note over Opencode: Tests fail → opencode reads error\nfixes code → reruns tests
    Opencode->>Opencode: run uv run generate-name generate
    Opencode->>Opencode: run uv run generate-name validate
    Opencode-->>API: session complete + logs
    API-->>UI: SSE: step3_done\n{files_written, test_result, validation_result}
    Note over UI: User sees final result\nnot intermediate steps
```

---

### What the user sees vs what the agent does internally

| Phase | What user sees | What the agent does internally |
|-------|---------------|----------------------------|
| Step 1 running | Spinner + "Generating schema..." | Reads description, reasons about fields, writes markdown |
| Step 1 done | Full schema in review panel + chat | — |
| User edits via chat | Thinking indicator + diff | Reads artifact, applies changes, computes diff |
| Step 3 running | Live log stream (INFO lines) | Writes 8-12 files, runs tests, fixes errors, reruns |
| Step 3 done | File tree + test summary + approve button | — |
| User edit request on code | Thinking indicator + file diffs | Reads relevant files, edits, runs pytest, fixes failures |

---

## opencode Configuration — Commands & Templates

All the markdown files that configure opencode as a synthetic data generator. These files live in the repo and are read by opencode at runtime — they are the "source code" of the AI pipeline.

### File map

```
CLAUDE.md                                ← repo context, loaded automatically on every session
.claude/commands/
  generate-dataset.md                    → /generate-dataset  (full pipeline, single command)
  generate-schema.md                     → /generate-schema   (step 1 only)
  generate-plan.md                       → /generate-plan     (step 2 only)
  implement.md                           → /implement         (step 3 only)
tools/templates/
  strategy_faker_pure.md                 ← patterns for structured-only generators
  strategy_faker_llm.md                  ← patterns for structured + LLM text fields
  strategy_llm.md                        ← patterns for full LLM generation
  strategy_data_driven.md               ← patterns for real-data statistical synthesis
```

---

### `CLAUDE.md` — Repo context (loaded automatically)

```markdown
# Simulation Data Hub

This repo contains synthetic data generators for enterprise datasets. Each generator lives in its own folder and produces realistic fake data for demos, testing, and AI training.

## Generator Scaffold Flow

To create a new generator, place a `dataset_description.md` in the target folder and run:

/generate-dataset

This single command runs the full pipeline automatically:
1. Reads `dataset_description.md` → produces `data_schema_spec.md`
2. Reads schema → selects strategy → produces `implementation_dataset.md`
3. Implements the full generator, runs it, and verifies output

### Step-by-step (optional, for debugging or partial runs)

/generate-schema   → data_schema_spec.md
/generate-plan     → implementation_dataset.md
/implement         → full generator code + run

## Generation Strategies

| Strategy     | When to use |
|--------------|-------------|
| faker_pure   | All structured fields — IDs, dates, numbers, enums. No LLM needed. |
| faker_llm    | Mostly structured + some free-text or classification fields. LLM called only for those fields. |
| llm          | Deep semantic consistency required across fields. Full LLM generation. |
| data_driven  | Real CSV exists in `data/`. Synthetic data statistically matches real distributions, frequencies, and correlations. |

Strategy templates are in `tools/templates/`.

## Conventions

- All generators use `uv` for dependency management
- Entry point: `uv run generate-{name} generate --config config/generation_config.yaml`
- Output always goes to `output/1k/` for 1k runs
- Seed-based deterministic generation via `config.general.seed`
- DeepSeek API key in `.env` at repo root (never committed); generators default to DeepSeek's OpenAI-compatible API
```

---

### `/generate-dataset` — Full pipeline command

```markdown
You are going to create a complete synthetic data generator from scratch. The user has a
`dataset_description.md` file in the current working directory.

## Guiding principles (apply throughout all steps)

- **Realism first**: generated data must look and feel like real-world data. Use realistic
  distributions, plausible value ranges, and domain-accurate correlations. A data analyst
  should not be able to immediately tell the data is synthetic.
- **Suggest constraints and correlations**: even if not explicitly described, infer and propose
  realistic constraints and field correlations based on domain knowledge.
- **Validation is mandatory**: the generator must include a fully functional `validate` CLI
  subcommand. Validation must cover: required fields not null, enum values within allowed set,
  numeric ranges, referential integrity, and realistic distribution checks.

---

Before starting, read `dataset_description.md` and ask the user any clarifying questions:
- Are there fields that are ambiguous in type or format?
- Should any fields have intentional data quality issues (nulls, duplicates, format errors)?
- Is there a preferred generation strategy, or should you select it automatically?
- Are there domain-specific constraints or correlations not mentioned in the description?
- Any preference on the output format (single CSV, multiple tables, JSON)?
- Suggest any additional fields or correlations you think would make the dataset more realistic.

Wait for the user's answers before proceeding. If the description is clear, summarize your
understanding and confirm with the user before starting.

Execute the following three steps in sequence. After each step, pause, show the user what was
produced, ask if they want to adjust anything, and wait for confirmation before continuing.

---

## Step 1: Generate Schema Spec

Produce `data_schema_spec.md` with:
- Overview, Fields table, Constraints, Correlations & Dependencies, Volume & Distribution Notes,
  Validation Rules

After writing, summarize key decisions and ask:
> "Here's the schema spec. Do you want to adjust any fields, constraints, correlations, or
> distributions before I move to the implementation plan?"

---

## Step 2: Generate Implementation Plan

Read strategy templates (faker_pure / faker_llm / llm / data_driven) and select the best fit.
Produce `implementation_dataset.md` with: strategy + justification, tech stack, project structure,
field implementation map, correlations implementation, LLM prompt notes (if applicable),
generation_config.yaml, validation spec, CLI commands.

After writing, summarize strategy chosen and ask:
> "Here's the implementation plan. Do you want to change the strategy, adjust any field generation
> logic, or modify the validation rules before I start coding?"

---

## Step 3: Implement the Generator

Read `implementation_dataset.md` and `data_schema_spec.md`. Look at `banking_customer_profiles/`
as a structural reference.

Implement every file. No stubs. Tests must have >80% coverage.

The `validate` subcommand is mandatory and must encode the exact rules from the schema spec.

After implementing, run:
  uv run generate-{name} generate --config config/generation_config.yaml
  uv run generate-{name} validate --config config/generation_config.yaml

Fix any errors until both succeed. Report: strategy, records generated, validation result, output path.
```

---

### `/generate-schema` — Step 1 only

```markdown
Read `dataset_description.md` in the current working directory.

## Guiding principles
- **Realism first**: every field, constraint, and correlation must reflect real-world data.
- **Suggest beyond what is described**: use domain knowledge to propose realistic constraints
  and correlations not explicitly mentioned. Label inferred ones with *(inferred)*.
- **Validation rules are mandatory**: every constraint and correlation must have a corresponding
  validation rule.

Produce `data_schema_spec.md` with:

# Data Schema Spec: {Dataset Name}

## Overview
## Fields
| Field | Type | Description | Example |

## Constraints
(label inferred ones with *(inferred)*)

## Correlations & Dependencies
{field_a} → {field_b}: {rule description}
(include directionality and magnitude, label inferred ones)

## Volume & Distribution Notes

## Validation Rules
- Required fields not null
- Enum values within allowed set
- Numeric ranges
- Distribution-level checks
- Referential integrity
- Cross-field consistency rules
```

---

### `/generate-plan` — Step 2 only

```markdown
Read `data_schema_spec.md` and all strategy templates.

## Guiding principles
- **Realism first**: correlations must be encoded concretely — not approximated.
- **Validation is mandatory**: map every constraint and correlation to a specific check in
  validator.py, including distribution-level assertions.

Select strategy:
- faker_pure: all structured fields, no free-text
- faker_llm: mostly structured + some free-text/classification
- llm: deep semantic consistency required
- data_driven: real CSV exists in `data/`

Produce `implementation_dataset.md` with:

# Implementation Plan: {Dataset Name}

## Selected Strategy + Justification
## Tech Stack
## Project Structure
## Generator Name
## Field Implementation Map
| Field | Generator | Correlation logic |

## Correlations Implementation
(concrete Python code patterns for each correlation)

## LLM Prompt Notes (if applicable)
## Config YAML
## Validation Spec
| Rule | Check | Failure condition |

## CLI Commands
```

---

### `/implement` — Step 3 only

```markdown
Read `implementation_dataset.md`, `data_schema_spec.md`, and the selected strategy template.
Look at `banking_customer_profiles/` as a structural reference.

## Guiding principles
- **Realism first**: implement all correlations exactly as specified.
- **Validation CLI is mandatory**: fully implemented, not optional.
- **No stubs**: every file must be fully functional.

Implement all files:
- pyproject.toml, config/generation_config.yaml, src/config.py, src/cli.py
- src/generators/main.py, src/writers/csv_writer.py, src/validators/validator.py
- src/models/schemas.py + LLM enricher (if llm or faker_llm)
- tests/test_generator.py + tests/test_validator.py (>80% coverage)

Validator must encode exact rules from the schema spec — not a generic validator.
Checks: nulls, enum values, numeric ranges, distribution rates, cross-field consistency.
Print PASS / FAIL with observed vs expected value on failures.

After implementing run both commands and fix until they succeed:
  uv run generate-{name} generate --config config/generation_config.yaml
  uv run generate-{name} validate --config config/generation_config.yaml
```

---

### Strategy Templates Summary

| Template | Key patterns |
|----------|-------------|
| `strategy_faker_pure.md` | Seed all randomness (Faker + numpy + random). Weighted choices for correlations. Numpy lognormal/normal for realistic numeric distributions. Multiple tables via FK mappings. |
| `strategy_faker_llm.md` | Phase 1: Faker for structured fields. Phase 2: LLM only for text/classification. `ThreadPoolExecutor` + shared client. Rules fallback enricher. CRITICAL OUTPUT RULES in prompt. |
| `strategy_llm.md` | Pydantic `response_format` for structured batches. `max_completion_tokens ≈ 150 × batch_size`. Batch count mismatch logging. Rate limit guidance: reduce `max_workers` before `batch_size`. |
| `strategy_data_driven.md` | Profile real CSV first (frequencies, scipy distribution fits, conditional correlations). Choose algorithm: Statistical Sampling / GaussianCopula / CTGAN / TVAE / CopulaGAN. Validator uses KS test. Present algorithm recommendation to user before implementing. |

---

## Key Design Decisions

1. **Human-in-the-loop at each step** — the pipeline pauses after schema and plan generation so the user can review and edit before proceeding. The AI never jumps ahead without approval.

2. **Artifacts are plain markdown** — `data_schema_spec.md` and `implementation_dataset.md` are editable text files. Users can tweak them in a Monaco editor before the next step runs.

3. **opencode as coding agent** — Step 3 spawns a short-lived `opencode serve` rooted at the project directory and drives it via the opencode SDK with the `implement` command, giving the agent full file system access to write and run the generator code. This mirrors exactly how a developer would use opencode manually.

4. **Strategy templates are injected at plan time** — the planner agent reads all 4 templates and selects the best one. The chosen template is embedded in `implementation_dataset.md` so the coding agent has full context without re-reading templates.

5. **Validation is always run** — generation is never considered complete until the validator passes. Failed validation blocks the download and shows which rules failed.

6. **Dynamic config form** — the UI reads `generation_config.yaml` and generates the form automatically. No hardcoded fields — every generator exposes its own parameters.

7. **Runs are immutable** — each generation run writes to its own `output/{run_id}/` folder. Previous runs are never overwritten, allowing comparison across configs.

---

## MVP Deployment — Azure VM + Docker Compose

Everything needed to run the full platform on a single Azure VM.

---

### Azure VM Spec

| Setting | Value | Reason |
|---------|-------|--------|
| Size | **Standard_D4s_v3** (4 vCPU, 16 GB RAM) | opencode process is memory-hungry; generators + tests need headroom |
| OS | **Ubuntu 22.04 LTS** | Stable, Docker-supported, widely documented |
| Disk | **64 GB Premium SSD** | Generated files + Docker images + PostgreSQL data |
| Ports open | 80, 443, 22 | HTTP/HTTPS for UI + API, SSH for admin |
| Public IP | Static | Required for consistent DNS |

```bash
# Provision via Azure CLI
az vm create \
  --resource-group synth-data-rg \
  --name synth-data-mvp \
  --image Ubuntu2204 \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --ssh-key-values ~/.ssh/id_rsa.pub \
  --public-ip-sku Standard \
  --os-disk-size-gb 64 \
  --os-disk-caching ReadWrite

# Open ports
az vm open-port --resource-group synth-data-rg --name synth-data-mvp --port 80 --priority 100
az vm open-port --resource-group synth-data-rg --name synth-data-mvp --port 443 --priority 110
```

---

### VM Bootstrap (run once after provisioning)

```bash
#!/bin/bash
# bootstrap.sh — run as azureuser on the VM

# 1. System deps
sudo apt-get update && sudo apt-get install -y \
  git curl wget unzip build-essential \
  ca-certificates gnupg lsb-release

# 2. Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# 3. Docker Compose v2
sudo apt-get install -y docker-compose-plugin
docker compose version

# 4. opencode — headless coding agent CLI (baked into the api image; installed here for host debugging)
curl -fsSL https://opencode.ai/install | bash

# 5. Verify opencode
opencode --version

# 6. uv (Python package manager — used inside worker container and by generators)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv --version

# 7. Clone repo
git clone https://github.com/your-org/simulation-data-hub.git /opt/synth-data
cd /opt/synth-data

# 8. Create .env from template
cp .env.example .env
nano .env   # fill in secrets
```

---

### Environment Variables — `.env`

```bash
# ─── DeepSeek ────────────────────────────────────────────────
# Single key used by opencode (schema/plan/coding), artifact edits, and the LLM generators.
DEEPSEEK_API_KEY=sk-...               # DeepSeek API key (OpenAI-compatible, https://api.deepseek.com)

# ─── PostgreSQL ──────────────────────────────────────────────
POSTGRES_USER=synth
POSTGRES_PASSWORD=changeme_strong_password
POSTGRES_DB=synthdata
DATABASE_URL=postgresql://synth:changeme_strong_password@postgres:5432/synthdata

# ─── Redis ───────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── API ─────────────────────────────────────────────────────
SECRET_KEY=changeme_random_32_chars_min
PROJECTS_DIR=/data/projects          # mounted volume — where all project files live
TEMPLATES_DIR=/app/tools/templates   # read-only, from repo
COMMANDS_DIR=/app/.claude/commands   # read-only, from repo
OPENCODE_MODEL=deepseek-v4-pro       # provider configured in api/opencode.json (DeepSeek, https://api.deepseek.com)
MAX_CONCURRENT_PIPELINES=3           # max simultaneous opencode serve processes

# ─── Frontend ────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://localhost:8000   # or https://your-domain.com/api
```

---

### Docker Images — one per service

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif'}}}%%
graph TB
    subgraph Images["Docker Images"]
        I1["web\nnode:20-alpine\n+ Next.js build"]
        I2["api\npython:3.13-slim\n+ FastAPI + uv\n+ opencode"]
        I3["worker\nCustom Dockerfile\n+ Python 3.13\n+ uv\n+ opencode\n+ git"]
        I4["redis\nredis:7-alpine"]
        I5["postgres\npostgres:16-alpine"]
    end

    I3 -->|needs opencode| CC["opencode binary\n(curl install)"]
    I3 -->|needs uv| UV["uv\n(generator runtime)"]
    I3 -->|needs git| GIT["git\n(generator repo context)"]
```

The `worker` container is custom because it needs opencode (the headless coding agent), uv (Python generator runtime), and git (repo context for generated projects).

---

### Dockerfiles

**`docker/Dockerfile.api`**
```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git && \
    rm -rf /var/lib/apt/lists/*

# uv for dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# opencode — headless coding agent CLI, baked in so the deploy is self-contained
RUN curl -fsSL https://opencode.ai/install | bash
ENV PATH="/root/.opencode/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`docker/Dockerfile.worker`**
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential && \
    rm -rf /var/lib/apt/lists/*

# opencode — headless coding agent CLI
RUN curl -fsSL https://opencode.ai/install | bash
ENV PATH="/root/.opencode/bin:$PATH"
RUN opencode --version

# uv — runs generated generators
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Python API deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Git config — opencode operates inside a git repo context and needs a git identity
RUN git config --global user.email "opencode-worker@synth-data" && \
    git config --global user.name "opencode Worker"

CMD ["uv", "run", "celery", "-A", "api.worker", "worker", "--loglevel=info", "--concurrency=2"]
```

**`docker/Dockerfile.web`**
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY web/package*.json ./
RUN npm ci

COPY web/ .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

---

### `docker-compose.yml`

```yaml
services:

  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      SECRET_KEY: ${SECRET_KEY}
      PROJECTS_DIR: ${PROJECTS_DIR}
      TEMPLATES_DIR: ${TEMPLATES_DIR}
      COMMANDS_DIR: ${COMMANDS_DIR}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      OPENCODE_MODEL: ${OPENCODE_MODEL}
      MAX_CONCURRENT_PIPELINES: ${MAX_CONCURRENT_PIPELINES}
    volumes:
      - projects_data:${PROJECTS_DIR}
      - ./tools/templates:${TEMPLATES_DIR}:ro
      - ./.claude/commands:${COMMANDS_DIR}:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    restart: unless-stopped
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      PROJECTS_DIR: ${PROJECTS_DIR}
      TEMPLATES_DIR: ${TEMPLATES_DIR}
      COMMANDS_DIR: ${COMMANDS_DIR}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      OPENCODE_MODEL: ${OPENCODE_MODEL}
    volumes:
      - projects_data:${PROJECTS_DIR}         # read + write: generator code + output
      - ./tools/templates:${TEMPLATES_DIR}:ro  # read-only: strategy templates
      - ./.claude/commands:${COMMANDS_DIR}:ro  # read-only: slash commands
      - /var/run/docker.sock:/var/run/docker.sock  # optional: if generators need Docker
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
    restart: unless-stopped
    ports:
      - "80:3000"
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
  projects_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/projects    # persisted on VM disk outside Docker
```

---

### opencode inside the Worker Container

opencode needs special attention inside Docker:

```bash
# Verify opencode works inside the worker container
docker compose exec worker opencode --version
docker compose exec worker opencode run "say hello" --model deepseek-v4-pro

# opencode needs DEEPSEEK_API_KEY set (passed via docker-compose env)
# It also needs a git repo context to operate — each project folder must be git init'd

# The worker initializes each new project folder as a git repo before invoking opencode:
# git init /data/projects/{project_id}
# git config user.email "worker@synth-data"
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#D97757', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#b85e3a', 'lineColor': '#D97757', 'secondaryColor': '#7B5EA7', 'tertiaryColor': '#2D2D3E', 'background': '#1E1E2E', 'mainBkg': '#D97757', 'clusterBkg': '#2D2D3E', 'clusterBorder': '#4A4A6A', 'titleColor': '#ffffff', 'edgeLabelBackground': '#3D3D55', 'nodeTextColor': '#ffffff', 'fontFamily': 'ui-sans-serif', 'actorBkg': '#D97757', 'actorBorder': '#b85e3a', 'actorTextColor': '#ffffff', 'actorLineColor': '#D97757', 'signalColor': '#D97757', 'signalTextColor': '#ffffff', 'labelBoxBkgColor': '#2D2D3E', 'labelBoxBorderColor': '#4A4A6A', 'labelTextColor': '#ffffff', 'loopTextColor': '#ffffff', 'noteBorderColor': '#7B5EA7', 'noteBkgColor': '#3D2D5E', 'noteTextColor': '#ffffff', 'activationBorderColor': '#D97757', 'activationBkgColor': '#3D2D2E'}}}%%
sequenceDiagram
    participant Celery as Celery Worker
    participant FS as /data/projects/{id}
    participant Opencode as opencode

    Celery->>FS: mkdir + git init
    Celery->>FS: write dataset_description.md
    Celery->>FS: write data_schema_spec.md
    Celery->>FS: write implementation_dataset.md
    Celery->>Opencode: per-step opencode serve, rooted at /data/projects/{id}\n--model deepseek-v4-pro\n"implement the generator..." 
    Note over Opencode: cwd = /data/projects/{id}\nDEEPSEEK_API_KEY from env\nFull file system access
    Opencode->>FS: write generator files
    Opencode->>Opencode: uv sync && uv run pytest
    Opencode->>Opencode: uv run generate-{name} generate
    Opencode->>Opencode: uv run generate-{name} validate
    Opencode-->>Celery: session complete + logs
    Celery->>Celery: parse result\npublish SSE event
```

---

### First Deploy

```bash
# On the VM, inside /opt/synth-data
cp .env.example .env
nano .env          # fill DEEPSEEK_API_KEY, POSTGRES_PASSWORD, SECRET_KEY

# Create projects dir on VM disk (persisted outside Docker)
sudo mkdir -p /data/projects
sudo chown -R azureuser:azureuser /data

# Build images (first time takes ~5 min)
docker compose build

# Start all services
docker compose up -d

# Run DB migrations
docker compose exec api uv run alembic upgrade head

# Check everything is healthy
docker compose ps
docker compose logs api --tail=50
docker compose logs worker --tail=50

# Test opencode in worker
docker compose exec worker opencode run "say hello" --model deepseek-v4-pro

# Open in browser
curl http://<vm-public-ip>/
```

---

### Useful Ops Commands

```bash
# View live logs
docker compose logs -f worker

# Restart a single service after code change
docker compose up -d --build api

# Check disk usage (projects grow over time)
du -sh /data/projects/*

# Connect to PostgreSQL
docker compose exec postgres psql -U synth -d synthdata

# Scale workers (if VM has enough CPU/RAM)
docker compose up -d --scale worker=2

# Update opencode inside worker
docker compose exec worker bash -c 'curl -fsSL https://opencode.ai/install | bash'
```

---

### Cost Estimate (Azure, MVP)

| Resource | Size | Est. monthly cost |
|----------|------|-------------------|
| VM Standard_D4s_v3 | 4 vCPU / 16 GB | ~$140 |
| Premium SSD 64 GB | OS + data | ~$10 |
| Static Public IP | — | ~$4 |
| **DeepSeek (pipeline)** | deepseek-v4-pro, ~500 pipeline runs/mo | ~$50–150 |
| **DeepSeek (generators)** | deepseek-chat, ~1M tokens/mo | ~$15 |
| **Total** | | **~$220–320/mo** |

