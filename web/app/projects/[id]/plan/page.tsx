"use client";

import { useEffect, useState, use } from "react";
import { api } from "@/lib/api";
import { ArtifactEditor } from "@/components/ArtifactEditor";
import { ChevronRight, Loader2 } from "lucide-react";
import { useProjectEvents } from "@/hooks/useProjectEvents";

export default function PlanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.projects.getPlan(id).then(r => setContent(r.content)).finally(() => setLoading(false));
  }, [id]);

  useProjectEvents(id, (event) => {
    if (event.type === "step_done" && event.step === "plan") {
      api.projects.getPlan(id).then(r => setContent(r.content));
    }
  });

  if (loading) {
    return <div className="flex items-center justify-center py-20"><Loader2 size={32} className="animate-spin text-brand-500" /></div>;
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex items-center gap-2 text-sm text-surface-400 mb-4">
        <a href="/" className="hover:text-gray-100">Projects</a>
        <ChevronRight size={14} />
        <a href={`/projects/${id}`} className="hover:text-gray-100">Project</a>
        <ChevronRight size={14} />
        <span className="text-gray-100">Implementation Plan</span>
      </div>

      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-100">Implementation Plan</h1>
        <p className="text-sm text-surface-400 mt-0.5">Review the generation strategy. Chat with the AI to adjust before code generation.</p>
      </div>

      <div className="flex-1 min-h-0">
        <ArtifactEditor
          title="implementation_dataset.md"
          content={content}
          onSave={c => api.projects.updatePlan(id, c).then(() => setContent(c))}
          onEdit={async msg => {
            const r = await api.projects.editPlan(id, msg);
            const fresh = await api.projects.getPlan(id);
            setContent(fresh.content);
            return r;
          }}
          onApprove={async () => {
            await api.projects.approvePlan(id);
            window.location.href = `/projects/${id}`;
          }}
          approveLabel="Approve Plan & Generate Code"
        />
      </div>
    </div>
  );
}
