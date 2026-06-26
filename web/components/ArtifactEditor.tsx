"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { MessageSquare, Code2, Eye, Send, Loader2, CheckCircle, ChevronDown, ChevronUp } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

interface EditResult {
  diff: string;
  summary: string;
  changes: string[];
}

interface Props {
  title: string;
  content: string | null;
  onSave: (content: string) => Promise<void>;
  onEdit: (message: string) => Promise<EditResult>;
  onApprove: () => Promise<void>;
  approveLabel?: string;
}

type Tab = "preview" | "editor";

function DiffView({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <div className="rounded-xl border border-surface-600 bg-surface-900 overflow-auto max-h-80 font-mono text-xs">
      {lines.map((line, i) => (
        <div
          key={i}
          className={`px-3 py-0.5 ${
            line.startsWith("+") && !line.startsWith("+++") ? "diff-add" :
            line.startsWith("-") && !line.startsWith("---") ? "diff-remove" :
            line.startsWith("@@") ? "diff-meta" :
            "text-surface-400"
          }`}
        >
          {line || " "}
        </div>
      ))}
    </div>
  );
}

export function ArtifactEditor({ title, content, onSave, onEdit, onApprove, approveLabel = "Approve & Continue" }: Props) {
  const [tab, setTab] = useState<Tab>("preview");
  const [editedContent, setEditedContent] = useState(content || "");
  const [chatMessage, setChatMessage] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "assistant"; text: string; changes?: string[] }[]>([]);
  const [lastDiff, setLastDiff] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [approving, setApproving] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(editedContent);
    } finally {
      setSaving(false);
    }
  }

  async function handleChatEdit() {
    if (!chatMessage.trim() || editing) return;
    const msg = chatMessage.trim();
    setChatMessage("");
    setChatHistory(h => [...h, { role: "user", text: msg }]);
    setEditing(true);
    try {
      const result = await onEdit(msg);
      setLastDiff(result.diff);
      setEditedContent(result.diff ? editedContent : editedContent);
      setChatHistory(h => [...h, { role: "assistant", text: result.summary, changes: result.changes }]);
      setShowDiff(true);
      window.dispatchEvent(new CustomEvent("artifactUpdated"));
    } catch (e) {
      setChatHistory(h => [...h, { role: "assistant", text: `Error: ${(e as Error).message}` }]);
    } finally {
      setEditing(false);
    }
  }

  async function handleApprove() {
    setApproving(true);
    try {
      await onApprove();
    } finally {
      setApproving(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 h-full">
      {/* Artifact panel — 3/5 */}
      <div className="lg:col-span-3 flex flex-col rounded-2xl border border-surface-600 bg-surface-800 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-600">
          <h3 className="font-semibold text-sm text-gray-100">{title}</h3>
          <div className="flex gap-1">
            {(["preview", "editor"] as Tab[]).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors
                  ${tab === t ? "bg-brand-500/20 text-brand-400" : "text-surface-400 hover:text-gray-100 hover:bg-surface-700"}`}
              >
                {t === "preview" ? <Eye size={12} /> : <Code2 size={12} />}
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {tab === "preview" ? (
            <div className="p-5 prose-dark">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content || "*No content yet*"}</ReactMarkdown>
            </div>
          ) : (
            <MonacoEditor
              height="100%"
              defaultLanguage="markdown"
              value={editedContent}
              onChange={v => setEditedContent(v || "")}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: "off",
                wordWrap: "on",
                scrollBeyondLastLine: false,
                padding: { top: 16, bottom: 16 },
              }}
            />
          )}
        </div>

        {tab === "editor" && (
          <div className="p-3 border-t border-surface-600">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 rounded-lg bg-surface-700 px-3 py-1.5 text-xs font-medium text-gray-100 hover:bg-surface-600 disabled:opacity-50 transition-colors"
            >
              {saving ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle size={12} />}
              Save changes
            </button>
          </div>
        )}
      </div>

      {/* Chat + approve panel — 2/5 */}
      <div className="lg:col-span-2 flex flex-col gap-4">
        {/* Chat */}
        <div className="flex-1 flex flex-col rounded-2xl border border-surface-600 bg-surface-800 overflow-hidden min-h-0">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-600">
            <MessageSquare size={14} className="text-brand-400" />
            <span className="text-sm font-semibold text-gray-100">Chat with AI</span>
          </div>

          <div className="flex-1 overflow-auto p-4 space-y-3">
            {chatHistory.length === 0 && (
              <div className="text-center py-6">
                <div className="text-sm text-surface-400">Ask the AI to modify this artifact.</div>
                <div className="mt-2 text-xs text-surface-500">e.g. "add an email field" or "change fraud rate to 5%"</div>
              </div>
            )}
            {chatHistory.map((msg, i) => (
              <div key={i} className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed
                  ${msg.role === "user"
                    ? "bg-brand-500/20 text-brand-100 border border-brand-500/20"
                    : "bg-surface-700 text-gray-100 border border-surface-600"}`}>
                  <p>{msg.text}</p>
                  {msg.changes && msg.changes.length > 0 && (
                    <ul className="mt-2 space-y-0.5">
                      {msg.changes.map((c, j) => (
                        <li key={j} className="text-green-400 flex items-start gap-1">
                          <span className="mt-0.5">+</span>
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            ))}
            {editing && (
              <div className="flex gap-2">
                <div className="bg-surface-700 border border-surface-600 rounded-xl px-3 py-2 text-xs text-surface-400 flex items-center gap-2">
                  <Loader2 size={12} className="animate-spin text-brand-400" />
                  AI is editing...
                </div>
              </div>
            )}
          </div>

          {lastDiff && (
            <div className="border-t border-surface-600 px-4 py-2">
              <button
                onClick={() => setShowDiff(!showDiff)}
                className="flex items-center gap-1.5 text-xs text-surface-400 hover:text-gray-100 transition-colors"
              >
                {showDiff ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                View diff
              </button>
              {showDiff && <div className="mt-2"><DiffView diff={lastDiff} /></div>}
            </div>
          )}

          <div className="border-t border-surface-600 p-3">
            <div className="flex gap-2">
              <textarea
                rows={2}
                value={chatMessage}
                onChange={e => setChatMessage(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleChatEdit(); } }}
                placeholder="Ask the AI to modify this artifact..."
                className="flex-1 resize-none rounded-xl border border-surface-600 bg-surface-700 px-3 py-2 text-xs text-gray-100 placeholder-surface-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500/20 transition"
              />
              <button
                onClick={handleChatEdit}
                disabled={!chatMessage.trim() || editing}
                className="flex h-full items-end justify-center rounded-xl bg-brand-500 p-2.5 text-white hover:bg-brand-600 disabled:opacity-50 transition-colors"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Approve */}
        <button
          onClick={handleApprove}
          disabled={approving || !content}
          className="flex items-center justify-center gap-2 rounded-xl bg-green-500/10 border border-green-500/30 py-3 text-sm font-semibold text-green-400 hover:bg-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {approving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
          {approving ? "Approving..." : approveLabel}
        </button>
      </div>
    </div>
  );
}
