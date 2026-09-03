"use client";

import { useEffect, useState, useCallback } from "react";
import { AuditEvent, Metrics, PaymentFailure, fetchAuditTrail, fetchFailures, fetchMetrics } from "@/lib/api";
import { MetricsStrip } from "@/components/MetricsStrip";
import { FailureList } from "@/components/FailureList";
import { DecisionTimeline } from "@/components/DecisionTimeline";

const POLL_INTERVAL_MS = 8000;

export default function DashboardPage() {
  const [failures, setFailures] = useState<PaymentFailure[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    try {
      const [f, m] = await Promise.all([fetchFailures(100), fetchMetrics()]);
      setFailures(f);
      setMetrics(m);
      setError(null);
    } catch (e) {
      setError(
        "Couldn't reach the RazorRecover backend. Is it running at the configured API URL?"
      );
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    loadList();
    const interval = setInterval(loadList, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadList]);

  useEffect(() => {
    if (!selectedId) {
      setEvents([]);
      return;
    }
    setLoadingTimeline(true);
    fetchAuditTrail(selectedId)
      .then(setEvents)
      .catch(() => setEvents([]))
      .finally(() => setLoadingTimeline(false));
  }, [selectedId]);

  // Keep the selected failure's own record fresh (e.g. after a poll updates its status)
  useEffect(() => {
    if (selectedId && !failures.some((f) => f.id === selectedId)) {
      setSelectedId(null);
    }
  }, [failures, selectedId]);

  const selectedFailure = failures.find((f) => f.id === selectedId) ?? null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-8">
        <div className="flex items-baseline justify-between gap-4 flex-wrap">
          <h1 className="font-serif text-2xl text-ink">RazorRecover</h1>
          <p className="text-[13px] text-ink-muted">
            Failed recurring-payment recovery — decisions, policy checks, and outcomes
          </p>
        </div>
      </header>

      {error && (
        <div className="mb-6 border border-unresolved/30 bg-unresolved-soft text-unresolved text-[14px] px-4 py-3">
          {error}
        </div>
      )}

      {metrics && (
        <section className="mb-8 pb-6 border-b border-rule-strong">
          <MetricsStrip metrics={metrics} />
        </section>
      )}

      <section className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-8">
        <div>
          <h2 className="text-[13px] text-ink-muted mb-2">Failures</h2>
          <div className="border-t border-rule max-h-[70vh] overflow-y-auto">
            {loadingList ? (
              <p className="py-10 text-center text-ink-muted text-sm">Loading…</p>
            ) : (
              <FailureList failures={failures} selectedId={selectedId} onSelect={setSelectedId} />
            )}
          </div>
        </div>

        <div className="lg:border-l lg:border-rule lg:pl-8">
          <h2 className="text-[13px] text-ink-muted mb-2">Decision timeline</h2>
          <DecisionTimeline failure={selectedFailure} events={events} loading={loadingTimeline} />
        </div>
      </section>
    </main>
  );
}
