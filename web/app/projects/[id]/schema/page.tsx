"use client";

import { useEffect, useState, use } from "react";
import { api } from "@/lib/api";
import { ArtifactEditor } from "@/components/ArtifactEditor";
import { ChevronRight, Loader2 } from "lucide-react";
import { useProjectEvents } from "@/hooks/useProjectEvents";

export default function SchemaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.projects.getSchema(id).then(r => setContent(r.content)).finally(() => setLoading(false));
  }, [id]);

  useProjectEvents(id, (event) => {
    if (event.type === "step_done" && event.step === "schema") {
      api.projects.getSchema(id).then(r => setContent(r.content));
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
        <span className="text-gray-100">Schema Spec</span>
      </div>

      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-100">Data Schema Spec</h1>
        <p className="text-sm text-surface-400 mt-0.5">Review the AI-generated schema. Chat with the AI to request changes, or edit directly.</p>
      </div>

      <div className="flex-1 min-h-0">
        <ArtifactEditor
          title="data_schema_spec.md"
          content={content}
          onSave={c => api.projects.updateSchema(id, c).then(() => setContent(c))}
          onEdit={async msg => {
            const r = await api.projects.editSchema(id, msg);
            const fresh = await api.projects.getSchema(id);
            setContent(fresh.content);
            return r;
          }}
          onApprove={async () => {
            await api.projects.approveSchema(id);
            window.location.href = `/projects/${id}`;
          }}
          approveLabel="Approve Schema & Generate Plan"
        />
      </div>
    </div>
  );
}
