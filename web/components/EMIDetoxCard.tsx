"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  TrendingDown,
  Calendar,
  ShieldCheck,
  Zap,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  CreditCard,
  Building2,
  Lock,
  Layers,
  ArrowUpRight,
} from "lucide-react";
import {
  calculateEMIDetox,
  formatINR,
  EMIDetoxResult,
  MOCK_HIGH_INTEREST_EMIS,
  MOCK_STUDENT_OR_LIGHT_EMIS,
} from "@/lib/emi-logic";

interface EMIDetoxCardProps {
  customerName?: string;
  onConsolidationSuccess?: (result: EMIDetoxResult) => void;
  className?: string;
}

/**
 * EMIDetoxCard Component
 * 
 * Strict Paytm Light Theme:
 * - Pure White (#FFFFFF)
 * - Subtle 1px borders (#E2E8F0 / border-gray-200)
 * - Paytm Navy Blue (#002970) for primary headings & brand identity
 * - Paytm Sky Blue (#00BAF2) for interactive accents & highlights
 * - Vibrant Green (#00B67A / #059669) for verified savings
 * - High-Risk Amber/Rose (#E11D48 / #F43F5E) for predatory APRs
 */
export default function EMIDetoxCard({
  customerName = "Ravi",
  onConsolidationSuccess,
  className = "",
}: EMIDetoxCardProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [selectedPreset, setSelectedPreset] = useState<"standard" | "light">("standard");
  const [isConsolidating, setIsConsolidating] = useState<boolean>(false);
  const [isConsolidated, setIsConsolidated] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"comparison" | "cibil_impact">("comparison");

  const detoxData = calculateEMIDetox(
    selectedPreset === "standard" ? MOCK_HIGH_INTEREST_EMIS : MOCK_STUDENT_OR_LIGHT_EMIS
  );

  const handleConsolidate = async () => {
    setIsConsolidating(true);
    await new Promise((r) => setTimeout(r, 1600));
    setIsConsolidating(false);
    setIsConsolidated(true);
    onConsolidationSuccess?.(detoxData);
  };

  const handleReset = () => {
    setIsConsolidated(false);
    setIsConsolidating(false);
  };

  return (
    <div
      className={`w-full rounded-[24px] bg-white border border-slate-200 shadow-[0_12px_40px_rgba(0,41,112,0.06)] overflow-hidden transition-all ${className}`}
    >
      {/* Top Banner / Raah Smart Insight Header */}
      <div className="bg-gradient-to-r from-[#F0F8FF] via-white to-[#F5FAFF] border-b border-slate-100 px-5 py-4 sm:px-7 sm:py-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#002970] text-[#00BAF2] shadow-sm">
            <Zap size={20} className="fill-[#00BAF2]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-[#00BAF2]/10 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider text-[#0070A0]">
                <Sparkles size={12} className="text-[#00BAF2]" />
                Raah Smart Insight
              </span>
              <span className="hidden sm:inline-block h-1 w-1 rounded-full bg-slate-300" />
              <span className="text-[12px] font-semibold text-[#002970]/80">
                Proactive Debt Consolidation
              </span>
            </div>
            <h2 className="mt-0.5 font-display text-[18px] sm:text-[20px] font-bold tracking-tight text-[#002970]">
              The EMI Detox Agent
            </h2>
          </div>
        </div>

        {/* Right Header Controls */}
        <div className="flex items-center gap-2">
          {/* Preset Selector */}
          <div className="hidden md:flex items-center rounded-xl bg-slate-100/80 p-1 text-[12px] font-medium text-slate-600">
            <button
              onClick={() => {
                setSelectedPreset("standard");
                handleReset();
              }}
              className={`rounded-lg px-2.5 py-1 transition ${
                selectedPreset === "standard"
                  ? "bg-white text-[#002970] font-semibold shadow-xs"
                  : "hover:text-[#002970]"
              }`}
            >
              3 High-APR Loans
            </button>
            <button
              onClick={() => {
                setSelectedPreset("light");
                handleReset();
              }}
              className={`rounded-lg px-2.5 py-1 transition ${
                selectedPreset === "light"
                  ? "bg-white text-[#002970] font-semibold shadow-xs"
                  : "hover:text-[#002970]"
              }`}
            >
              2 BNPL Accounts
            </button>
          </div>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-[#002970] hover:bg-slate-50 transition shadow-xs"
          >
            {isExpanded ? (
              <>
                <ChevronUp size={14} /> Collapse
              </>
            ) : (
              <>
                <ChevronDown size={14} /> View Detox Plan
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.28, ease: "easeInOut" }}
            className="p-5 sm:p-7"
          >
            {/* Top Insight Alert Message */}
            <div className="mb-6 rounded-2xl bg-[#FFF5F5] border border-rose-200/80 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-slate-700">
              <div className="flex items-start gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-rose-500 text-white mt-0.5">
                  <AlertTriangle size={17} />
                </span>
                <div>
                  <p className="text-[13.5px] font-semibold text-[#991B1B] leading-snug">
                    Raah scanned your UPI mandates: You are paying{" "}
                    <b className="font-bold underline text-rose-900">
                      {formatINR(detoxData.totalCurrentMonthlyPayout)}/month
                    </b>{" "}
                    across {detoxData.totalLoansCount} separate apps at predatory rates (avg{" "}
                    {detoxData.weightedAverageInterestAPR}% APR).
                  </p>
                  <p className="mt-0.5 text-[12px] text-rose-700/80">
                    Multiple auto-debits on different dates increase late fee penalties and harm
                    your CIBIL score.
                  </p>
                </div>
              </div>
              <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-white px-3 py-1 text-[12px] font-bold text-rose-700 border border-rose-200 shadow-xs">
                3 Auto-Debits Active
              </span>
            </div>

            {/* If Already Consolidated: Celebration / Confirmed State */}
            {isConsolidated ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="rounded-3xl bg-gradient-to-b from-[#F0FDF4] to-white border-2 border-[#00B67A]/30 p-6 sm:p-8 text-center"
              >
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#00B67A] text-white shadow-lg shadow-[#00B67A]/30 mb-4">
                  <CheckCircle2 size={32} />
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#00B67A]/15 px-3 py-1 text-[12px] font-bold text-[#047857]">
                  <ShieldCheck size={14} /> Consolidation Active
                </span>
                <h3 className="mt-3 font-display text-[26px] font-bold text-[#002970] tracking-tight">
                  Congratulations, {customerName}! Your EMIs are Detoxed.
                </h3>
                <p className="mx-auto mt-2 max-w-lg text-[14.5px] text-slate-600 leading-relaxed">
                  Paytm has pre-approved and disbursed{" "}
                  <b>{formatINR(detoxData.totalOutstandingBalance)}</b> to pay off your{" "}
                  {detoxData.totalLoansCount} third-party loans. All old high-interest accounts are
                  being closed.
                </p>

                {/* Consolidated Stats Grid */}
                <div className="mt-6 mx-auto grid max-w-3xl grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="rounded-2xl bg-white border border-slate-200/90 p-4 shadow-xs">
                    <p className="text-[11px] font-semibold uppercase text-slate-400">
                      New Monthly EMI
                    </p>
                    <p className="mt-1 font-display text-[24px] font-bold text-[#002970]">
                      {formatINR(detoxData.paytmConsolidatedMonthlyEMI)}
                    </p>
                    <p className="mt-0.5 text-[11.5px] text-slate-500">
                      Auto-debited on 5th only
                    </p>
                  </div>
                  <div className="rounded-2xl bg-emerald-50 border border-emerald-200/80 p-4 shadow-xs">
                    <p className="text-[11px] font-semibold uppercase text-emerald-700">
                      Guaranteed Monthly Savings
                    </p>
                    <p className="mt-1 font-display text-[24px] font-bold text-[#00B67A]">
                      {formatINR(detoxData.monthlySavings)}
                    </p>
                    <p className="mt-0.5 text-[11.5px] text-emerald-800 font-medium">
                      {formatINR(detoxData.annualSavings)} saved per year
                    </p>
                  </div>
                  <div className="rounded-2xl bg-white border border-slate-200/90 p-4 shadow-xs">
                    <p className="text-[11px] font-semibold uppercase text-slate-400">
                      CIBIL Score Benefit
                    </p>
                    <p className="mt-1 font-display text-[24px] font-bold text-[#0070A0]">
                      +{detoxData.cibilBoostProjectionPoints} Pts
                    </p>
                    <p className="mt-0.5 text-[11.5px] text-slate-500">
                      Unsecured BNPLs closed
                    </p>
                  </div>
                </div>

                <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-4 py-2 text-[13px] font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    <RefreshCw size={13} /> Reset Simulation
                  </button>
                </div>
              </motion.div>
            ) : (
              /* The Comparative View (Chaos vs Paytm Solution) */
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
                {/* ----------------- LEFT SIDE: THE CHAOS (5 Cols) ----------------- */}
                <div className="lg:col-span-6 flex flex-col justify-between rounded-3xl bg-[#FBFBFC] border border-slate-200 p-5 sm:p-6">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-rose-100 text-rose-600 font-bold text-[12px]">
                            ✕
                          </span>
                          <h4 className="font-display text-[16px] font-bold text-[#002970]">
                            Current Fragmented EMIs
                          </h4>
                        </div>
                        <p className="mt-0.5 text-[11.5px] text-slate-500">
                          {detoxData.totalLoansCount} separate lenders · Fragmented due dates
                        </p>
                      </div>
                      <span className="rounded-full bg-rose-100 px-2.5 py-1 text-[11px] font-bold text-rose-700">
                        Avg {detoxData.weightedAverageInterestAPR}% APR
                      </span>
                    </div>

                    {/* Stack of Fragmented High-Interest Loans */}
                    <div className="mt-4 space-y-3">
                      {detoxData.existingLoans.map((loan) => (
                        <div
                          key={loan.id}
                          className="rounded-2xl bg-white border border-slate-200/90 p-3.5 shadow-2xs hover:border-rose-300 transition"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2.5">
                              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-[#002970] font-semibold text-[13px]">
                                <Building2 size={18} className="text-slate-600" />
                              </div>
                              <div>
                                <p className="font-display text-[14px] font-bold text-[#002970] leading-snug">
                                  {loan.lender}
                                </p>
                                <p className="text-[11px] text-slate-500">{loan.productName}</p>
                              </div>
                            </div>
                            <span className="rounded-full bg-rose-50 border border-rose-200/80 px-2 py-0.5 text-[11px] font-bold text-rose-700 shrink-0">
                              {loan.interestRateAPR}% APR
                            </span>
                          </div>

                          <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-[12px]">
                            <div className="flex items-center gap-1.5 text-slate-600">
                              <Calendar size={13} className="text-rose-500" />
                              <span>
                                Due on <b>{loan.dueDayOfMonth}th</b> every mo.
                              </span>
                            </div>
                            <div className="text-right">
                              <span className="font-display font-bold text-[#002970]">
                                {formatINR(loan.monthlyEMI)}
                              </span>
                              <span className="text-[10px] text-slate-400 block">/month</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Chaos Summary Footer */}
                  <div className="mt-5 rounded-2xl bg-rose-50/60 border border-rose-200/60 p-3.5 text-[12.5px] text-rose-900">
                    <div className="flex items-center justify-between font-bold">
                      <span>Total Current Monthly Outflow:</span>
                      <span className="font-display text-[16px] text-rose-700">
                        {formatINR(detoxData.totalCurrentMonthlyPayout)}/mo
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-rose-700/80">
                      Outstanding Principal: {formatINR(detoxData.totalOutstandingBalance)} · 3
                      separate NACH bounce penalties possible.
                    </p>
                  </div>
                </div>

                {/* ----------------- RIGHT SIDE: THE PAYTM SOLUTION (6 Cols) ----------------- */}
                <div className="lg:col-span-6 flex flex-col justify-between rounded-3xl bg-gradient-to-br from-[#F5FAFF] via-white to-[#EDF7FF] border-2 border-[#00BAF2]/40 p-5 sm:p-6 shadow-md relative overflow-hidden">
                  {/* Subtle Decorative Paytm Blue Glow */}
                  <div className="absolute -top-12 -right-12 h-40 w-40 rounded-full bg-[#00BAF2]/10 blur-2xl pointer-events-none" />

                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-[#00BAF2]/20">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#00BAF2] text-white font-bold text-[12px] shadow-xs">
                            ✓
                          </span>
                          <h4 className="font-display text-[16px] font-bold text-[#002970]">
                            The Paytm Solution
                          </h4>
                        </div>
                        <p className="mt-0.5 text-[11.5px] text-slate-500">
                          1 Consolidated Loan · 1 Low Interest Rate · 1 Date
                        </p>
                      </div>
                      <span className="rounded-full bg-[#00BAF2]/15 border border-[#00BAF2]/30 px-3 py-1 text-[11.5px] font-bold text-[#0070A0]">
                        14% APR Flat
                      </span>
                    </div>

                    {/* Bold Savings Card */}
                    <div className="mt-4 rounded-2xl bg-white border border-[#00BAF2]/30 p-5 shadow-sm text-center">
                      <p className="text-[12px] font-bold uppercase tracking-wider text-[#0070A0]">
                        Your Net Cash Savings
                      </p>
                      <motion.div
                        initial={{ scale: 0.95 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", stiffness: 400 }}
                        className="mt-1 flex items-baseline justify-center gap-1.5"
                      >
                        <span className="font-display text-[34px] sm:text-[40px] font-extrabold text-[#00B67A] tracking-tight">
                          Save {formatINR(detoxData.monthlySavings)}
                        </span>
                        <span className="text-[14px] font-semibold text-slate-500">/ month</span>
                      </motion.div>
                      <p className="mt-1 text-[12.5px] font-medium text-emerald-800">
                        🎉 That is <b>{formatINR(detoxData.annualSavings)}</b> extra in your pocket
                        every year!
                      </p>

                      {/* New EMI Comparison Pill */}
                      <div className="mt-4 grid grid-cols-2 gap-2 text-left bg-slate-50 rounded-xl p-3 border border-slate-100">
                        <div>
                          <p className="text-[10.5px] uppercase font-semibold text-slate-400">
                            New Single EMI
                          </p>
                          <p className="font-display text-[18px] font-bold text-[#002970]">
                            {formatINR(detoxData.paytmConsolidatedMonthlyEMI)}
                            <span className="text-[11px] font-normal text-slate-500">/mo</span>
                          </p>
                        </div>
                        <div className="border-l border-slate-200 pl-3">
                          <p className="text-[10.5px] uppercase font-semibold text-slate-400">
                            Single Auto-Debit
                          </p>
                          <p className="font-display text-[16px] font-bold text-[#0070A0] flex items-center gap-1">
                            <Calendar size={14} /> 5th of Month
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Key Strategic Benefits */}
                    <ul className="mt-4 space-y-2 text-[12.5px] text-[#002970]">
                      <li className="flex items-center gap-2">
                        <CheckCircle2 size={16} className="text-[#00BAF2] shrink-0" />
                        <span>
                          <b>Paytm Auto-Closes 3 Accounts:</b> Direct payoff to LazyPay, KreditBee &
                          HDFC.
                        </span>
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 size={16} className="text-[#00BAF2] shrink-0" />
                        <span>
                          <b>Zero Mental Friction:</b> Never worry about staggered 5th, 12th & 22nd
                          penalties.
                        </span>
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 size={16} className="text-[#00BAF2] shrink-0" />
                        <span>
                          <b>CIBIL Score Upgrade:</b> Closing multiple high-utilization short-term
                          lines boosts bureau standing.
                        </span>
                      </li>
                    </ul>
                  </div>

                  {/* Action Button with Spring Physics */}
                  <div className="mt-6 pt-3 border-t border-[#00BAF2]/20">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ type: "spring", stiffness: 400, damping: 15 }}
                      disabled={isConsolidating}
                      onClick={handleConsolidate}
                      className="w-full flex items-center justify-center gap-2.5 rounded-2xl bg-[#00BAF2] hover:bg-[#00A5D8] py-4 px-6 font-display text-[16px] font-bold text-[#002970] shadow-md shadow-[#00BAF2]/25 transition-colors disabled:opacity-75 cursor-pointer"
                    >
                      {isConsolidating ? (
                        <>
                          <RefreshCw size={18} className="animate-spin text-[#002970]" />
                          Refinancing 3 Loans with 1-Click Paytm...
                        </>
                      ) : (
                        <>
                          <Zap size={18} className="fill-[#002970]" />
                          Consolidate into 1-Click Paytm EMI
                          <ArrowRight size={17} />
                        </>
                      )}
                    </motion.button>
                    <p className="mt-2 text-center text-[11px] text-slate-500">
                      ⚡ Instant digital payoff · No paperwork · Powered by Paytm Lending Partner
                    </p>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
