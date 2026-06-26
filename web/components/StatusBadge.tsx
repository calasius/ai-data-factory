import { Clock, CheckCircle, Loader2, AlertCircle, Play } from "lucide-react";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending:        { label: "Pending",          color: "text-surface-400 bg-surface-700",          icon: <Clock size={11} /> },
  schema_running: { label: "Generating Schema", color: "text-yellow-400 bg-yellow-400/10",        icon: <Loader2 size={11} className="animate-spin" /> },
  schema_review:  { label: "Schema Review",    color: "text-brand-400 bg-brand-500/15",           icon: <CheckCircle size={11} /> },
  plan_running:   { label: "Generating Plan",  color: "text-yellow-400 bg-yellow-400/10",         icon: <Loader2 size={11} className="animate-spin" /> },
  plan_review:    { label: "Plan Review",      color: "text-purple-400 bg-purple-500/15",         icon: <CheckCircle size={11} /> },
  coding_running: { label: "Implementing",     color: "text-blue-400 bg-blue-400/10",             icon: <Loader2 size={11} className="animate-spin" /> },
  ready:          { label: "Ready",            color: "text-green-400 bg-green-400/10",           icon: <CheckCircle size={11} /> },
  error:          { label: "Error",            color: "text-red-400 bg-red-400/10",               icon: <AlertCircle size={11} /> },
  running:        { label: "Running",          color: "text-blue-400 bg-blue-400/10",             icon: <Loader2 size={11} className="animate-spin" /> },
  success:        { label: "Success",          color: "text-green-400 bg-green-400/10",           icon: <CheckCircle size={11} /> },
  failed:         { label: "Failed",           color: "text-red-400 bg-red-400/10",               icon: <AlertCircle size={11} /> },
  validation_failed: { label: "Validation Failed", color: "text-orange-400 bg-orange-400/10",    icon: <AlertCircle size={11} /> },
  done:           { label: "Done",             color: "text-green-400 bg-green-400/10",           icon: <CheckCircle size={11} /> },
  reviewing:      { label: "Awaiting Review",  color: "text-brand-400 bg-brand-500/15",           icon: <Clock size={11} /> },
};

export function StatusBadge({ status, size = "sm" }: { status: string; size?: "sm" | "xs" }) {
  const cfg = STATUS_CONFIG[status] || { label: status, color: "text-surface-400 bg-surface-700", icon: null };
  const padding = size === "xs" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${padding} ${cfg.color}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}
