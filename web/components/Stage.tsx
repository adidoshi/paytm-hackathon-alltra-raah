"use client";

import { motion } from "framer-motion";
import { ArrowDownLeft, ArrowUpRight, FastForward, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, inr, type Journey, type Lang, type Persona } from "@/lib/api";
import { LANG_LABEL } from "@/lib/strings";
import Phone, { RaahMark, type Screen } from "./Phone";
import TracePanel from "./TracePanel";

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

function Metric({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="rounded-2xl bg-white/[0.05] p-3">
      <p className="text-[11px] text-white/50">{label}</p>
      <motion.p key={value} initial={{ opacity: 0.3, y: 4 }} animate={{ opacity: 1, y: 0 }} className={`font-display text-[19px] font-semibold ${good ? "text-[#5fe0a8]" : "text-white"}`}>
        {value}
      </motion.p>
    </div>
  );
}

export default function Stage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [userId, setUserId] = useState("ravi");
  const [lang, setLang] = useState<Lang>("mr");
  const [journey, setJourney] = useState<Journey | null>(null);
  const [screen, setScreen] = useState<Screen>("home");
  const [step, setStep] = useState(0);
  const [banner, setBanner] = useState<Journey["notifications"][number] | null>(null);
  const [health, setHealth] = useState<{ llm: boolean; voice: boolean } | null>(null);
  const [epoch, setEpoch] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const persona = personas.find((p) => p.user_id === userId);

  useEffect(() => {
    api.personas().then(setPersonas).catch(() => setError("Cannot reach the Raah API. Start it with: uvicorn api.main:app --port 8000"));
    api.health().then(setHealth).catch(() => {});
  }, []);

  const sync = useCallback((j: Journey) => {
    setJourney(j);
    if (j.status === "new") setScreen("home");
    else if (j.status === "approved" || j.status === "approved_direct") setScreen("approved");
    else setScreen((s) => (s === "raah" || s === "rejected" ? s : "raah"));
  }, []);

  // load the journey whenever the customer changes
  useEffect(() => {
    let alive = true;
    setBanner(null);
    setStep(0);
    api.journey(userId, lang).then((j) => alive && sync(j)).catch(() => {});
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, epoch]);

  function pickPersona(p: Persona) {
    setLang(p.language);
    setUserId(p.user_id);
  }

  async function changeLang(l: Lang) {
    setLang(l);
    if (journey && journey.status !== "new") setJourney(await api.journey(userId, l));
  }

  async function onApply(amount: number, tenure: number) {
    setScreen("checking");
    setBanner(null);
    try {
      const [j] = await Promise.all([api.apply(userId, amount, tenure, lang), wait(2200)]);
      setJourney(j);
      setStep(0);
      setScreen(j.status === "approved_direct" ? "approved" : "rejected");
    } catch (e) {
      setError((e as Error).message);
      setScreen("apply");
    }
  }

  async function onAdvance() {
    if (!journey?.can_advance || busy) return;
    setBusy(true);
    try {
      const j = await api.advance(userId, lang);
      setJourney(j);
      setScreen("raah");
      setStep(2);
      const top = j.notifications[0];
      if (top) {
        setBanner(top);
        if (top.kind !== "eligible") setTimeout(() => setBanner((b) => (b?.id === top.id ? null : b)), 5500);
      }
    } finally {
      setBusy(false);
    }
  }

  async function onReset() {
    await api.reset();
    setJourney(null);
    setScreen("home");
    setEpoch((e) => e + 1);
  }

  const snap = journey?.snapshot;
  const started = journey && journey.status !== "new";

  return (
    <div className="stage-bg flex min-h-screen flex-col text-white">
      {/* header */}
      <header className="flex flex-wrap items-center gap-x-6 gap-y-3 border-b border-white/10 px-5 py-3 lg:px-8">
        <div className="flex items-center gap-3">
          <RaahMark size={34} />
          <div>
            <p className="font-display text-[22px] font-bold leading-none tracking-tight">Raah</p>
            <p className="mt-1 text-[11px] text-white/55">by Team Alltra</p>
          </div>
        </div>
        <p className="hidden text-[13px] text-white/70 md:block">No loan rejection is a dead end.</p>
        <div className="flex-1" />
        <p className="order-last w-full text-[10.5px] font-semibold uppercase tracking-[0.14em] text-sky/90 xl:order-none xl:w-auto">
          Paytm Build for India AI Hackathon · Pune · Track 2: AI-Powered Financial Journeys
        </p>
        <div className="flex items-center gap-1 rounded-full bg-white/[0.07] p-1">
          {(Object.keys(LANG_LABEL) as Lang[]).map((l) => (
            <button
              key={l} onClick={() => changeLang(l)}
              className={`rounded-full px-3 py-1.5 text-[12.5px] font-medium transition ${lang === l ? "bg-sky text-navy" : "text-white/70 hover:text-white"}`}
            >
              {LANG_LABEL[l]}
            </button>
          ))}
        </div>
        <button onClick={onReset} className="flex items-center gap-1.5 rounded-full border border-white/15 px-3 py-2 text-[12.5px] text-white/75 hover:bg-white/5">
          <RotateCcw size={13} /> Reset demo
        </button>
      </header>

      {error && <p className="bg-rust px-5 py-2 text-center text-[13px]">{error}</p>}

      <main className="mx-auto grid w-full max-w-[1480px] flex-1 grid-cols-1 gap-5 p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:p-6 xl:grid-cols-[minmax(280px,360px)_auto_minmax(300px,1fr)]">
        {/* left: customer and data */}
        <section className="order-2 flex flex-col gap-4 xl:order-1 xl:h-[780px]">
          <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-white/45">Customer</p>
            <div className="mt-2.5 space-y-2">
              {personas.map((p) => (
                <button
                  key={p.user_id} onClick={() => pickPersona(p)}
                  className={`flex w-full items-center gap-3 rounded-2xl p-2.5 text-left transition ${p.user_id === userId ? "bg-sky/15 ring-1 ring-sky/60" : "hover:bg-white/5"}`}
                >
                  <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-display font-semibold ${p.user_id === userId ? "bg-sky text-navy" : "bg-white/10"}`}>
                    {p.first_name[0]}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[14px] font-semibold">{p.name}</span>
                    <span className="block truncate text-[12px] text-white/55">
                      {p.occupation} · wants {inr(p.application.amount)}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-white/45">Demo clock</p>
              <p className="font-mono text-[12px] text-sky">Day {journey?.day ?? 0}</p>
            </div>
            <div className="mt-3 flex items-center">
              {[0, 30, 60, 90].map((d, i) => (
                <div key={d} className="flex flex-1 items-center last:flex-none">
                  <span className={`flex h-7 w-7 items-center justify-center rounded-full text-[10.5px] font-bold ${(journey?.day ?? 0) >= d && started ? "bg-sky text-navy" : "bg-white/10 text-white/50"}`}>{d}</span>
                  {i < 3 && <span className={`mx-1 h-0.5 flex-1 rounded ${(journey?.day ?? 0) > d ? "bg-sky" : "bg-white/10"}`} />}
                </div>
              ))}
            </div>
            <button
              onClick={onAdvance} disabled={!journey?.can_advance || busy}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl bg-sky py-2.5 text-[13.5px] font-semibold text-navy transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-white/35"
            >
              <FastForward size={15} /> Simulate +30 days
            </button>
            <p className="mt-2 text-[11.5px] leading-snug text-white/45">
              Plays the next month of Paytm and bureau events, then the eligibility watcher re-runs the lender rules.
            </p>
          </div>

          <div className="flex min-h-[220px] flex-1 flex-col overflow-hidden rounded-3xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-white/45">What the rules see</p>
            <div className="mt-2.5 grid grid-cols-2 gap-2">
              <Metric label="Credit score" value={snap?.score ? String(snap.score) : "none"} good={!!snap?.score && snap.score >= 700} />
              <Metric label="On-time months" value={String(snap?.on_time_cycles ?? "–")} />
              <Metric label="Card use" value={snap?.utilisation != null ? `${snap.utilisation}%` : "no card"} good={snap?.utilisation != null && snap.utilisation <= 30} />
              <Metric label="EMI load with loan" value={snap ? `${snap.foir}%` : "–"} good={!!snap && snap.foir <= 50} />
            </div>
            <p className="mt-4 text-[11px] font-semibold uppercase tracking-wider text-white/45">Paytm activity (mock data)</p>
            <div className="thin-scroll mt-2 flex-1 space-y-1.5 overflow-y-auto pr-1">
              {(journey?.feed ?? []).map((e, i) => (
                <motion.div key={`${e.day}-${e.text}-${i}`} initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2.5 rounded-xl bg-white/[0.04] px-2.5 py-2">
                  <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${e.dir === "in" ? "bg-[#5fe0a8]/15 text-[#5fe0a8]" : "bg-white/10 text-white/60"}`}>
                    {e.dir === "in" ? <ArrowDownLeft size={13} /> : <ArrowUpRight size={13} />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12.5px] text-white/90">{e.text}</span>
                    <span className="block text-[10.5px] text-white/40">{e.source} · day {e.day}</span>
                  </span>
                  {e.amount > 0 && <span className="shrink-0 font-mono text-[11.5px] text-white/70">{inr(e.amount)}</span>}
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* centre: what the customer sees */}
        <section className="order-1 flex justify-center xl:order-2">
          {persona && (
            <Phone
              persona={persona} journey={journey} lang={lang} screen={screen} step={step}
              setStep={setStep} setScreen={setScreen} onApply={onApply}
              onAcceptOffer={async (id) => setJourney(await api.acceptOffer(userId, id, lang))}
              onReapply={async () => { const j = await api.reapply(userId, lang); setBanner(null); sync(j); }}
              onRestart={onReset} banner={banner} dismissBanner={() => setBanner(null)}
            />
          )}
        </section>

        {/* right: proof for the judges */}
        <section className="order-3 lg:col-span-2 xl:col-span-1 xl:h-[780px]">
          <TracePanel userId={userId} epoch={epoch} health={health} />
        </section>
      </main>

      <footer className="px-6 pb-4 text-center text-[11px] text-white/35">
        Raah by Team Alltra · Lender, bureau and Paytm data are mocked behind adapters · Rules engine, agent, voice and consent flow are real
      </footer>
    </div>
  );
}
