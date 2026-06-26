"use client";

import { useEffect, useState, use } from "react";
import { api, type Project } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { useProjectEvents } from "@/hooks/useProjectEvents";
import {
  Database, FileText, Code, Play, ChevronRight, Loader2,
  CheckCircle, Clock, ArrowRight, AlertCircle, Zap, RefreshCw, Download,
} from "lucide-react";
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
import { formatDistanceToNow } from "date-fns";

const STEPS = [
  { key: "schema", label: "Schema Generation", icon: FileText, description: "AI analyses your description and designs the data schema" },
  { key: "plan",   label: "Implementation Plan", icon: Code, description: "AI selects a generation strategy and writes the implementation plan" },
  { key: "coding", label: "Code Generation",    icon: Zap, description: "The AI implements the full generator, runs tests, and validates output" },
];

function PipelineStep({ step, status, active }: { step: typeof STEPS[0]; status?: string; active: boolean }) {
  const Icon = step.icon;
  const isDone = status === "done";
  const isRunning = status === "running";
  const isError = status === "error";

  return (
    <div className={`relative flex gap-4 ${active ? "opacity-100" : "opacity-60"}`}>
      <div className="flex flex-col items-center">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border transition-all
          ${isDone ? "border-green-500/50 bg-green-500/10 text-green-400" :
            isRunning ? "border-brand-500/50 bg-brand-500/10 text-brand-400 shadow-glow animate-pulse-slow" :
            isError ? "border-red-500/50 bg-red-500/10 text-red-400" :
            "border-surface-600 bg-surface-700 text-surface-400"}`}>
          {isRunning ? <Loader2 size={18} className="animate-spin" /> :
           isDone ? <CheckCircle size={18} /> :
           isError ? <AlertCircle size={18} /> :
           <Icon size={18} />}
        </div>
        <div className="mt-2 w-px flex-1 bg-surface-600 min-h-[24px]" />
      </div>
      <div className="pb-6 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-gray-100">{step.label}</span>
          {status && <StatusBadge status={status} size="xs" />}
        </div>
        <p className="mt-0.5 text-xs text-surface-400">{step.description}</p>
      </div>
    </div>
  );
}

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    loadProject();
    // Slow polling as a safety net in case SSE drops
    const interval = setInterval(loadProject, 10000);
    return () => clearInterval(interval);
  }, [id]);

  // Real-time updates: any backend event triggers an immediate refresh
  useProjectEvents(id, (event) => {
    if (event.type === "step_progress" || event.type === "step_done") {
      loadProject();
    }
  });

  async function loadProject() {
    try {
      const p = await api.projects.get(id);
      setProject(p);
    } finally {
      setLoading(false);
    }
  }

  async function startPipeline() {
    setStarting(true);
    try {
      await api.projects.startPipeline(id);
      await loadProject();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setStarting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="animate-spin text-brand-500" />
      </div>
    );
  }

  if (!project) return <div className="text-center py-20 text-surface-400">Project not found</div>;

  const steps = project.pipeline_steps || [];
  const getStep = (key: string) => steps.find(s => s.step === key);

  const canStartPipeline = project.status === "pending";
  const schemaReady = ["schema_review", "plan_running", "plan_review", "coding_running", "ready"].includes(project.status);
  const planReady = ["plan_review", "coding_running", "ready"].includes(project.status);
  const isReady = project.status === "ready";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-surface-400 mb-6">
        <a href="/" className="hover:text-gray-100 transition-colors">Projects</a>
        <ChevronRight size={14} />
        <span className="text-gray-100">{project.name}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left — project info + pipeline */}
        <div className="lg:col-span-1 space-y-6">
          {/* Project card */}
          <div className="rounded-2xl border border-surface-600 bg-surface-800 p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/15 border border-brand-500/20">
                <Database size={18} className="text-brand-400" />
              </div>
              <StatusBadge status={project.status} />
            </div>
            <h1 className="text-xl font-bold text-gray-100">{project.name}</h1>
            <p className="mt-2 text-sm text-surface-400 leading-relaxed line-clamp-4">{project.description}</p>
            <div className="mt-3 text-xs text-surface-500">
              Created {formatDistanceToNow(new Date(project.created_at), { addSuffix: true })}
            </div>
          </div>

          {/* Pipeline controls */}
          <div className="rounded-2xl border border-surface-600 bg-surface-800 p-5">
            <h2 className="text-sm font-semibold text-gray-100 mb-4">Pipeline</h2>

            {STEPS.map((step, i) => {
              const s = getStep(step.key);
              return <PipelineStep key={step.key} step={step} status={s?.status} active={true} />;
            })}

            {canStartPipeline && (
              <button
                onClick={startPipeline}
                disabled={starting}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-brand-500 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-glow mt-2"
              >
                {starting ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                {starting ? "Starting..." : "Start AI Pipeline"}
              </button>
            )}
          </div>
        </div>

        {/* Right — actions */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-sm font-semibold text-surface-400 uppercase tracking-wide">Actions</h2>

          <ActionCard
            href={schemaReady ? `/projects/${id}/schema` : undefined}
            disabled={!schemaReady}
            icon={<FileText size={20} />}
            title="Schema Spec"
            description="Review and edit the AI-generated data schema. Chat with the AI to request changes."
            badge={schemaReady ? "Ready for review" : "Waiting for generation"}
            badgeColor={schemaReady ? "brand" : "surface"}
          />

          <ActionCard
            href={planReady ? `/projects/${id}/plan` : undefined}
            disabled={!planReady}
            icon={<Code size={20} />}
            title="Implementation Plan"
            description="Review the generation strategy and field implementation map."
            badge={planReady ? "Ready for review" : "Locked until schema is approved"}
            badgeColor={planReady ? "purple" : "surface"}
          />

          <ActionCard
            href={isReady ? `/projects/${id}/runs` : undefined}
            disabled={!isReady}
            icon={<Play size={20} />}
            title="Generate Data"
            description="Run the generator with custom parameters. View history and download outputs."
            badge={isReady ? "Generator ready" : "Locked until plan is approved"}
            badgeColor={isReady ? "green" : "surface"}
          />

          <ActionCard
            href={isReady ? `${BASE}/projects/${id}/download` : undefined}
            disabled={!isReady}
            external
            icon={<Download size={20} />}
            title="Download Project"
            description="Download the full project as a ZIP (schema, plan, generator code, configs)."
            badge={isReady ? "Available" : "Locked until generator is ready"}
            badgeColor={isReady ? "green" : "surface"}
          />
        </div>
      </div>
    </div>
  );
}

function ActionCard({
  href, disabled, icon, title, description, badge, badgeColor, external,
}: {
  href?: string;
  disabled: boolean;
  icon: React.ReactNode;
  title: string;
  description: string;
  badge: string;
  badgeColor: "brand" | "purple" | "green" | "surface";
  external?: boolean;
}) {
  const badgeStyles = {
    brand: "text-brand-400 bg-brand-500/10 border-brand-500/20",
    purple: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    green: "text-green-400 bg-green-400/10 border-green-400/20",
    surface: "text-surface-400 bg-surface-700 border-surface-600",
  };

  const inner = (
    <div className={`flex items-center gap-4 rounded-2xl border p-5 transition-all
      ${disabled
        ? "border-surface-700 bg-surface-800/50 opacity-60 cursor-not-allowed"
        : "border-surface-600 bg-surface-800 hover:border-brand-500/50 hover:shadow-glow cursor-pointer group"}`}>
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border transition-colors
        ${disabled ? "border-surface-600 bg-surface-700 text-surface-500" : "border-brand-500/30 bg-brand-500/10 text-brand-400 group-hover:bg-brand-500/20"}`}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-semibold text-gray-100">{title}</span>
          <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${badgeStyles[badgeColor]}`}>
            {badge}
          </span>
        </div>
        <p className="text-sm text-surface-400">{description}</p>
      </div>
      {!disabled && <ArrowRight size={18} className="text-surface-500 group-hover:text-brand-400 group-hover:translate-x-0.5 transition-all shrink-0" />}
    </div>
  );

  if (href && !disabled) {
    return external
      ? <a href={href} rel="noopener">{inner}</a>
      : <a href={href}>{inner}</a>;
  }
  return <div>{inner}</div>;
}
