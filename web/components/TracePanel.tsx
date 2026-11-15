"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { api, type Health, type TraceEntry } from "@/lib/api";

const KIND: Record<string, { label: string; cls: string }> = {
  event: { label: "EVENT", cls: "bg-white/10 text-white/70" },
  lender: { label: "LENDER", cls: "bg-amber/20 text-amber" },
  rule: { label: "RULE", cls: "bg-sky/15 text-sky" },
  tool: { label: "TOOL", cls: "bg-[#a78bfa]/20 text-[#c4b5fd]" },
  llm: { label: "LLM", cls: "bg-[#f472b6]/20 text-[#f9a8d4]" },
  guard: { label: "GUARD", cls: "bg-[#5fe0a8]/15 text-[#5fe0a8]" },
  consent: { label: "CONSENT", cls: "bg-[#5fe0a8] text-navy" },
  voice: { label: "SARVAM", cls: "bg-[#fbbf24]/20 text-[#fcd34d]" },
  nudge: { label: "NUDGE", cls: "bg-brand/40 text-white" },
};

export default function TracePanel({ userId, epoch, health }: { userId: string; epoch: number; health: Health | null }) {
  const [entries, setEntries] = useState<TraceEntry[]>([]);
  const [consents, setConsents] = useState(0);
  const last = useRef(0);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEntries([]);
    setConsents(0);
    last.current = 0;
    let alive = true;
    const tick = async () => {
      try {
        const r = await api.trace(userId, last.current);
        if (!alive) return;
        setConsents(r.consents.length);
        if (r.entries.length) {
          last.current = r.entries[r.entries.length - 1].id;
          setEntries((e) => [...e, ...r.entries].slice(-200));
        }
      } catch {}
    };
    void tick();
    const id = setInterval(tick, 1200);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [userId, epoch]);

  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" });
  }, [entries.length]);

  return (
    <aside className="flex h-full min-h-[420px] flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#0a1322]/90">
      <div className="border-b border-white/10 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-[15px] font-semibold text-white">Agent trace</h2>
          <span className="flex items-center gap-1.5 text-[11px] text-white/50">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#5fe0a8]" /> live
          </span>
        </div>
        <p className="mt-1 text-[12px] leading-snug text-white/55">Rules decide. The LLM explains. The user consents.</p>
        <div className="mt-2.5 flex flex-wrap gap-1.5 text-[10.5px] font-medium">
          <span className="rounded-full bg-sky/15 px-2 py-0.5 text-sky">Rules engine: on</span>
          <span className={`rounded-full px-2 py-0.5 ${health?.agent_models?.length ? "bg-[#f472b6]/20 text-[#f9a8d4]" : "bg-white/10 text-white/50"}`}>
            Agent: {health?.agent_models?.[0] ?? "intent router"}
            {health && health.agent_models.length > 1 && <span className="opacity-60"> → {health.agent_models[1]}</span>}
          </span>
          <span className={`rounded-full px-2 py-0.5 ${health?.voice ? "bg-[#fbbf24]/20 text-[#fcd34d]" : "bg-white/10 text-white/50"}`}>
            {health?.voice ? `Sarvam voice: ${health.tts} · ${health.stt}` : "Sarvam voice: off"}
          </span>
          <span className={`rounded-full px-2 py-0.5 ${health?.mcp?.startsWith("on") ? "bg-[#fbbf24]/20 text-[#fcd34d]" : "bg-white/10 text-white/50"}`}>
            Sarvam MCP: {health?.mcp ?? "off"}
          </span>
          <span className="rounded-full bg-[#5fe0a8]/15 px-2 py-0.5 text-[#5fe0a8]">Consents logged: {consents}</span>
        </div>
      </div>
      <div ref={box} className="thin-scroll flex-1 space-y-1.5 overflow-y-auto p-3 font-mono text-[11.5px]">
        {entries.length === 0 && <p className="p-3 text-white/35">Waiting for a loan application…</p>}
        <AnimatePresence initial={false}>
          {entries.map((e) => {
            const k = KIND[e.kind] ?? KIND.event;
            const fail = /FAIL|REJECTED/.test(e.title);
            return (
              <motion.div
                key={e.id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
                className={`rounded-lg px-2.5 py-1.5 ${fail ? "bg-amber/10" : "bg-white/[0.03]"}`}
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-px shrink-0 rounded px-1.5 py-px text-[9.5px] font-bold tracking-wide ${k.cls}`}>{k.label}</span>
                  <span className={`min-w-0 break-words leading-snug ${fail ? "text-amber" : "text-white/90"}`}>{e.title}</span>
                </div>
                {e.detail && <p className="mt-0.5 break-words pl-1 leading-snug text-white/45">{e.detail}</p>}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </aside>
  );
}
