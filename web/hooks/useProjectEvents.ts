"use client";

import { useEffect } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Subscribe to the project's SSE channel and invoke `onEvent` on every event.
 * Auto-reconnects via the EventSource builtin behavior.
 */
export function useProjectEvents(projectId: string | undefined, onEvent: (e: any) => void) {
  useEffect(() => {
    if (!projectId) return;
    const es = new EventSource(`${BASE}/projects/${projectId}/events`);
    es.onmessage = (ev) => {
      try {
        onEvent(JSON.parse(ev.data));
      } catch {
        // ignore non-JSON
      }
    };
    es.onerror = () => {
      // EventSource will retry automatically
    };
    return () => es.close();
  }, [projectId]);
}

export function useRunEvents(projectId: string | undefined, runId: string | undefined, onEvent: (e: any) => void) {
  useEffect(() => {
    if (!projectId || !runId) return;
    const es = new EventSource(`${BASE}/projects/${projectId}/runs/${runId}/events`);
    es.onmessage = (ev) => {
      try {
        onEvent(JSON.parse(ev.data));
      } catch {
        // ignore non-JSON
      }
    };
    return () => es.close();
  }, [projectId, runId]);
}
