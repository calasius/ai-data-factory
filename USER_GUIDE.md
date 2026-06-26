# AI Data Factory — User Guide

A web platform that turns a plain-English description of a dataset into a **fully working synthetic data generator**, end to end. No coding required from the user.

---

## Table of Contents

- [What it does](#what-it-does)
- [Supported generation strategies](#supported-generation-strategies)
- [Under the hood — opencode + DeepSeek as the agent pipeline](#under-the-hood--opencode--deepseek-as-the-agent-pipeline)
- [End-to-end walkthrough of the UI](#end-to-end-walkthrough-of-the-ui)
  - [1. Projects home](#1-projects-home)
  - [2. Creating a new project](#2-creating-a-new-project)
  - [3. Project detail page — the pipeline](#3-project-detail-page--the-pipeline)
  - [4. Schema Review](#4-schema-review)
  - [5. Plan Review](#5-plan-review)
  - [6. Code Generation](#6-code-generation)
  - [7. Runs — producing datasets](#7-runs--producing-datasets)
- [Tips for writing a good dataset description](#tips-for-writing-a-good-dataset-description)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)

---

## What it does

1. You describe the dataset you need (fields, distributions, business rules, volume) in plain English.
2. The platform designs a schema, picks a generation strategy, writes the generator code, runs it, and validates the output.
3. You download a synthetic CSV. You can re-run the generator with different sizes and seeds as many times as you want.

The platform has **3 review stages** plus an execution stage. At each review stage you either approve the artifact or chat with the AI to refine it in place.

---

## Supported generation strategies

| Strategy | When to use |
|---|---|
| **`faker_pure`** | Fully structured datasets (IDs, enums, numbers, dates). Fully deterministic given a seed. |
| **`faker_llm`** | Structured fields + a few free-text or classification fields. Faker builds the skeleton; an LLM enriches the text fields (narratives, reviews, classifications). |
| **`llm`** | Datasets where many fields must be deeply semantically consistent with each other (e.g. claim narratives where amount, date, and description must align). |
| **`data_driven`** | You provide a reference CSV and the platform produces synthetic data that statistically matches it (GaussianCopula, CTGAN, TVAE). |

> **Note:** for `data_driven`, CSV upload through the UI is not yet implemented. See [Known limitations](#known-limitations).

---

## Under the hood — opencode + DeepSeek as the agent pipeline

Instead of writing a custom multi-agent orchestration, the entire AI pipeline is **opencode** — an open-source headless coding agent CLI — driven by the FastAPI backend via the **opencode Python SDK** (`opencode_ai`). opencode **is** the agent for every step, and it runs on **DeepSeek** (model `deepseek-v4-pro`, configured in `api/opencode.json` as a DeepSeek provider over its OpenAI-compatible API at `https://api.deepseek.com`).

For each pipeline step, the backend spawns a short-lived `opencode serve` process **rooted at the project directory** (this is what gives the run its filesystem isolation), creates a session, sends the step's command template as the prompt, lets the agent do the work with its tools, then tears the server down. It's one isolated server per step — startup is ~1–2s, negligible against generation time.

Each stage is backed by a reusable **command template** stored in `.claude/commands/`, reused verbatim as the prompt for that step:

| Stage | Command template | What opencode does |
|---|---|---|
| Schema | `/generate-schema` | Reads the user's dataset description, produces `data_schema_spec.md`. |
| Plan | `/generate-plan` | Reads the schema + strategy templates in `tools/templates/`, picks the best strategy, writes `implementation_dataset.md`. |
| Coding | `/implement` | Reads the plan + chosen strategy template, writes the full generator, runs it, validates output, fixes errors. |
| Runs | `/generate-dataset` | Executes the approved generator with a run's seed/size config, streams logs. |

The **Chat-with-the-AI** feature on the schema and plan review pages talks to **DeepSeek directly** via its OpenAI-compatible API (`api.deepseek.com`, model `deepseek-chat`), streamed over SSE: the backend sends the current Markdown artifact plus the user's instruction, and it returns the updated artifact plus a JSON diff summary.

### Why this architecture matters

- **Any capability opencode has, the pipeline has** — reading files, running shell commands, running Python, iterating until tests pass — because it is literally opencode (DeepSeek).
- **Zero-deploy customization**: editing `.claude/commands/*.md` changes behavior for every future project immediately. No rebuilds, no deploys.
- **New strategies are plain Markdown**: drop a `strategy_foo.md` into `tools/templates/` and the planner can pick it.
- **One key**: a single `DEEPSEEK_API_KEY` env var — no per-user auth, no host credential mount, no subscription. The opencode binary is baked into the api Docker image, so the deploy is self-contained.
- **Live streaming is trivial**: the opencode SDK surfaces the agent's output → piped through FastAPI SSE → streamed to the browser UI.

---

## End-to-end walkthrough of the UI

### 1. Projects home

**URL:** `/`

When you open the app you land on the Projects page. It lists every project you've created, showing for each:

- **Name** and a truncated description.
- A **status badge** indicating where the project currently is in the pipeline (see statuses below).
- How long ago it was created.

**Statuses you might see on a project card:**

| Status | Meaning |
|---|---|
| **Pending** | Created but pipeline hasn't started. |
| **Generating Schema** | The AI agent is drafting the data schema spec. |
| **Schema Review** | Schema ready — waiting for you to approve or iterate. |
| **Generating Plan** | The AI agent is drafting the implementation plan. |
| **Plan Review** | Plan ready — waiting for you to approve or iterate. |
| **Coding** | opencode is writing and testing the generator. |
| **Ready** | Generator is built and ready to produce datasets. |
| **Error** | Something failed — open the project to see details. |

**Top-right:** a **New Project** button.

Clicking a project card takes you to that project's detail page (section 3).

### 2. Creating a new project

Click **New Project** on the home page to open the creation modal. You'll fill in two fields:

- **Project Name** — a short label (e.g. *"Insurance Claims Dataset"*).
- **Dataset Description** — a plain-English description of what you need.

Click **Create & Start Pipeline**. The platform:

1. Creates the project.
2. Kicks off **Step 1 — Schema Generation** automatically.
3. Redirects you to the project detail page.

> 💡 The quality of the generated dataset is largely determined by this description. See [Tips for writing a good dataset description](#tips-for-writing-a-good-dataset-description) below.

### 3. Project detail page — the pipeline

**URL:** `/projects/<project-id>`

This page shows a vertical 3-step pipeline with a live status for each step:

1. **Schema Generation** — AI analyses your description and designs the data schema.
2. **Implementation Plan** — AI selects a generation strategy and writes the implementation plan.
3. **Code Generation** — opencode implements the full generator, runs tests, and validates output.

Each step's icon updates in real time via **Server-Sent Events (SSE)**:

- ⚪ Pending — not started.
- 🔵 Running — the AI agent is working (animated spinner).
- ✅ Done — completed successfully.
- ❌ Error — failed; click through to see details.

When a step reaches **Review** state, its card becomes clickable and takes you to the corresponding review page (Schema or Plan). After **Code Generation** finishes you can go to **Runs**.

There's also a **Runs** link once the generator is ready, to trigger dataset generation.

### 4. Schema Review

**URL:** `/projects/<project-id>/schema`

This is where you review and refine the schema the AI agent produced. The page is a **split view**:

```
┌──────────────────────────────┬───────────────────────────────────┐
│  💬 Chat with the AI         │  📝  data_schema_spec.md          │
│  ──────────────────────────  │  ──────────────────────────────   │
│  [Your message + send]       │  [Preview] [Editor] tabs          │
│                              │                                    │
│  AI: "Added a new...         │  # Overview                        │
│  field — here's the diff."   │  Dataset of ...                    │
│                              │                                    │
│                              │  | Field | Type | Description |   │
│                              │  |-------|------|-------------|   │
│                              │  | ...   | ...  | ...         |   │
│                              │                                    │
│                              │  [Approve & Continue ▶]           │
└──────────────────────────────┴───────────────────────────────────┘
```

**Left pane — Chat with the AI:**

- Type a natural-language instruction (e.g. *"add a `policy_holder_age` field correlated with `claim_type`"*, *"change `amount_usd` to a lognormal between 100 and 50000"*, *"remove the `notes` field"*).
- Click **Send**. The AI updates the Markdown artifact, and shows you:
  - A one-line **summary** of what changed.
  - A list of **specific changes**.
  - A collapsible **diff view** of before/after.
- You can iterate as many times as you want.

**Right pane — the artifact, with two tabs:**

- **Preview** (default) — rendered Markdown, including GFM tables.
- **Editor** — Monaco editor for direct hand-editing. Your edits can be saved with **Save** (persists to disk).

**Bottom-right — Approve button:**

- Once satisfied, click **Approve & Continue**. This locks the schema and advances the pipeline to **Step 2 — Plan Generation**.

### 5. Plan Review

**URL:** `/projects/<project-id>/plan`

Once the schema is approved, the AI agent generates an `implementation_dataset.md` — the technical plan that specifies:

- **Selected strategy** + justification (`faker_pure`, `faker_llm`, `llm`, `data_driven`).
- **Tech stack** (Python libraries, LLM providers).
- **Project structure** (files and modules).
- **Field implementation map** — for each column, whether it's Faker, LLM, or data-driven, with the distribution / parameters.
- **Correlations implementation**.
- **Config YAML** schema.
- **Validation spec** (what checks to run on generated data).
- **CLI commands** exposed by the generator.

The UI is the same split-view **ArtifactEditor** as Schema Review:

- **Chat pane (left)** — ask the AI to tweak the plan (*"switch to `faker_llm`, the narrative field needs context"*, *"use chi-squared test for `claim_status`"*, *"set batch size to 50 for LLM calls"*).
- **Artifact pane (right)** — Preview / Editor tabs. Edit directly if needed.
- **Approve & Continue** — advances to **Step 3 — Code Generation**.

### 6. Code Generation

This step is **mostly automated** — opencode:

1. Reads the approved plan and the selected strategy template.
2. Writes the generator (Python package with a CLI entry point).
3. Runs it on a sample.
4. Validates the output.
5. Fixes any errors it finds and retries.

On the project detail page you'll see a live spinner for this step. When it completes, the project status changes to **Ready** and you can navigate to the **Runs** tab to produce datasets.

If it **fails** (status turns red), open the project detail page and inspect the error. You can:

- Re-run the step.
- Go back to the Plan review, tweak instructions via the AI, approve again, and let opencode rewrite the generator.

### 7. Runs — producing datasets

**URL:** `/projects/<project-id>/runs`

This is where you actually generate synthetic data. The page has two columns:

**Left column — New Generation Run form:**

| Field | Description |
|---|---|
| **Records** | How many rows to generate. 1 – 100,000. |
| **Seed** | Integer for reproducibility. Same seed + same config → same dataset. |
| **Strategy** | `Rules (Faker)`, `LLM`, or `Data Driven`. Usually leave as the one the AI picked in the plan. |
| **Output Format** | `csv`, `json`, or `parquet`. |

Click **Generate** to start the run. You'll see:

- **Live logs** streaming in a console below the form — everything the generator prints to stdout.
- The run appears immediately at the top of the **Run History** on the right with status `running`.

**Right column — Run History:**

Each run card shows:

- **Status badge** — `pending`, `running`, `success`, `failed`, `validation_failed`.
- **Record count** and short ID.
- **Duration** once done.
- **Relative timestamp**.
- **Download** button (shown on successful runs) — downloads the output file.
- **Validation result** block — green ✅ if validation passed, red ❌ with error list if it failed.
- **Run config tags** — a quick visual of the parameters that produced this run.

> 💡 You can launch multiple runs with different seeds or sizes from the same generator without going back to Schema or Plan. The generator is reusable.

---

## Tips for writing a good dataset description

The richer your initial description, the better the schema (and the whole pipeline) will be. A good description includes:

- **Domain and purpose** — *"Insurance claims for ML fraud detection training."*
- **List of fields** — even if inferred/approximate. *"claim_id, policy_id, incident_date, claim_type, amount_usd, location_city, narrative."*
- **Value ranges / enums** — *"claim_type is one of: collision, theft, water_damage, fire."*
- **Distributions** — *"amount_usd follows a lognormal; 80% under $5k, 5% over $50k."*
- **Business rules / correlations** — *"water_damage claims are cheaper than fire claims on average. narrative must mention the claim_type and location_city."*
- **Volume** — *"~1,000 rows for training, ~100 rows for testing."*

**Example prompt that produces good results:**

> Insurance claims dataset with ~100 records. Fields: `claim_id`, `policy_id`, `incident_date` (last 90 days), `claim_type` (collision/theft/water_damage/fire with weights 35/25/25/15), `amount_usd` (varies by claim_type: collision 2k-20k, theft 500-5k, water 500-3k, fire 5k-80k), `location_city` (US cities), and a free-text `narrative` written in first person that must be semantically consistent with `claim_type`, `amount_usd`, and `location_city`. The narrative tone should be informal like a real policyholder reporting.

---

## Troubleshooting

### The pipeline status doesn't update live

The project detail page updates via SSE plus a 10-second safety poll. If you see the status stuck:

- Refresh the page.
- Check your browser has no ad-blocker or extension blocking EventSource connections.

### A step failed with an error

- Open the project detail page — errors display inline on the failing step.
- For Schema/Plan errors, re-enter the review page and chat with the AI to retry or adjust.
- For Code Generation errors, go back to the Plan page, refine the instructions, approve again, and opencode will re-implement.

### A run failed

- Inspect the **live logs** that streamed while it ran — they contain stderr from the generator.
- Check the run card on the History panel — the **Validation** block shows why validation rejected the output (if that's the failure mode).
- Common fixes: re-run with a different seed (rules out a seed-specific edge case), lower the record count to isolate the issue, or tweak the plan and let opencode rewrite the generator.

### Download doesn't appear on a successful run

If the run is marked success but there's no Download button, something went wrong writing the output file. Check the live logs for I/O errors, and inspect the run's output directory on the server.

### LLM runs are slow

LLM-based runs (`faker_llm`, `llm`) call DeepSeek's OpenAI-compatible API per batch of rows, so latency scales with dataset size. Expect tens of seconds to a few minutes for 100–1000 rows.

---

## Known limitations

- **`data_driven` CSV upload is not yet wired up in the UI.** The strategy logic exists, but until the upload flow is implemented, you'll need to place the reference CSV on the server manually.
- **LLM batching and parallelism vary by generator.** opencode uses the strategy templates in `tools/templates/` to decide batch size and workers; some generators are faster than others. Standardizing this via the strategy templates is on the roadmap.
- **No user auth.** The preview deployment is single-tenant and relies on the operator's single `DEEPSEEK_API_KEY`. Multi-user auth is planned.
