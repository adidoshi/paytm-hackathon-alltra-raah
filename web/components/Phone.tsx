"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight, BadgeCheck, Banknote, Bell, Check, ChevronLeft, CircleAlert, CreditCard, Landmark, Lock,
  Mic, QrCode, ReceiptText, Send, ShieldCheck, Smartphone, Sparkles, Square, Volume2, X, Zap,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, emi, inr, type ChatReply, type Journey, type Lang, type Persona } from "@/lib/api";
import { tr, type StringKey } from "@/lib/strings";
import { useRecorder, useSpeaker } from "@/lib/useVoice";

export type Screen = "home" | "apply" | "checking" | "rejected" | "raah" | "approved";

type Props = {
  persona: Persona;
  journey: Journey | null;
  lang: Lang;
  screen: Screen;
  step: number;
  setStep: (n: number) => void;
  setScreen: (s: Screen) => void;
  onApply: (amount: number, tenure: number) => void;
  onAcceptOffer: (id: string) => void;
  onReapply: () => Promise<void>;
  onRestart: () => void;
  banner: Journey["notifications"][number] | null;
  dismissBanner: () => void;
};

const slide = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.28 },
};

export function RaahMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="7" fill="#1565c0" />
      <path d="M6 18c0-5 3-6 6-7s5-2 5-5" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M13.6 5.2 17.2 5l.4 3.6" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Wave({ on, dark }: { on: boolean; dark?: boolean }) {
  return (
    <span className="flex h-4 items-center gap-[3px]" aria-hidden>
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className={`w-[3px] rounded-full ${dark ? "bg-white" : "bg-brand"} ${on ? "wave-bar h-4" : "h-1.5"}`}
          style={{ animationDelay: `${i * 0.12}s` }}
        />
      ))}
    </span>
  );
}

function Ring({ value, label }: { value: number; label: string }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative h-[88px] w-[88px] shrink-0">
      <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="7" />
        <motion.circle
          cx="40" cy="40" r={r} fill="none" stroke={value >= 100 ? "#5fe0a8" : "#7cb9f7"} strokeWidth="7" strokeLinecap="round"
          strokeDasharray={c}
          initial={false}
          animate={{ strokeDashoffset: c * (1 - value / 100) }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
        <span className="font-display text-[22px] font-bold leading-none">{value}%</span>
        <span className="mt-0.5 text-[10px] text-white/70">{label}</span>
      </div>
    </div>
  );
}

export default function Phone(p: Props) {
  const { persona, journey, lang, screen, step } = p;
  const t = (k: StringKey, params?: Record<string, string | number>) => tr(lang, k, params);
  const speaker = useSpeaker();
  const recorder = useRecorder();

  const [amount, setAmount] = useState(persona.application.amount);
  const [tenure, setTenure] = useState(persona.application.tenure_months);
  const [showHook, setShowHook] = useState(false);
  const [consentOpen, setConsentOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chat, setChat] = useState<{ who: "me" | "raah"; text: string; card?: "consent" | null; tools?: string[] }[]>([]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const chatEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setAmount(persona.application.amount);
    setTenure(persona.application.tenure_months);
    setChat([]);
    setChatOpen(false);
    setConsentOpen(false);
    speaker.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [persona.user_id]);

  useEffect(() => {
    if (screen !== "rejected") return setShowHook(false);
    const id = setTimeout(() => setShowHook(true), 1500);
    return () => clearTimeout(id);
  }, [screen]);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, thinking]);

  async function speak(text: string) {
    if (speaker.speaking) return speaker.stop();
    setLoadingAudio(true);
    try {
      const audio = await api.tts(persona.user_id, text, lang);
      speaker.play(audio, text, lang);
    } catch {
      speaker.play(null, text, lang); // browser voice when Sarvam is unreachable
    } finally {
      setLoadingAudio(false);
    }
  }

  function enterRaah() {
    p.setScreen("raah");
    p.setStep(0);
    if (journey?.explanation) void speak(journey.explanation.text);
  }

  function handleReply(r: ChatReply, spoken: boolean) {
    setChat((c) => [...c, { who: "raah", text: r.reply, card: r.card, tools: r.tools }]);
    if (spoken) speaker.play(r.audio, r.reply, r.lang);
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || thinking) return;
    setDraft("");
    setChatOpen(true);
    setChat((c) => [...c, { who: "me", text: q }]);
    setThinking(true);
    try {
      handleReply(await api.chat(persona.user_id, q, lang, false), false);
    } catch (e) {
      setChat((c) => [...c, { who: "raah", text: String((e as Error).message) }]);
    } finally {
      setThinking(false);
    }
  }

  async function toggleMic() {
    if (!recorder.recording) {
      speaker.stop();
      try {
        await recorder.start();
        setChatOpen(true);
      } catch {
        setChatOpen(true);
        setChat((c) => [...c, { who: "raah", text: t("voice_off") }]);
      }
      return;
    }
    const blob = await recorder.stop();
    if (!blob) return;
    setThinking(true);
    try {
      const r = await api.voiceAsk(persona.user_id, lang, blob);
      setChat((c) => [...c, { who: "me", text: r.transcript ?? "…" }]);
      handleReply(r, true);
    } catch {
      setChat((c) => [...c, { who: "raah", text: t("voice_off") }]);
    } finally {
      setThinking(false);
    }
  }

  async function agree() {
    setSubmitting(true);
    try {
      await p.onReapply();
      setConsentOpen(false);
      setChatOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  const estEmi = emi(amount, 0.18, tenure);
  const steps: StringKey[] = ["step_why", "step_today", "step_plan", "step_reapply"];
  const eligible = journey?.status === "eligible";

  return (
    <div className="relative mx-auto h-[780px] w-[384px] max-w-full shrink-0 text-ink rounded-[46px] border-[10px] border-[#05090f] bg-paper shadow-[0_40px_80px_-20px_rgba(0,0,0,0.7),0_0_0_1.5px_rgba(124,185,247,0.25)]">
      <div className="absolute left-1/2 top-2 z-30 h-6 w-28 -translate-x-1/2 rounded-full bg-[#05090f]" />
      <div className="relative flex h-full flex-col overflow-hidden rounded-[36px] bg-paper">
        {/* status bar */}
        <div className={`flex h-10 shrink-0 items-end justify-between px-7 pb-1 text-[11px] font-semibold ${screen === "raah" || screen === "approved" ? "bg-navy text-white" : "text-ink"}`}>
          <span>9:41</span>
          <span className="tracking-wide">5G ▪ 86%</span>
        </div>

        {/* nudge banner */}
        <AnimatePresence>
          {p.banner && screen === "raah" && (
            <motion.button
              initial={{ y: -90, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -90, opacity: 0 }}
              transition={{ type: "spring", stiffness: 260, damping: 24 }}
              onClick={() => { p.dismissBanner(); if (p.banner?.kind === "eligible") p.setStep(3); }}
              className="absolute inset-x-3 top-11 z-40 flex items-start gap-3 rounded-2xl bg-white/95 p-3 text-left shadow-xl ring-1 ring-black/5 backdrop-blur"
            >
              <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${p.banner.kind === "eligible" ? "bg-good text-white" : "bg-brand text-white"}`}>
                {p.banner.kind === "eligible" ? <BadgeCheck size={17} /> : <Bell size={16} />}
              </span>
              <span className="min-w-0">
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-mute">Raah · now</span>
                <span className="block text-[13px] font-semibold leading-snug text-ink">{p.banner.title}</span>
                <span className="block text-[12px] leading-snug text-mute">{p.banner.body}</span>
              </span>
            </motion.button>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          {/* ------------------------------------------------ home */}
          {screen === "home" && (
            <motion.div key="home" {...slide} className="flex flex-1 flex-col overflow-y-auto no-scrollbar">
              <div className="bg-gradient-to-b from-brand to-brand-dark px-5 pb-7 pt-3 text-white">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-display text-xl font-semibold">{t("hi", { name: persona.first_name })}</p>
                    <p className="text-[13px] text-white/75">{t("home_sub")}</p>
                  </div>
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/15 font-display font-semibold">
                    {persona.first_name[0]}
                  </span>
                </div>
                <div className="mt-5 grid grid-cols-4 gap-2 text-center text-[11px]">
                  {[[QrCode, "Scan & Pay"], [Smartphone, "To Mobile"], [Landmark, "To Bank"], [ReceiptText, "Bills"]].map(([Icon, label]) => {
                    const I = Icon as typeof QrCode;
                    return (
                      <div key={label as string} className="flex flex-col items-center gap-1.5">
                        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15"><I size={19} /></span>
                        {label as string}
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="-mt-4 flex-1 space-y-3 rounded-t-3xl bg-paper px-4 pt-5">
                <p className="px-1 text-[11px] font-semibold uppercase tracking-wider text-mute">Loans & Credit</p>
                <motion.button
                  whileTap={{ scale: 0.98 }}
                  onClick={() => p.setScreen("apply")}
                  className="flex w-full items-center gap-3 rounded-2xl bg-white p-4 text-left shadow-sm ring-2 ring-brand/70"
                >
                  <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-soft text-brand"><Banknote size={22} /></span>
                  <span className="flex-1">
                    <span className="block font-display text-[15px] font-semibold">{t("loan_tile")}</span>
                    <span className="block text-[12px] text-mute">{t("loan_tile_sub")}</span>
                  </span>
                  <ArrowRight size={18} className="text-brand" />
                </motion.button>
                <div className="grid grid-cols-2 gap-3">
                  {[[CreditCard, "Credit Card"], [ShieldCheck, "Insurance"], [Zap, "UPI AutoPay"], [Landmark, "Fixed Deposit"]].map(([Icon, label]) => {
                    const I = Icon as typeof QrCode;
                    return (
                      <div key={label as string} className="flex items-center gap-2.5 rounded-2xl bg-white p-3 text-[13px] font-medium text-ink/80 shadow-sm">
                        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-paper text-mute"><I size={17} /></span>
                        {label as string}
                      </div>
                    );
                  })}
                </div>
              </div>
            </motion.div>
          )}

          {/* ------------------------------------------------ apply */}
          {screen === "apply" && (
            <motion.div key="apply" {...slide} className="flex flex-1 flex-col px-5 pb-5">
              <button onClick={() => p.setScreen("home")} className="flex items-center gap-1 py-2 text-[13px] text-mute">
                <ChevronLeft size={16} /> {t("apply_title")}
              </button>
              <div className="mt-2 rounded-3xl bg-white p-5 shadow-sm">
                <p className="text-[12px] font-medium text-mute">{t("amount")}</p>
                <p className="font-display text-[34px] font-bold tracking-tight text-ink">{inr(amount)}</p>
                <input
                  type="range" min={25000} max={500000} step={25000} value={amount}
                  onChange={(e) => setAmount(Number(e.target.value))} className="mt-2 w-full" aria-label={t("amount")}
                />
                <div className="flex justify-between text-[11px] text-mute"><span>{inr(25000)}</span><span>{inr(500000)}</span></div>
                <p className="mt-5 text-[12px] font-medium text-mute">{t("tenure")}</p>
                <div className="mt-2 grid grid-cols-4 gap-2">
                  {[12, 24, 36, 48].map((m) => (
                    <button
                      key={m} onClick={() => setTenure(m)}
                      className={`rounded-xl py-2 text-[13px] font-semibold transition ${tenure === m ? "bg-brand text-white" : "bg-paper text-ink/70"}`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
                <p className="mt-1 text-right text-[11px] text-mute">{t("months")}</p>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <p className="text-[11px] text-mute">{t("income")}</p>
                  <p className="font-display text-lg font-semibold">{inr(persona.monthly_income)}</p>
                </div>
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <p className="text-[11px] text-mute">{t("emi_est")}</p>
                  <p className="font-display text-lg font-semibold">{inr(estEmi)}</p>
                </div>
              </div>
              <div className="flex-1" />
              <motion.button
                whileTap={{ scale: 0.98 }} onClick={() => p.onApply(amount, tenure)}
                className="rounded-2xl bg-brand py-4 font-display text-[16px] font-semibold text-white shadow-lg shadow-brand/30"
              >
                {t("apply_btn")}
              </motion.button>
            </motion.div>
          )}

          {/* ------------------------------------------------ checking */}
          {screen === "checking" && (
            <motion.div key="checking" {...slide} className="flex flex-1 flex-col items-center justify-center gap-5 px-8 text-center">
              <div className="relative h-20 w-20">
                <motion.span
                  className="absolute inset-0 rounded-full border-[5px] border-brand/15 border-t-brand"
                  animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                />
                <Landmark className="absolute inset-0 m-auto text-brand" size={28} />
              </div>
              <div>
                <p className="font-display text-lg font-semibold">{t("checking")}</p>
                <p className="text-[13px] text-mute">{t("checking_sub")}</p>
              </div>
            </motion.div>
          )}

          {/* ------------------------------------------------ rejected (today's dead end) */}
          {screen === "rejected" && journey && (
            <motion.div key="rejected" {...slide} className="relative flex flex-1 flex-col px-5 pb-5">
              <div className="flex flex-1 flex-col items-center justify-center text-center">
                <motion.span
                  initial={{ scale: 0.6 }} animate={{ scale: 1 }}
                  className="flex h-16 w-16 items-center justify-center rounded-full bg-rust-soft text-rust"
                >
                  <CircleAlert size={30} />
                </motion.span>
                <p className="mt-4 font-display text-xl font-semibold">{t("rejected_title")}</p>
                <p className="mt-2 max-w-[260px] text-[13px] leading-relaxed text-mute">{t("rejected_body")}</p>
                <p className="mt-3 rounded-full bg-black/5 px-3 py-1 font-mono text-[11px] text-mute">Ref {journey.application.reference}</p>
                <motion.p
                  initial={{ opacity: 0 }} animate={{ opacity: showHook ? 0 : 1 }} transition={{ delay: 0.5 }}
                  className="mt-8 text-[12px] italic text-mute/80"
                >
                  {t("rejected_today")}
                </motion.p>
              </div>
              <AnimatePresence>
                {showHook && (
                  <motion.div
                    initial={{ y: 220, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
                    transition={{ type: "spring", stiffness: 170, damping: 20 }}
                    className="rounded-3xl bg-navy p-5 text-white shadow-2xl"
                  >
                    <div className="flex items-center gap-2 text-[12px] font-semibold text-sky">
                      <RaahMark size={20} /> Raah
                    </div>
                    <p className="mt-3 font-display text-[24px] font-bold leading-tight">{t("hook_title")}</p>
                    <p className="mt-1 text-[14px] leading-snug text-white/75">{t("hook_body")}</p>
                    <motion.button
                      whileTap={{ scale: 0.98 }} onClick={enterRaah}
                      className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-sky py-3.5 font-display text-[15px] font-semibold text-navy"
                    >
                      {t("hook_btn")} <ArrowRight size={17} />
                    </motion.button>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* ------------------------------------------------ raah journey */}
          {screen === "raah" && journey && (
            <motion.div key="raah" {...slide} className="flex min-h-0 flex-1 flex-col">
              <div className="shrink-0 bg-navy px-4 pb-3 text-white">
                <div className="flex items-center justify-between py-1.5">
                  <span className="flex items-center gap-2 font-display text-[17px] font-semibold"><RaahMark /> Raah</span>
                  <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-white/80">
                    {inr(journey.application.amount)} · Day {journey.day}
                  </span>
                </div>
                <div className="mt-2 grid grid-cols-4 gap-1.5">
                  {steps.map((k, i) => {
                    const complete = i === 3 ? journey.status === "approved" : i < step;
                    return (
                      <button key={k} onClick={() => p.setStep(i)} className="group text-left">
                        <span className={`block h-1 rounded-full transition-colors ${i === step ? "bg-sky" : complete ? "bg-sky/50" : "bg-white/15"}`} />
                        <span className={`mt-1.5 flex items-center gap-1 text-[11px] font-medium ${i === step ? "text-white" : "text-white/55"}`}>
                          {i === 3 && eligible && <span className="h-1.5 w-1.5 rounded-full bg-[#5fe0a8]" />}
                          {t(k)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto no-scrollbar px-4 pb-4 pt-4">
                <AnimatePresence mode="wait">
                  {step === 0 && (
                    <motion.div key="why" {...slide} className="space-y-3">
                      <h2 className="font-display text-[19px] font-semibold">{t("why_title")}</h2>
                      {journey.explanation && (
                        <div className="rounded-3xl bg-white p-4 shadow-sm ring-1 ring-line">
                          <p className="text-[14.5px] leading-relaxed text-ink">{journey.explanation.text}</p>
                          <button
                            onClick={() => speak(journey.explanation!.text)}
                            className="mt-3 flex items-center gap-2.5 rounded-full bg-sky-soft py-2 pl-3 pr-4 text-[13px] font-semibold text-brand"
                          >
                            {speaker.speaking ? <Square size={14} fill="currentColor" /> : <Volume2 size={16} />}
                            {loadingAudio ? "…" : speaker.speaking ? t("stop") : t("listen")}
                            <Wave on={speaker.speaking} />
                          </button>
                        </div>
                      )}
                      {journey.reasons.map((r) => (
                        <div key={r.code} className={`rounded-2xl border-l-4 bg-white p-4 shadow-sm ${r.resolved ? "border-good" : "border-amber"}`}>
                          <div className="flex items-start justify-between gap-2">
                            <p className="font-display text-[15px] font-semibold leading-snug">{r.title}</p>
                            {r.resolved && (
                              <span className="flex shrink-0 items-center gap-1 rounded-full bg-good-soft px-2 py-0.5 text-[11px] font-semibold text-good">
                                <Check size={12} /> {t("fixed")}
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-[13px] leading-relaxed text-mute">{r.detail}</p>
                        </div>
                      ))}
                    </motion.div>
                  )}

                  {step === 1 && (
                    <motion.div key="today" {...slide} className="space-y-3">
                      <h2 className="font-display text-[19px] font-semibold">{t("today_title")}</h2>
                      {journey.offers.length === 0 && <p className="rounded-2xl bg-white p-4 text-[13px] text-mute shadow-sm">{t("today_none")}</p>}
                      {journey.offers.map((o) => (
                        <div key={o.id} className="overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-line">
                          <div className="bg-gradient-to-br from-brand to-navy-3 p-4 text-white">
                            <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2 py-0.5 text-[11px] font-medium">
                              <ShieldCheck size={12} /> {t("verified")}
                            </span>
                            <p className="mt-2 font-display text-[19px] font-semibold leading-tight">{o.name}</p>
                            <p className="text-[13px] text-white/75">{o.tagline}</p>
                          </div>
                          <div className="p-4">
                            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                              {o.facts.map(([k, v]) => (
                                <div key={k}>
                                  <p className="text-[11px] text-mute">{k}</p>
                                  <p className="font-display text-[15px] font-semibold">{v}</p>
                                </div>
                              ))}
                            </div>
                            <p className="mt-3 text-[13px] leading-relaxed text-mute">{o.why}</p>
                            <motion.button
                              whileTap={{ scale: 0.98 }} disabled={o.accepted} onClick={() => p.onAcceptOffer(o.id)}
                              className={`mt-3 flex w-full items-center justify-center gap-2 rounded-2xl py-3 text-[14px] font-semibold ${o.accepted ? "bg-good-soft text-good" : "bg-brand text-white"}`}
                            >
                              {o.accepted ? <><Check size={16} /> {t("started")}</> : t("start_btn")}
                            </motion.button>
                          </div>
                        </div>
                      ))}
                    </motion.div>
                  )}

                  {step === 2 && (
                    <motion.div key="plan" {...slide} className="space-y-3">
                      <div className="flex items-center gap-4 rounded-3xl bg-navy p-4 text-white">
                        <Ring value={journey.plan.readiness} label={t("ready")} />
                        <div className="min-w-0">
                          <p className="font-display text-[17px] font-semibold leading-tight">{t("plan_title")}</p>
                          <p className="mt-0.5 text-[12px] leading-snug text-white/65">{t("plan_sub")}</p>
                          <div className="mt-2.5 flex items-center gap-1">
                            {[0, 30, 60, 90].map((d, i) => (
                              <span key={d} className="flex items-center gap-1">
                                {i > 0 && <span className={`h-0.5 w-5 rounded ${journey.day >= d ? "bg-sky" : "bg-white/20"}`} />}
                                <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${journey.day >= d ? "bg-sky text-navy" : "bg-white/10 text-white/60"}`}>{d}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                      {journey.plan.actions.map((a) => (
                        <motion.div layout key={a.id} className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-line">
                          <div className="flex items-start gap-3">
                            <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${a.done ? "bg-good text-white" : "border-2 border-line"}`}>
                              {a.done && <Check size={14} />}
                            </span>
                            <div className="min-w-0 flex-1">
                              <p className="font-display text-[14.5px] font-semibold leading-snug">{a.title}</p>
                              <p className="mt-0.5 text-[12.5px] leading-relaxed text-mute">{a.detail}</p>
                              <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-paper">
                                <motion.div
                                  className={`h-full rounded-full ${a.done ? "bg-good" : "bg-brand"}`}
                                  initial={false} animate={{ width: `${Math.max(a.progress * 100, a.done ? 100 : 3)}%` }}
                                  transition={{ duration: 0.8 }}
                                />
                              </div>
                              <div className="mt-1.5 flex items-center justify-between text-[11px] text-mute">
                                {a.binary ? <span /> : <span>{t("now")} <b className="text-ink">{a.current}</b> · {t("target")} <b className="text-ink">{a.target}</b></span>}
                                <span className={a.done ? "font-semibold text-good" : ""}>{a.done ? t("done") : t("by_day", { day: a.due_day })}</span>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  )}

                  {step === 3 && (
                    <motion.div key="reapply" {...slide} className="space-y-3">
                      <h2 className="font-display text-[19px] font-semibold">{t("reapply_title")}</h2>
                      <div className={`rounded-3xl p-5 ${eligible ? "bg-good-soft ring-1 ring-good/30" : "bg-white ring-1 ring-line"}`}>
                        <span className={`flex h-12 w-12 items-center justify-center rounded-2xl ${eligible ? "bg-good text-white" : "bg-paper text-mute"}`}>
                          {eligible ? <BadgeCheck size={24} /> : <Lock size={21} />}
                        </span>
                        <p className="mt-3 text-[14.5px] leading-relaxed text-ink">{eligible ? t("reapply_ready") : t("reapply_locked")}</p>
                        <div className="mt-3 space-y-1.5">
                          {journey.reasons.map((r) => (
                            <div key={r.code} className="flex items-center gap-2 text-[13px]">
                              <span className={`flex h-4.5 w-4.5 items-center justify-center rounded-full ${r.resolved ? "bg-good text-white" : "bg-amber/25 text-rust"}`}>
                                {r.resolved ? <Check size={11} /> : <X size={11} />}
                              </span>
                              <span className={r.resolved ? "text-mute line-through" : "text-ink"}>{r.title}</span>
                            </div>
                          ))}
                        </div>
                        <motion.button
                          whileTap={{ scale: 0.98 }} disabled={!eligible} onClick={() => setConsentOpen(true)}
                          className={`mt-4 w-full rounded-2xl py-3.5 font-display text-[15px] font-semibold ${eligible ? "bg-good text-white shadow-lg shadow-good/30" : "bg-paper text-mute"}`}
                        >
                          {t("reapply_btn")}
                        </motion.button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* chat sheet */}
              <AnimatePresence>
                {chatOpen && (
                  <motion.div
                    initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }} transition={{ type: "spring", stiffness: 260, damping: 30 }}
                    className="absolute inset-x-0 bottom-[68px] top-[150px] z-20 flex flex-col rounded-t-3xl bg-white shadow-[0_-12px_40px_rgba(0,0,0,0.18)]"
                  >
                    <div className="flex items-center justify-between px-4 py-3">
                      <span className="flex items-center gap-2 text-[13px] font-semibold"><Sparkles size={15} className="text-brand" /> Ask Raah</span>
                      <button onClick={() => { setChatOpen(false); speaker.stop(); }} aria-label="Close" className="rounded-full bg-paper p-1.5 text-mute"><X size={15} /></button>
                    </div>
                    <div className="flex-1 space-y-2.5 overflow-y-auto no-scrollbar px-4 pb-3">
                      {chat.map((m, i) => (
                        <div key={i} className={`flex ${m.who === "me" ? "justify-end" : "justify-start"}`}>
                          <div className={`max-w-[86%] rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed ${m.who === "me" ? "rounded-br-md bg-brand text-white" : "rounded-bl-md bg-paper text-ink"}`}>
                            {m.text}
                            {m.card === "consent" && (
                              <button onClick={() => setConsentOpen(true)} className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-xl bg-good py-2 text-[13px] font-semibold text-white">
                                <Lock size={13} /> {t("reapply_btn")}
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                      {(thinking || recorder.recording) && (
                        <div className="flex items-center gap-2 text-[12.5px] text-mute">
                          <Wave on /> {recorder.recording ? t("listening") : t("thinking")}
                        </div>
                      )}
                      <div ref={chatEnd} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ask bar */}
              <div className="z-30 flex shrink-0 items-center gap-2 border-t border-line bg-white px-3 py-3">
                <form onSubmit={(e) => { e.preventDefault(); void send(draft); }} className="flex flex-1 items-center rounded-full bg-paper pl-4 pr-1.5">
                  <input
                    value={draft} onChange={(e) => setDraft(e.target.value)} onFocus={() => chat.length && setChatOpen(true)}
                    placeholder={t("ask")} className="h-11 min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-mute/70"
                  />
                  {draft.trim() && (
                    <button type="submit" aria-label="Send" className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white"><Send size={14} /></button>
                  )}
                </form>
                <motion.button
                  whileTap={{ scale: 0.92 }} onClick={toggleMic} aria-label="Ask by voice"
                  animate={recorder.recording ? { boxShadow: ["0 0 0 0 rgba(184,81,11,0.5)", "0 0 0 12px rgba(184,81,11,0)"] } : { boxShadow: "0 0 0 0 rgba(0,0,0,0)" }}
                  transition={recorder.recording ? { repeat: Infinity, duration: 1.1 } : {}}
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white ${recorder.recording ? "bg-rust" : "bg-brand"}`}
                >
                  {recorder.recording ? <Square size={15} fill="currentColor" /> : <Mic size={19} />}
                </motion.button>
              </div>

              {/* consent sheet */}
              <AnimatePresence>
                {consentOpen && (
                  <>
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setConsentOpen(false)} className="absolute inset-0 z-40 bg-navy/60" />
                    <motion.div
                      initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }} transition={{ type: "spring", stiffness: 240, damping: 28 }}
                      className="absolute inset-x-0 bottom-0 z-50 rounded-t-[28px] bg-white p-5 pb-6"
                    >
                      <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-line" />
                      <div className="flex items-center gap-2.5">
                        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-soft text-brand"><Lock size={19} /></span>
                        <p className="font-display text-[19px] font-semibold">{t("consent_title")}</p>
                      </div>
                      <p className="mt-3 text-[14px] leading-relaxed text-ink">{t("consent_body", { amount: inr(journey.application.amount) })}</p>
                      <ul className="mt-3 space-y-2">
                        {(["consent_1", "consent_2", "consent_3"] as StringKey[]).map((k) => (
                          <li key={k} className="flex items-start gap-2.5 text-[13.5px] text-ink">
                            <Check size={16} className="mt-0.5 shrink-0 text-good" /> {t(k)}
                          </li>
                        ))}
                      </ul>
                      <motion.button
                        whileTap={{ scale: 0.98 }} disabled={submitting} onClick={agree}
                        className="mt-5 w-full rounded-2xl bg-good py-4 font-display text-[16px] font-semibold text-white shadow-lg shadow-good/30 disabled:opacity-70"
                      >
                        {submitting ? t("checking") : t("consent_agree")}
                      </motion.button>
                      <button onClick={() => setConsentOpen(false)} className="mt-2 w-full py-2 text-[13px] font-medium text-mute">{t("cancel")}</button>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* ------------------------------------------------ approved */}
          {screen === "approved" && journey && (
            <motion.div key="approved" {...slide} className="relative flex flex-1 flex-col items-center justify-center overflow-hidden bg-navy px-7 text-center text-white">
              {Array.from({ length: 36 }).map((_, i) => (
                <span
                  key={i} className="confetti absolute top-[-12px] h-2.5 w-1.5 rounded-sm"
                  style={{
                    left: `${(i * 53) % 100}%`,
                    background: ["#7cb9f7", "#5fe0a8", "#f39a3d", "#ffffff"][i % 4],
                    animationDelay: `${(i % 9) * 0.12}s`,
                    ["--dx" as string]: `${((i * 37) % 80) - 40}px`,
                  }}
                />
              ))}
              <motion.span
                initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 200, damping: 12, delay: 0.15 }}
                className="flex h-24 w-24 items-center justify-center rounded-full bg-[#5fe0a8] text-navy shadow-[0_0_60px_rgba(95,224,168,0.5)]"
              >
                <Check size={48} strokeWidth={3} />
              </motion.span>
              <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="mt-6 font-display text-[34px] font-bold">
                {t("approved_title")}
              </motion.p>
              <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }} className="mt-2 text-[15px] leading-relaxed text-white/80">
                {journey.status === "approved_direct"
                  ? t("approved_direct", { amount: inr(journey.application.amount) })
                  : t("approved_body", { amount: inr(journey.application.amount), day: journey.day })}
              </motion.p>
              {journey.status === "approved" && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9 }} className="mt-6 flex items-center gap-2 text-[13px]">
                  <span className="rounded-full border border-amber/60 px-3 py-1 text-amber line-through decoration-amber/60">{t("rejected_title")}</span>
                  <ArrowRight size={16} className="text-sky" />
                  <span className="rounded-full bg-sky px-3 py-1 font-semibold text-navy">{t("approved_title")}</span>
                </motion.div>
              )}
              <button onClick={p.onRestart} className="mt-10 rounded-full bg-white/10 px-5 py-2.5 text-[13px] font-medium text-white/85">{t("again")}</button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
