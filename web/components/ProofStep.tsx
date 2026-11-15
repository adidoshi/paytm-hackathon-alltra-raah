"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  AlarmClock, ArrowRight, Banknote, Building2, Check, CircleAlert, HandCoins, Landmark, Lock, ReceiptText, ShieldCheck, ShoppingBag,
} from "lucide-react";
import { useEffect, useState } from "react";
import { inr, type Cashflow, type Lang } from "@/lib/api";
import { tr, type StringKey } from "@/lib/strings";

const ICON = {
  income: { I: Banknote, cls: "bg-good-soft text-good" },
  bills: { I: ReceiptText, cls: "bg-sky-soft text-brand" },
  hidden: { I: CircleAlert, cls: "bg-rust-soft text-rust" },
  borrowed: { I: HandCoins, cls: "bg-rust-soft text-rust" },
  timing: { I: AlarmClock, cls: "bg-rust-soft text-rust" },
  spend: { I: ShoppingBag, cls: "bg-paper text-mute" },
} as const;

const TICKER = [
  "UPI/CR/…/BUNDL TECH/ICIC/de payout",
  "ACH D- BAJAJ FINANCE LTD-P400…",
  "UPI/DR/…/LAXMI ENTERPRISES/…/hapta",
  "NEFT CR-…-CITIUSTECH LIMITED-SAL",
  "UPI/CR/…/SHAIKH TRADERS/…/pagaar",
  "UPI/DR/…/VITTHAL GAIKWAD/…/kholi bhade",
  "IMPS/P2A/…/ROPPEN TRANSPORTATION",
  "UPI/DR/…/SIMPL TECHNOLOGIES/…/bill",
];

type Props = {
  lang: Lang;
  cashflow: Cashflow | null;
  onRead: () => Promise<void>;
  onAnswer: (gap: string, answer: string) => Promise<void>;
  onNext: () => void;
};

export default function ProofStep({ lang, cashflow, onRead, onAnswer, onNext }: Props) {
  const t = (k: StringKey, params?: Record<string, string | number>) => tr(lang, k, params);
  const [reading, setReading] = useState(false);
  const [tick, setTick] = useState(0);
  const [answered, setAnswered] = useState(false);

  useEffect(() => {
    if (!reading) return;
    const id = setInterval(() => setTick((n) => n + 1), 260);
    return () => clearInterval(id);
  }, [reading]);

  async function share() {
    setReading(true);
    try {
      // Let the reading moment register even when the answer is served from cache.
      await Promise.all([onRead(), new Promise((r) => setTimeout(r, 2600))]);
    } finally {
      setReading(false);
    }
  }

  if (reading) {
    return (
      <div className="flex flex-col items-center px-2 pt-6 text-center">
        <div className="relative h-20 w-20">
          <motion.span
            className="absolute inset-0 rounded-full border-[5px] border-brand/15 border-t-brand"
            animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
          />
          <Landmark className="absolute inset-0 m-auto text-brand" size={28} />
        </div>
        <p className="mt-4 font-display text-[17px] font-semibold">{t("reading")}</p>
        <p className="text-[12.5px] text-mute">{t("reading_sub")}</p>
        <div className="mt-5 w-full space-y-1.5 overflow-hidden">
          {[0, 1, 2, 3].map((i) => (
            <motion.p
              key={`${tick}-${i}`} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1 - i * 0.22, x: 0 }}
              className="truncate rounded-lg bg-white px-3 py-1.5 text-left font-mono text-[10.5px] text-mute ring-1 ring-line"
            >
              {TICKER[(tick + i) % TICKER.length]}
            </motion.p>
          ))}
        </div>
      </div>
    );
  }

  if (!cashflow) {
    return (
      <div className="space-y-3">
        <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-line">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-soft text-brand"><Building2 size={23} /></span>
          <p className="mt-3 font-display text-[18px] font-semibold leading-snug">{t("proof_title")}</p>
          <p className="mt-1.5 text-[13.5px] leading-relaxed text-mute">{t("proof_body")}</p>
          <ul className="mt-3 space-y-2">
            {(["proof_b1", "proof_b2", "proof_b3"] as StringKey[]).map((k) => (
              <li key={k} className="flex items-start gap-2.5 text-[13px] text-ink">
                <Check size={15} className="mt-0.5 shrink-0 text-good" /> {t(k)}
              </li>
            ))}
          </ul>
          <motion.button
            whileTap={{ scale: 0.98 }} onClick={share}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-brand py-3.5 font-display text-[15px] font-semibold text-white shadow-lg shadow-brand/25"
          >
            <Lock size={16} /> {t("proof_btn")}
          </motion.button>
          <p className="mt-2 text-center text-[10.5px] text-mute">RBI Account Aggregator · consent logged</p>
        </div>
      </div>
    );
  }

  const max = Math.max(cashflow.verified_income, cashflow.keyword_income, 1);
  return (
    <div className="space-y-3">
      <h2 className="font-display text-[19px] font-semibold">{t("findings_title")}</h2>

      <div className="flex flex-wrap gap-1.5">
        {cashflow.sources.map((s) => (
          <span key={s.name} className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-ink/80 ring-1 ring-line">
            {s.name} · {s.rows}
          </span>
        ))}
      </div>

      <div className="space-y-2">
        {cashflow.findings.map((f, i) => {
          const { I, cls } = ICON[f.kind];
          return (
            <motion.div
              key={f.text} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.12 }}
              className="flex items-start gap-3 rounded-2xl bg-white p-3.5 shadow-sm ring-1 ring-line"
            >
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${cls}`}><I size={16} /></span>
              <span className="min-w-0">
                <span className="block text-[13.5px] font-medium leading-snug text-ink">{f.text}</span>
                {f.sub && <span className="mt-0.5 block text-[12px] leading-snug text-mute">{f.sub}</span>}
              </span>
            </motion.div>
          );
        })}
      </div>

      <AnimatePresence>
        {cashflow.gap && !answered && (
          <motion.div exit={{ opacity: 0, height: 0 }} className="rounded-2xl bg-navy p-4 text-white">
            <p className="text-[13.5px] leading-snug">{cashflow.gap.question}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {cashflow.gap.options.map((o) => (
                <button
                  key={o} onClick={async () => { setAnswered(true); await onAnswer(cashflow.gap!.id, o); }}
                  className="rounded-full bg-white/12 px-3 py-1.5 text-[12.5px] font-medium ring-1 ring-white/25 hover:bg-white/20"
                >
                  {o}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      {answered && <p className="text-center text-[12px] text-good">{t("answered")}</p>}

      <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-line">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-mute">{t("income_found")}</p>
        {[
          { label: t("raah_reader"), value: cashflow.verified_income, cls: "bg-good" },
          { label: t("keyword_rules"), value: cashflow.keyword_income, cls: "bg-line" },
        ].map((b) => (
          <div key={b.label} className="mt-2">
            <div className="flex justify-between text-[12px]">
              <span className="text-ink/80">{b.label}</span>
              <span className="font-display font-semibold">{inr(b.value)}</span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-paper">
              <motion.div className={`h-full rounded-full ${b.cls}`} initial={{ width: 0 }} animate={{ width: `${(b.value / max) * 100}%` }} transition={{ duration: 0.9 }} />
            </div>
          </div>
        ))}
        <p className="mt-3 flex items-center gap-1 text-[10.5px] text-mute">
          <ShieldCheck size={11} className="text-good" /> {t("read_by", { model: cashflow.model })}
        </p>
      </div>

      <motion.button
        whileTap={{ scale: 0.98 }} onClick={onNext}
        className="flex w-full items-center justify-center gap-2 rounded-2xl bg-brand py-3.5 font-display text-[15px] font-semibold text-white"
      >
        {t("see_today")} <ArrowRight size={17} />
      </motion.button>
    </div>
  );
}
