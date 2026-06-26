const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

interface JobStatus<T> {
  id: string;
  status: "pending" | "done" | "error";
  result?: T;
  error?: string;
}

async function waitForJob<T>(jobId: string, { intervalMs = 1500, timeoutMs = 15 * 60 * 1000 } = {}): Promise<T> {
  const start = Date.now();
  while (true) {
    const job = await req<JobStatus<T>>(`/jobs/${jobId}`);
    if (job.status === "done") return job.result as T;
    if (job.status === "error") throw new Error(job.error || "Job failed");
    if (Date.now() - start > timeoutMs) throw new Error("Job timed out");
    await new Promise(r => setTimeout(r, intervalMs));
  }
}

export interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
  strategy: string | null;
  created_at: string;
  updated_at: string;
  schema_content?: string | null;
  plan_content?: string | null;
  artifacts?: { id: string; type: string; path: string }[];
  pipeline_steps?: { id: string; step: string; status: string; started_at: string | null; completed_at: string | null }[];
}

export interface Run {
  id: string;
  project_id: string;
  num_records: number | null;
  status: string;
  run_config: Record<string, unknown> | null;
  validation_result: { passed: boolean; errors: string[] } | null;
  duration_seconds: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export const api = {
  projects: {
    list: () => req<Project[]>("/projects"),
    create: (data: { name: string; description: string }) =>
      req<Project>("/projects", { method: "POST", body: JSON.stringify(data) }),
    get: (id: string) => req<Project>(`/projects/${id}`),
    delete: (id: string) =>
      fetch(`${BASE}/projects/${id}`, { method: "DELETE" }).then(res => {
        if (!res.ok) throw new Error(`Delete failed: ${res.statusText}`);
      }),
    startPipeline: (id: string) =>
      req<{ status: string }>(`/projects/${id}/pipeline/start`, { method: "POST" }),
    getSchema: (id: string) => req<{ content: string | null }>(`/projects/${id}/schema`),
    updateSchema: (id: string, content: string) =>
      req(`/projects/${id}/schema`, { method: "PATCH", body: JSON.stringify({ content }) }),
    editSchema: async (id: string, message: string) => {
      const { job_id } = await req<{ job_id: string }>(`/projects/${id}/schema/edit`, {
        method: "POST", body: JSON.stringify({ message }),
      });
      return waitForJob<{ diff: string; summary: string; changes: string[] }>(job_id);
    },
    approveSchema: (id: string) =>
      req(`/projects/${id}/schema/approve`, { method: "PATCH" }),
    getPlan: (id: string) => req<{ content: string | null }>(`/projects/${id}/plan`),
    updatePlan: (id: string, content: string) =>
      req(`/projects/${id}/plan`, { method: "PATCH", body: JSON.stringify({ content }) }),
    editPlan: async (id: string, message: string) => {
      const { job_id } = await req<{ job_id: string }>(`/projects/${id}/plan/edit`, {
        method: "POST", body: JSON.stringify({ message }),
      });
      return waitForJob<{ diff: string; summary: string; changes: string[] }>(job_id);
    },
    approvePlan: (id: string) =>
      req(`/projects/${id}/plan/approve`, { method: "PATCH" }),
    getConfig: (id: string) =>
      req<{ content: string; path: string }>(`/projects/${id}/config`),
    updateConfig: (id: string, content: string) =>
      req<{ status: string; path: string }>(`/projects/${id}/config`, {
        method: "PATCH", body: JSON.stringify({ content }),
      }),
  },
  runs: {
    list: (projectId: string) => req<Run[]>(`/projects/${projectId}/runs`),
    create: (
      projectId: string,
      data: {
        num_records: number;
        seed: number;
        strategy: string;
        output_format: string;
        config_yaml?: string | null;
        save_as_default?: boolean;
      },
    ) =>
      req<Run>(`/projects/${projectId}/runs`, { method: "POST", body: JSON.stringify(data) }),
    get: (projectId: string, runId: string) => req<Run>(`/projects/${projectId}/runs/${runId}`),
  },
};
