"use client";

import { useEffect, useState, use } from "react";
import dynamic from "next/dynamic";
import { api, type Run } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Play, Save, Download, ChevronRight, Loader2, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function RunsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [configYaml, setConfigYaml] = useState<string>("");
  const [originalYaml, setOriginalYaml] = useState<string>("");
  const [configPath, setConfigPath] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    api.runs.list(id).then(setRuns).finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    api.projects.getConfig(id)
      .then(({ content, path }) => {
        setConfigYaml(content);
        setOriginalYaml(content);
        setConfigPath(path);
        setConfigError(null);
      })
      .catch((e: Error) => {
        setConfigError(e.message);
      })
      .finally(() => setConfigLoading(false));
  }, [id]);

  useEffect(() => {
    if (!activeRunId) return;
    const es = new EventSource(`${BASE}/projects/${id}/runs/${activeRunId}/events`);
    es.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.type === "log") {
        setLogs(l => [...l, event.line]);
      } else if (event.type === "done") {
        es.close();
        setActiveRunId(null);
        api.runs.list(id).then(setRuns);
      }
    };
    return () => es.close();
  }, [activeRunId, id]);

  const isDirty = configYaml !== originalYaml;

  async function handleCreate(saveAsDefault: boolean) {
    if (saveAsDefault) setSaving(true); else setCreating(true);
    setLogs([]);
    try {
      const run = await api.runs.create(id, {
        num_records: 0,
        seed: 0,
        strategy: "",
        output_format: "",
        config_yaml: configYaml,
        save_as_default: saveAsDefault,
      });
      if (saveAsDefault) setOriginalYaml(configYaml);
      setRuns(r => [run, ...r]);
      setActiveRunId(run.id);
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setCreating(false);
      setSaving(false);
    }
  }

  async function handleSaveOnly() {
    setSaving(true);
    try {
      await api.projects.updateConfig(id, configYaml);
      setOriginalYaml(configYaml);
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const busy = creating || saving || !!activeRunId;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center gap-2 text-sm text-surface-400 mb-6">
        <a href="/" className="hover:text-gray-100">Projects</a>
        <ChevronRight size={14} />
        <a href={`/projects/${id}`} className="hover:text-gray-100">Project</a>
        <ChevronRight size={14} />
        <span className="text-gray-100">Runs</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* New run form */}
        <div className="lg:col-span-3 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-100">New Generation Run</h2>
            {configPath && (
              <span className="text-xs font-mono text-surface-500">{configPath}</span>
            )}
          </div>

          <div className="rounded-2xl border border-surface-600 bg-surface-800 p-5 space-y-4">
            {configLoading ? (
              <div className="flex items-center justify-center py-10 text-surface-400">
                <Loader2 size={16} className="animate-spin mr-2" /> Loading config...
              </div>
            ) : configError ? (
              <div className="flex items-start gap-2 rounded-lg bg-amber-500/10 border border-amber-500/30 px-4 py-3 text-sm text-amber-300">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <div>
                  <div className="font-medium">No config available</div>
                  <div className="text-xs text-amber-300/80 mt-1">{configError}</div>
                  <div className="text-xs text-amber-300/60 mt-1">Run the pipeline first to generate <code className="font-mono">config/generation_config.yaml</code>.</div>
                </div>
              </div>
            ) : (
              <>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-medium text-surface-400 uppercase tracking-wide">Configuration (YAML)</label>
                    {isDirty && <span className="text-[10px] font-mono text-amber-400">● unsaved changes</span>}
                  </div>
                  <div className="rounded-xl border border-surface-600 overflow-hidden">
                    <MonacoEditor
                      height="420px"
                      defaultLanguage="yaml"
                      value={configYaml}
                      onChange={(v) => setConfigYaml(v ?? "")}
                      theme="vs-dark"
                      options={{
                        minimap: { enabled: false },
                        fontSize: 12,
                        tabSize: 2,
                        lineNumbers: "on",
                        scrollBeyondLastLine: false,
                        wordWrap: "on",
                      }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-surface-500">
                    Edit to override for this run. Click <span className="font-medium text-surface-300">Save &amp; Run</span> to also persist as the project default.
                  </p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleCreate(false)}
                    disabled={busy}
                    className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-brand-500 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-glow"
                  >
                    {creating ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                    {creating ? "Starting..." : activeRunId ? "Running..." : "Run"}
                  </button>
                  <button
                    onClick={() => handleCreate(true)}
                    disabled={busy || !isDirty}
                    title={!isDirty ? "No changes to save" : "Save as default and run"}
                    className="flex-1 flex items-center justify-center gap-2 rounded-xl border border-brand-500/50 bg-surface-700 py-2.5 text-sm font-semibold text-gray-100 hover:bg-surface-600 disabled:opacity-50 transition-colors"
                  >
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    {saving ? "Saving..." : "Save & Run"}
                  </button>
                  <button
                    onClick={handleSaveOnly}
                    disabled={busy || !isDirty}
                    title={!isDirty ? "No changes to save" : "Save as default without running"}
                    className="rounded-xl border border-surface-600 bg-surface-700 px-3 text-sm text-surface-300 hover:bg-surface-600 disabled:opacity-50 transition-colors"
                  >
                    Save only
                  </button>
                </div>
              </>
            )}
          </div>

          {/* Live logs */}
          {(activeRunId || logs.length > 0) && (
            <div className="rounded-2xl border border-surface-600 bg-surface-900 overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2 border-b border-surface-700">
                {activeRunId ? (
                  <Loader2 size={12} className="animate-spin text-brand-400" />
                ) : (
                  <CheckCircle size={12} className="text-green-400" />
                )}
                <span className="text-xs font-mono text-surface-400">Live output</span>
              </div>
              <div className="p-3 max-h-60 overflow-auto">
                {logs.map((line, i) => (
                  <div key={i} className="log-line">{line}</div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Run history */}
        <div className="lg:col-span-2">
          <h2 className="text-lg font-bold text-gray-100 mb-4">Run History</h2>
          {loading ? (
            <div className="flex justify-center py-10"><Loader2 size={24} className="animate-spin text-brand-500" /></div>
          ) : runs.length === 0 ? (
            <div className="text-center py-10 text-surface-400 text-sm">No runs yet. Start your first generation above.</div>
          ) : (
            <div className="space-y-3">
              {runs.map(run => (
                <RunCard key={run.id} run={run} projectId={id} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RunCard({ run, projectId }: { run: Run; projectId: string }) {
  const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const validPassed = run.validation_result?.passed;

  return (
    <div className="rounded-2xl border border-surface-600 bg-surface-800 p-4">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <StatusBadge status={run.status} />
            {run.num_records && (
              <span className="text-xs text-surface-400 font-mono">{run.num_records.toLocaleString()} records</span>
            )}
          </div>
          <div className="mt-1 text-xs text-surface-500 font-mono">
            {run.id.slice(0, 8)}...
            {run.duration_seconds && ` · ${run.duration_seconds.toFixed(1)}s`}
            {run.created_at && ` · ${formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}`}
          </div>
        </div>
        {run.status === "success" && (
          <a
            href={`${BASE}/projects/${projectId}/runs/${run.id}/download`}
            className="flex items-center gap-1.5 rounded-lg bg-surface-700 px-3 py-1.5 text-xs text-gray-100 hover:bg-surface-600 transition-colors"
          >
            <Download size={12} />
            Download
          </a>
        )}
      </div>

      {run.validation_result && (
        <div className={`mt-2 rounded-lg px-3 py-2 text-xs ${validPassed ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
          <div className="flex items-center gap-1.5 font-medium">
            {validPassed ? <CheckCircle size={11} /> : <XCircle size={11} />}
            Validation {validPassed ? "PASSED" : "FAILED"}
          </div>
          {!validPassed && run.validation_result.errors?.length > 0 && (
            <ul className="mt-1 space-y-0.5 font-mono">
              {run.validation_result.errors.slice(0, 3).map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </div>
      )}

      {run.run_config && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(run.run_config).map(([k, v]) =>
            typeof v === "object" ? Object.entries(v as Record<string, unknown>).map(([k2, v2]) => (
              <span key={`${k}.${k2}`} className="rounded-md bg-surface-700 px-2 py-0.5 text-[10px] font-mono text-surface-400">
                {k2}={String(v2)}
              </span>
            )) : null
          )}
        </div>
      )}
    </div>
  );
}
