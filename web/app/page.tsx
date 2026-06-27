"use client";

import { useEffect, useState } from "react";
import { api, type Project } from "@/lib/api";
import { Plus, Database, Clock, CheckCircle, Loader2, AlertCircle, ChevronRight, Cpu, Sparkles, Trash2, Upload, FileText, X } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending:        { label: "Pending",       color: "text-surface-400 bg-surface-700",                icon: <Clock size={12} /> },
  schema_running: { label: "Generating Schema", color: "text-yellow-400 bg-yellow-400/10",           icon: <Loader2 size={12} className="animate-spin" /> },
  schema_review:  { label: "Schema Review", color: "text-brand-400 bg-brand-400/10",                 icon: <CheckCircle size={12} /> },
  plan_running:   { label: "Generating Plan",   color: "text-yellow-400 bg-yellow-400/10",           icon: <Loader2 size={12} className="animate-spin" /> },
  plan_review:    { label: "Plan Review",   color: "text-purple-400 bg-purple-400/10",               icon: <CheckCircle size={12} /> },
  coding_running: { label: "Coding",        color: "text-blue-400 bg-blue-400/10",                   icon: <Loader2 size={12} className="animate-spin" /> },
  ready:          { label: "Ready",         color: "text-green-400 bg-green-400/10",                 icon: <CheckCircle size={12} /> },
  error:          { label: "Error",         color: "text-red-400 bg-red-400/10",                     icon: <AlertCircle size={12} /> },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || { label: status, color: "text-surface-400 bg-surface-700", icon: null };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${cfg.color}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [file, setFile] = useState<File | null>(null);
  const [creating, setCreating] = useState(false);

  function closeCreate() {
    setShowCreate(false);
    setForm({ name: "", description: "" });
    setFile(null);
  }
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(e: React.MouseEvent, project: Project) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`Delete project "${project.name}"? This removes the database record and all files on disk. This cannot be undone.`)) return;
    setDeletingId(project.id);
    try {
      await api.projects.delete(project.id);
      setProjects(ps => ps.filter(p => p.id !== project.id));
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setDeletingId(null);
    }
  }

  useEffect(() => {
    api.projects.list().then(setProjects).finally(() => setLoading(false));
  }, []);

  async function handleCreate() {
    // Description is optional when a source CSV is provided (data-driven flow).
    if (!form.name.trim() || (!form.description.trim() && !file)) return;
    setCreating(true);
    try {
      const description = form.description.trim() ||
        "Generate synthetic data that matches the structure and distributions of the uploaded source file.";
      const project = await api.projects.create({ name: form.name, description });
      if (file) {
        await api.projects.uploadData(project.id, file);
      }
      window.location.href = `/projects/${project.id}`;
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      {/* Hero */}
      <div className="mb-10 flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={16} className="text-brand-400" />
            <span className="text-xs font-mono text-brand-400 uppercase tracking-widest">Synthetic Data</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-100">Projects</h1>
          <p className="mt-1 text-surface-400">Describe a dataset — AI builds the generator.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 transition-colors shadow-glow"
        >
          <Plus size={16} /> New Project
        </button>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg rounded-2xl border border-surface-600 bg-surface-800 p-6 shadow-2xl animate-slide-up">
            <h2 className="text-lg font-semibold text-gray-100 mb-1">New Project</h2>
            <p className="text-sm text-surface-400 mb-5">Describe your dataset and the AI will build a generator for it.</p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-surface-400 uppercase tracking-wide mb-1.5">Project Name</label>
                <input
                  className="w-full rounded-xl border border-surface-600 bg-surface-700 px-3.5 py-2.5 text-sm text-gray-100 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 transition"
                  placeholder="e.g. Insurance Claims Dataset"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-surface-400 uppercase tracking-wide mb-1.5">
                  Dataset Description{file && <span className="ml-1 normal-case text-surface-500">(optional — derived from your CSV)</span>}
                </label>
                <textarea
                  rows={6}
                  className="w-full rounded-xl border border-surface-600 bg-surface-700 px-3.5 py-2.5 text-sm text-gray-100 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 transition resize-none font-mono"
                  placeholder="Describe the dataset you need. Include fields, distributions, business rules, correlations, volume..."
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>

              {/* Optional: upload a real CSV → data-driven generation */}
              <div>
                <label className="block text-xs font-medium text-surface-400 uppercase tracking-wide mb-1.5">
                  Source CSV <span className="normal-case text-surface-500">(optional — match an existing dataset)</span>
                </label>
                {file ? (
                  <div className="flex items-center justify-between rounded-xl border border-brand-500/30 bg-brand-500/10 px-3.5 py-2.5">
                    <span className="flex items-center gap-2 text-sm text-gray-100 truncate">
                      <FileText size={15} className="text-brand-400 shrink-0" />
                      <span className="truncate">{file.name}</span>
                      <span className="text-xs text-surface-400 shrink-0">({(file.size / 1024).toFixed(0)} KB)</span>
                    </span>
                    <button onClick={() => setFile(null)} className="ml-2 text-surface-400 hover:text-gray-100 shrink-0" title="Remove file">
                      <X size={15} />
                    </button>
                  </div>
                ) : (
                  <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-surface-600 bg-surface-700/50 px-3.5 py-3 text-sm text-surface-400 hover:border-brand-500/50 hover:text-gray-100 transition">
                    <Upload size={15} />
                    Upload a CSV to generate similar data
                    <input
                      type="file"
                      accept=".csv,text/csv"
                      className="hidden"
                      onChange={e => setFile(e.target.files?.[0] ?? null)}
                    />
                  </label>
                )}
              </div>
            </div>

            <div className="mt-5 flex gap-3 justify-end">
              <button onClick={closeCreate} className="rounded-xl px-4 py-2 text-sm text-surface-400 hover:text-gray-100 hover:bg-surface-700 transition-colors">
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !form.name.trim() || (!form.description.trim() && !file)}
                className="flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {creating ? <Loader2 size={14} className="animate-spin" /> : <Cpu size={14} />}
                {creating ? "Creating..." : "Create & Start Pipeline"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Projects grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={32} className="animate-spin text-brand-500" />
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-surface-700 border border-surface-600">
            <Database size={28} className="text-surface-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-100">No projects yet</h3>
          <p className="mt-1 text-surface-400 text-sm">Create your first project to start generating synthetic data.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-6 flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 transition-colors"
          >
            <Plus size={16} /> New Project
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map(p => (
            <a
              key={p.id}
              href={`/projects/${p.id}`}
              className="group relative flex flex-col rounded-2xl border border-surface-600 bg-surface-800 p-5 hover:border-brand-500/50 hover:shadow-glow transition-all"
            >
              <button
                onClick={(e) => handleDelete(e, p)}
                disabled={deletingId === p.id}
                title="Delete project"
                className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 flex items-center justify-center h-7 w-7 rounded-lg bg-surface-700/80 text-surface-400 hover:bg-red-500/15 hover:text-red-400 transition-all disabled:opacity-50"
              >
                {deletingId === p.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
              </button>
              <div className="flex items-start justify-between mb-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/15 border border-brand-500/20">
                  <Database size={18} className="text-brand-400" />
                </div>
                <StatusBadge status={p.status} />
              </div>
              <h3 className="font-semibold text-gray-100 group-hover:text-brand-400 transition-colors">{p.name}</h3>
              <p className="mt-1 text-sm text-surface-400 line-clamp-2 flex-1">{p.description}</p>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-surface-500">
                  {formatDistanceToNow(new Date(p.created_at), { addSuffix: true })}
                </span>
                <ChevronRight size={16} className="text-surface-500 group-hover:text-brand-400 group-hover:translate-x-0.5 transition-all" />
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
