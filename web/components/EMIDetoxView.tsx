"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  Calendar,
  ShieldCheck,
  Zap,
  TrendingDown,
  Building2,
  RefreshCw,
  Sparkles,
  ArrowRight,
  TrendingUp,
  CreditCard,
  Briefcase,
  Layers,
  Award,
  DollarSign,
  HeartHandshake,
  Plus,
  Trash2,
  X,
  RotateCcw,
  FileText,
} from "lucide-react";
import {
  EMI_DETOX_USERS,
  EMIDetoxUser,
  ExistingLoanItem,
  CalculatedDetoxMath,
  calculateDetoxMetrics,
  formatINR,
} from "@/lib/mockData";
import type { DetoxAIAnalysis } from "@/app/api/emi-detox/analyze/route";

interface EMIDetoxViewProps {
  initialUserId?: string;
  onConsolidationComplete?: (user: EMIDetoxUser, math: CalculatedDetoxMath) => void;
}

export default function EMIDetoxView({
  initialUserId = "ravi",
  onConsolidationComplete,
}: EMIDetoxViewProps) {
  const [selectedUserId, setSelectedUserId] = useState<string>(initialUserId);
  const [tenure, setTenure] = useState<number>(12);
  const [isConsolidating, setIsConsolidating] = useState<boolean>(false);
  const [isConsolidated, setIsConsolidated] = useState<boolean>(false);

  // Dynamic loan portfolios per user (allows adding unlisted loans)
  const [userLoansMap, setUserLoansMap] = useState<Record<string, ExistingLoanItem[]>>(() => {
    const map: Record<string, ExistingLoanItem[]> = {};
    Object.values(EMI_DETOX_USERS).forEach((u) => {
      map[u.userId] = [...u.currentEMIs];
    });
    return map;
  });

  // Modal state for adding custom unlisted loan
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [modalForm, setModalForm] = useState({
    lenderName: "",
    accountNumber: "",
    loanType: "Instant Loan" as ExistingLoanItem["loanType"],
    outstandingAmount: "",
    monthlyEMI: "",
    interestRate: "32",
    dueDayOfMonth: "15",
    penalties: "₹500 bounce charge + 3% monthly penal interest",
  });

  // Live LLM state
  const [aiAnalysis, setAiAnalysis] = useState<DetoxAIAnalysis | null>(null);
  const [isLoadingAI, setIsLoadingAI] = useState<boolean>(false);

  const baseUser: EMIDetoxUser =
    EMI_DETOX_USERS[selectedUserId] || EMI_DETOX_USERS.ravi;
  const currentLoans: ExistingLoanItem[] =
    userLoansMap[selectedUserId] || baseUser.currentEMIs;
  const currentUser: EMIDetoxUser = {
    ...baseUser,
    currentEMIs: currentLoans,
  };

  // 1. Math Calculation (DONE IN TYPESCRIPT, NEVER HALLUCINATED)
  const math: CalculatedDetoxMath = calculateDetoxMetrics(currentUser, 14.0, tenure);

  // 2. Fetch Live LLM Analysis for this user's profile
  const fetchAIAnalysis = useCallback(async (user: EMIDetoxUser, mathData: CalculatedDetoxMath) => {
    setIsLoadingAI(true);
    try {
      const res = await fetch("/api/emi-detox/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user, math: mathData }),
      });
      if (res.ok) {
        const data: DetoxAIAnalysis = await res.json();
        setAiAnalysis(data);
      }
    } catch (e) {
      console.warn("[EMIDetoxView] Failed to fetch LLM analysis:", e);
    } finally {
      setIsLoadingAI(false);
    }
  }, []);

  useEffect(() => {
    setIsConsolidated(false);
    void fetchAIAnalysis(currentUser, math);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedUserId, currentLoans.length]);

  const handleConsolidateAction = async () => {
    setIsConsolidating(true);
    await new Promise((r) => setTimeout(r, 1500));
    setIsConsolidating(false);
    setIsConsolidated(true);
    onConsolidationComplete?.(currentUser, math);
  };

  const handleAddLoanSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalForm.lenderName.trim()) return;

    const outstanding = Math.max(1000, Number(modalForm.outstandingAmount) || 25000);
    const emi = Math.max(100, Number(modalForm.monthlyEMI) || Math.round(outstanding / 8));
    const apr = Math.max(1, Math.min(60, Number(modalForm.interestRate) || 30));
    const dueDay = Math.min(31, Math.max(1, Number(modalForm.dueDayOfMonth) || 15));

    const newLoanItem: ExistingLoanItem = {
      id: `manual-${Date.now()}`,
      lenderName: modalForm.lenderName.trim(),
      accountNumber:
        modalForm.accountNumber.trim() || `LN-${Math.floor(1000 + Math.random() * 9000)}`,
      loanType: modalForm.loanType,
      outstandingAmount: outstanding,
      monthlyEMI: emi,
      interestRate: apr,
      dueDayOfMonth: dueDay,
      tenureRemainingMonths: 12,
      penalties: modalForm.penalties.trim() || "Standard late charges apply",
      riskCategory: apr >= 30 ? "critical" : apr >= 20 ? "high" : "moderate",
      isManual: true,
    };

    const updatedLoans = [...currentLoans, newLoanItem];
    setUserLoansMap((prev) => ({
      ...prev,
      [selectedUserId]: updatedLoans,
    }));

    setIsAddModalOpen(false);
    setModalForm({
      lenderName: "",
      accountNumber: "",
      loanType: "Instant Loan",
      outstandingAmount: "",
      monthlyEMI: "",
      interestRate: "32",
      dueDayOfMonth: "15",
      penalties: "₹500 bounce charge + 3% monthly penal interest",
    });

    const updatedUser: EMIDetoxUser = { ...currentUser, currentEMIs: updatedLoans };
    const updatedMath = calculateDetoxMetrics(updatedUser, 14.0, tenure);
    void fetchAIAnalysis(updatedUser, updatedMath);
  };

  const handleRemoveLoan = (loanId: string) => {
    const updatedLoans = currentLoans.filter((l) => l.id !== loanId);
    setUserLoansMap((prev) => ({
      ...prev,
      [selectedUserId]: updatedLoans,
    }));
    const updatedUser: EMIDetoxUser = { ...currentUser, currentEMIs: updatedLoans };
    const updatedMath = calculateDetoxMetrics(updatedUser, 14.0, tenure);
    void fetchAIAnalysis(updatedUser, updatedMath);
  };

  const handleResetLoans = () => {
    const defaultLoans = baseUser.currentEMIs;
    setUserLoansMap((prev) => ({
      ...prev,
      [selectedUserId]: [...defaultLoans],
    }));
    const updatedUser: EMIDetoxUser = { ...currentUser, currentEMIs: defaultLoans };
    const updatedMath = calculateDetoxMetrics(updatedUser, 14.0, tenure);
    void fetchAIAnalysis(updatedUser, updatedMath);
  };

  const hasManualLoans = currentLoans.some((l) => l.isManual);

  return (
    <div className="space-y-6">
      {/* -------------------- Top User Profile Switcher -------------------- */}
      <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-white/10">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-sky animate-pulse" />
              <p className="text-[11px] font-semibold uppercase tracking-wider text-sky">
                Proactive Debt Consolidation Agent
              </p>
            </div>
            <h2 className="mt-0.5 font-display text-[20px] font-bold text-white tracking-tight">
              Select Customer Portfolio
            </h2>
          </div>
          <div className="flex items-center gap-2 text-[12px] text-white/55">
            <span>Paytm Partner Lending APR:</span>
            <span className="rounded-full bg-sky/20 px-2.5 py-0.5 font-mono font-bold text-sky">
              14.0% Flat
            </span>
          </div>
        </div>

        {/* User Persona Selector Cards */}
        <div className="mt-3.5 grid grid-cols-1 sm:grid-cols-3 gap-3">
          {Object.values(EMI_DETOX_USERS).map((user) => {
            const isSelected = user.userId === selectedUserId;
            return (
              <button
                key={user.userId}
                onClick={() => setSelectedUserId(user.userId)}
                className={`flex items-start gap-3 rounded-2xl p-3 text-left transition ${
                  isSelected
                    ? "bg-sky/15 ring-1 ring-sky/60"
                    : "bg-white/[0.02] border border-white/5 hover:bg-white/[0.06]"
                }`}
              >
                <span
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl font-display text-[15px] font-bold ${
                    isSelected ? "bg-sky text-navy" : "bg-white/10 text-white/80"
                  }`}
                >
                  {user.firstName[0]}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-1">
                    <p className="font-display text-[14.5px] font-semibold text-white leading-snug truncate">
                      {user.name}
                    </p>
                    <span
                      className={`text-[11px] font-mono px-2 py-0.5 rounded-full ${
                        user.cibilScore >= 700
                          ? "bg-[#5fe0a8]/15 text-[#5fe0a8]"
                          : user.cibilScore >= 650
                          ? "bg-amber/20 text-amber"
                          : "bg-rust/20 text-rust"
                      }`}
                    >
                      CIBIL {user.cibilScore}
                    </span>
                  </div>
                  <p className="text-[12px] text-white/55 truncate">{user.occupation}</p>
                  <p className="mt-1 text-[11px] text-white/40">
                    Monthly income: <b className="text-white/80">{formatINR(user.income)}</b>
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Behavioral Context Callout */}
        <div className="mt-3.5 rounded-2xl border border-white/5 bg-white/[0.02] p-3.5 text-[12.5px] leading-relaxed text-white/70">
          <span className="font-semibold text-white">Why they are in debt: </span>
          <span>{currentUser.behavioralContext}</span>
        </div>
      </div>

      {/* -------------------- Split-Screen: Before (Chaos) vs After (Paytm) -------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-stretch">
        {/* ==================== LEFT SIDE: THE CHAOS (BEFORE) ==================== */}
        <div className="flex flex-col justify-between rounded-3xl border border-white/10 bg-white/[0.04] p-5 sm:p-6">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3.5 border-b border-white/10">
              <div>
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-rust/20 text-rust text-[12px] font-bold">
                    ✕
                  </span>
                  <h3 className="font-display text-[18px] font-bold text-white tracking-tight">
                    Current Fragmented EMIs
                  </h3>
                </div>
                <p className="mt-0.5 text-[12px] text-white/50">
                  {currentUser.currentEMIs.length} high-interest lenders · Disparate billing dates
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {hasManualLoans && (
                  <button
                    onClick={handleResetLoans}
                    className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-white/55 hover:text-white hover:bg-white/10 transition cursor-pointer"
                    title="Reset to default loans"
                  >
                    <RotateCcw size={11} />
                    <span>Reset</span>
                  </button>
                )}
                <button
                  onClick={() => setIsAddModalOpen(true)}
                  className="flex items-center gap-1.5 rounded-full bg-sky/20 border border-sky/40 px-3 py-1 text-[11.5px] font-semibold text-sky hover:bg-sky/30 transition cursor-pointer"
                >
                  <Plus size={13} className="text-sky" />
                  <span>+ Add Unlisted Loan</span>
                </button>
                <span className="rounded-full bg-rust/20 px-3 py-1 text-[11.5px] font-mono font-bold text-rust">
                  Avg {math.weightedAverageAPR}% APR
                </span>
              </div>
            </div>

            {/* List of current predatory EMIs */}
            <div className="mt-4 space-y-3">
              {currentUser.currentEMIs.map((loan) => (
                <div
                  key={loan.id}
                  className={`rounded-2xl border p-4 transition ${
                    loan.isManual
                      ? "border-sky/40 bg-sky/[0.04] hover:bg-sky/[0.08]"
                      : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
                          loan.isManual ? "bg-sky/20 text-sky" : "bg-white/10 text-white"
                        }`}
                      >
                        <CreditCard size={18} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-display text-[14.5px] font-bold text-white leading-snug">
                            {loan.lenderName}
                          </p>
                          {loan.isManual && (
                            <span className="rounded-full bg-sky/20 border border-sky/40 px-2 py-0.5 text-[9.5px] font-semibold uppercase tracking-wider text-sky">
                              Unlisted
                            </span>
                          )}
                        </div>
                        <p className="text-[11.5px] text-white/50">
                          {loan.loanType}
                          {loan.accountNumber ? ` · Ref: ${loan.accountNumber}` : ""}
                          {" · Outstanding: "}
                          <span className="text-white/80 font-medium">
                            {formatINR(loan.outstandingAmount)}
                          </span>
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="rounded-full bg-rust/25 px-2.5 py-0.5 font-mono text-[11.5px] font-bold text-rust">
                        {loan.interestRate}% APR
                      </span>
                      {loan.isManual && (
                        <button
                          onClick={() => handleRemoveLoan(loan.id)}
                          className="rounded-lg p-1 text-white/40 hover:text-rust hover:bg-rust/20 transition cursor-pointer"
                          title="Remove custom loan"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 border-t border-white/5 pt-2.5 text-[12px]">
                    <span className="flex items-center gap-1.5 text-white/60">
                      <Calendar size={13} className="text-amber" />
                      Due on <b className="text-white">{loan.dueDayOfMonth}th</b> of month
                    </span>
                    <span className="font-mono font-bold text-white text-[13.5px]">
                      {formatINR(loan.monthlyEMI)}
                      <span className="font-normal text-white/40 text-[11px]">/mo</span>
                    </span>
                  </div>

                  <p className="mt-2 text-[11px] text-amber/80 flex items-center gap-1">
                    <AlertTriangle size={12} className="shrink-0" />
                    <span>{loan.penalties}</span>
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Left Summary Box */}
          <div className="mt-6 rounded-2xl border border-rust/30 bg-rust/10 p-4">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-white/70">
                Total Monthly Burden:
              </span>
              <span className="font-display text-[19px] font-bold text-rust">
                {formatINR(math.totalCurrentMonthlyPayout)}/mo
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11.5px] text-white/50 border-t border-white/5 pt-2">
              <span>Total Outstanding Principal:</span>
              <span className="font-mono text-white/80">
                {formatINR(math.totalOutstandingAmount)}
              </span>
            </div>
            <div className="mt-1 flex items-center justify-between text-[11.5px] text-white/50">
              <span>Current Debt-to-Income (DTI):</span>
              <span className="font-mono font-bold text-rust">{math.dtiBefore}% of income</span>
            </div>
          </div>
        </div>

        {/* ==================== RIGHT SIDE: THE PAYTM SOLUTION (AFTER) ==================== */}
        <div className="flex flex-col justify-between rounded-3xl border border-sky/30 bg-white/[0.04] p-5 sm:p-6 relative overflow-hidden">
          <div>
            <div className="flex items-center justify-between pb-3.5 border-b border-white/10">
              <div>
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-sky text-navy text-[12px] font-bold">
                    ✓
                  </span>
                  <h3 className="font-display text-[18px] font-bold text-white tracking-tight">
                    Paytm Debt Consolidation Loan
                  </h3>
                </div>
                <p className="mt-0.5 text-[12px] text-white/50">
                  1 Single Clean Loan · 14.0% APR · Auto-settle 3 accounts
                </p>
              </div>
              <span className="rounded-full bg-sky/20 px-3 py-1 text-[11.5px] font-mono font-bold text-sky">
                14% APR Flat
              </span>
            </div>

            {/* Guaranteed Savings Callout */}
            <div className="mt-4 rounded-2xl border border-good/40 bg-good/10 p-5 text-center">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[#5fe0a8]">
                Net Monthly Cash Savings
              </p>
              <div className="mt-1 flex items-baseline justify-center gap-2">
                <span className="font-display text-[36px] sm:text-[42px] font-extrabold text-[#5fe0a8] tracking-tight">
                  Save {formatINR(math.netMonthlySavings)}
                </span>
                <span className="text-[14px] text-white/60">/ month</span>
              </div>
              <p className="mt-1 text-[13px] text-white/80">
                🎉 That is <b className="text-white">{formatINR(math.netAnnualSavings)}</b> saved per
                year!
              </p>

              {/* Monthly EMI & Tenure Comparison */}
              <div className="mt-4 grid grid-cols-2 gap-2 text-left">
                <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
                  <p className="text-[10.5px] uppercase font-semibold text-white/45">
                    New Single EMI
                  </p>
                  <p className="mt-0.5 font-display text-[20px] font-bold text-white">
                    {formatINR(math.paytmConsolidatedMonthlyEMI)}
                    <span className="text-[11px] font-normal text-white/45">/mo</span>
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
                  <p className="text-[10.5px] uppercase font-semibold text-white/45">
                    Single Auto-Debit
                  </p>
                  <p className="mt-0.5 font-display text-[16px] font-bold text-sky flex items-center gap-1">
                    <Calendar size={14} /> 5th of Month
                  </p>
                </div>
              </div>
            </div>

            {/* Key Strategic Benefits List */}
            <ul className="mt-4 space-y-2 text-[12.5px] text-white/85">
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-sky shrink-0 mt-0.5" />
                <span>
                  <b>Paytm 1-Click Payoff:</b> Direct digital disbursement clears all 3 third-party
                  balances automatically.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-sky shrink-0 mt-0.5" />
                <span>
                  <b>DTI Ratio Drop:</b> Debt burden drops from {math.dtiBefore}% down to{" "}
                  <b className="text-[#5fe0a8]">{math.dtiAfter}%</b>.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-sky shrink-0 mt-0.5" />
                <span>
                  <b>CIBIL Standing:</b> Closing multiple unsecured BNPL lines projects a{" "}
                  <b className="text-sky">+{math.projectedCibilBoostPoints} points</b> bureau boost.
                </span>
              </li>
            </ul>
          </div>

          {/* Action Button & Confirmation */}
          <div className="mt-6 pt-3 border-t border-white/10">
            {isConsolidated ? (
              <div className="rounded-2xl border border-good/50 bg-good/20 p-4 text-center">
                <p className="font-display text-[15px] font-bold text-[#5fe0a8] flex items-center justify-center gap-1.5">
                  <CheckCircle2 size={18} />
                  Consolidation Pre-Approved & Active!
                </p>
                <p className="mt-1 text-[11.5px] text-white/70">
                  Disbursement scheduled to clear competitor accounts. First single EMI due on 5th.
                </p>
                <button
                  onClick={() => setIsConsolidated(false)}
                  className="mt-3 text-[11px] underline text-white/50 hover:text-white"
                >
                  Reset / Re-test
                </button>
              </div>
            ) : (
              <>
                <motion.button
                  whileTap={{ scale: 0.98 }}
                  disabled={isConsolidating}
                  onClick={handleConsolidateAction}
                  className="w-full flex items-center justify-center gap-2 rounded-2xl bg-sky py-3.5 px-6 font-display text-[15px] font-semibold text-navy transition enabled:hover:brightness-110 disabled:opacity-75 cursor-pointer shadow-lg shadow-sky/20"
                >
                  {isConsolidating ? (
                    <>
                      <RefreshCw size={17} className="animate-spin text-navy" />
                      Processing 1-Click Paytm Refinance...
                    </>
                  ) : (
                    <>
                      <Zap size={17} className="fill-navy" />
                      Consolidate into 1-Click Paytm EMI
                      <ArrowRight size={16} />
                    </>
                  )}
                </motion.button>
                <p className="mt-2 text-center text-[11px] text-white/45">
                  Instant digital payoff · No manual branch visits · Zero foreclosure penalty
                </p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* -------------------- 4. Live LLM Raah AI Assessment -------------------- */}
      <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5 sm:p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand text-white">
              <Sparkles size={16} className="text-sky" />
            </span>
            <div>
              <h3 className="font-display text-[17px] font-bold text-white tracking-tight">
                Raah AI Empathy & Conversion Engine
              </h3>
              <p className="text-[11px] text-white/50">
                Live Indic LLM Assessment (Sarvam-105B) · Grounded in verified mathematical outputs
              </p>
            </div>
          </div>
          <button
            onClick={() => void fetchAIAnalysis(currentUser, math)}
            disabled={isLoadingAI}
            className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11.5px] font-medium text-white/70 hover:bg-white/10 transition disabled:opacity-50"
          >
            <RefreshCw size={12} className={isLoadingAI ? "animate-spin text-sky" : ""} />
            {isLoadingAI ? "Synthesizing..." : "Re-analyze with LLM"}
          </button>
        </div>

        {/* 3 LLM Sections */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: The Counselor Pitch (Conversion Engine) */}
          <div className="flex flex-col justify-between rounded-2xl border border-white/10 bg-white/[0.02] p-4">
            <div>
              <div className="flex items-center gap-2 text-sky text-[12px] font-bold uppercase tracking-wider">
                <HeartHandshake size={15} />
                <span>The Counselor Pitch</span>
              </div>
              <p className="mt-2 text-[13px] leading-relaxed text-white/90 italic">
                {isLoadingAI ? (
                  <span className="text-white/40 animate-pulse">Generating personalized counselor pitch...</span>
                ) : (
                  `"${aiAnalysis?.counselorPitch}"`
                )}
              </p>
            </div>
            <p className="mt-3 text-[10.5px] text-white/40 border-t border-white/5 pt-2">
              Speaks to their emotional stress to maximize consolidation conversion.
            </p>
          </div>

          {/* Card 2: Dynamic Partner Routing */}
          <div className="flex flex-col justify-between rounded-2xl border border-white/10 bg-white/[0.02] p-4">
            <div>
              <div className="flex items-center gap-2 text-[#5fe0a8] text-[12px] font-bold uppercase tracking-wider">
                <Building2 size={15} />
                <span>Dynamic Partner Routing</span>
              </div>
              {isLoadingAI ? (
                <p className="mt-2 text-[13px] text-white/40 animate-pulse">Evaluating risk tier & partner...</p>
              ) : (
                <div className="mt-2 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-display text-[15px] font-bold text-white">
                      {aiAnalysis?.partnerRouting.partnerName}
                    </span>
                    <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10.5px] text-sky font-mono">
                      {aiAnalysis?.partnerRouting.interestOffered}
                    </span>
                  </div>
                  <span className="inline-block rounded-md bg-white/5 px-2 py-0.5 text-[11px] font-medium text-white/60">
                    {aiAnalysis?.partnerRouting.riskTier}
                  </span>
                  <p className="text-[12px] leading-relaxed text-white/75 mt-1">
                    {aiAnalysis?.partnerRouting.routingJustification}
                  </p>
                </div>
              )}
            </div>
            <p className="mt-3 text-[10.5px] text-white/40 border-t border-white/5 pt-2">
              Matches CIBIL score & cash flow with the optimal co-lending partner.
            </p>
          </div>

          {/* Card 3: Paytm ROI Justification (For the Judges) */}
          <div className="flex flex-col justify-between rounded-2xl border border-white/10 bg-white/[0.02] p-4">
            <div>
              <div className="flex items-center gap-2 text-amber text-[12px] font-bold uppercase tracking-wider">
                <Award size={15} />
                <span>Paytm ROI (For the Judges)</span>
              </div>
              <p className="mt-2 text-[12.5px] leading-relaxed text-white/85">
                {isLoadingAI ? (
                  <span className="text-white/40 animate-pulse">Calculating unit economics & ecosystem ROI...</span>
                ) : (
                  aiAnalysis?.paytmROIJustification
                )}
              </p>
            </div>
            <p className="mt-3 text-[10.5px] text-white/40 border-t border-white/5 pt-2">
              Demonstrates why proactive debt refinance generates high margin with zero CAC.
            </p>
          </div>
        </div>
      </div>

      {/* -------------------- Manual Loan Input Modal -------------------- */}
      <AnimatePresence>
        {isAddModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="w-full max-w-lg rounded-3xl border border-white/10 bg-[#0d1829] p-6 shadow-2xl text-white relative max-h-[90vh] overflow-y-auto"
            >
              {/* Modal Header */}
              <div className="flex items-start justify-between pb-4 border-b border-white/10">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-sky/20 text-sky text-[12px] font-bold">
                      +
                    </span>
                    <h3 className="font-display text-[18px] font-bold text-white tracking-tight">
                      Add Unlisted / External Loan
                    </h3>
                  </div>
                  <p className="mt-1 text-[12px] text-white/50">
                    Include loans, credit cards, or BNPLs not yet captured in Account Aggregator.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="rounded-xl p-1.5 text-white/50 hover:text-white hover:bg-white/10 transition cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleAddLoanSubmit} className="mt-4 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {/* Lender Name */}
                  <div className="sm:col-span-2">
                    <label className="block text-[11.5px] font-medium text-white/70 mb-1">
                      Lender / App Name <span className="text-rust">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Navi Instant Loan, Ring, Bajaj Finance"
                      value={modalForm.lenderName}
                      onChange={(e) => setModalForm({ ...modalForm, lenderName: e.target.value })}
                      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-2 text-[13px] text-white placeholder-white/30 focus:border-sky/60 focus:outline-none focus:ring-1 focus:ring-sky/60"
                    />
                  </div>

                  {/* Loan / Account Reference */}
                  <div>
                    <label className="block text-[11.5px] font-medium text-white/70 mb-1">
                      Loan Account / Card Number
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. LN-9842-X or HDFC-8821"
                      value={modalForm.accountNumber}
                      onChange={(e) => setModalForm({ ...modalForm, accountNumber: e.target.value })}
                      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-2 text-[13px] text-white placeholder-white/30 focus:border-sky/60 focus:outline-none focus:ring-1 focus:ring-sky/60"
                    />
                  </div>

                  {/* Loan Type */}
                  <div>
                    <label className="block text-[11.5px] font-medium text-white/70 mb-1">
                      Loan Category
                    </label>
                    <select
                      value={modalForm.loanType}
                      onChange={(e) =>
                        setModalForm({
                          ...modalForm,
                          loanType: e.target.value as ExistingLoanItem["loanType"],
                        })
                      }
                      className="w-full rounded-xl border border-white/10 bg-[#132238] px-3.5 py-2 text-[13px] text-white focus:border-sky/60 focus:outline-none focus:ring-1 focus:ring-sky/60 cursor-pointer"
                    >
                      <option value="Instant Loan">Instant Loan / FinTech</option>
                      <option value="BNPL">BNPL (LazyPay, Simple, etc.)</option>
                      <option value="Credit Card">Credit Card Revolver</option>
                      <option value="Consumer Durable">Consumer Durable EMI</option>
                      <option value="Two-Wheeler Loan">Two-Wheeler Loan</option>
                    </select>
                  </div>

                  {/* Outstanding Amount */}
                  <div>
                    <label className="block text-[11.5px] font-medium text-white/70 mb-1">
                      Outstanding Balance (₹) <span className="text-rust">*</span>
                    </label>
                    <input
                      type="number"
                      required
                      min={1000}
                      step={500}
                      placeholder="e.g. 35000"
                      value={modalForm.outstandingAmount}
                      onChange={(e) =>
                        setModalForm({ ...modalForm, outstandingAmount: e.target.value })
                      }
                      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-2 text-[13px] text-white placeholder-white/30 focus:border-sky/60 focus:outline-none focus:ring-1 focus:ring-sky/60 font-mono"
                    />
                  </div>

                  {/* Monthly EMI */}
                  <div>
                    <label className="block text-[11.5px] font-medium text-white/70 mb-1">
                      Monthly EMI Payout (₹) <span className="text-rust">*</span>
                    </label>
                    <input
                      type="number"
                      required
                      min={100}
                      step={100}
                      placeholder="e.g. 4200"
                      value={modalForm.monthlyEMI}
                      onChange={(e) => setModalForm({ ...modalForm, monthlyEMI: e.target.value })}
                      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-2 text-[13px] text-white placeholder-white/30 focus:border-sky/60 focus:outline-none focus:ring-1 focus:ring-sky/60 font-mono"
                    />
                  </div>

                  {/* Interest Rate APR % */}
                  <div>
                    <label className="block text-[11.5px] font-medium text-white/70 mb-1">
                      Interest Rate (% APR)
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        min={5}
                        max={60}
                        step={0.5}
                        placeholder="e.g. 32"
                        value={modalForm.interestRate}
                        onChange={(e) =>
                          setModalForm({ ...modalForm, interestRate: e.target.value })
                        }
                        className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-2 text-[13px] text-white placeholder-white/30 focus:border-sky/60 focus:outline-none focus:ring-1 focus:ring-sky/60 font-mono pr-8"
                      />
                      <span className="absolute right-3 top-2 text-[12px] text-white/40 font-mono">
                        %
                      </span>
                    </div>
                  </div>

                  {/* Due Day of Month */}
                  <div>
                    <label className="block text-[11.5px] font-medium text-white/70 mb-1">
                      Monthly Due Day (1-31)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={31}
                      placeholder="e.g. 15"
                      value={modalForm.dueDayOfMonth}
                      onChange={(e) =>
                        setModalForm({ ...modalForm, dueDayOfMonth: e.target.value })
                      }
                      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-2 text-[13px] text-white placeholder-white/30 focus:border-sky/60 focus:outline-none focus:ring-1 focus:ring-sky/60 font-mono"
                    />
                  </div>

                  {/* Late fee / penalties */}
                  <div className="sm:col-span-2">
                    <label className="block text-[11.5px] font-medium text-white/70 mb-1">
                      Late Payment Penalty / Bounce Charges
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. ₹500 bounce fee + daily penal interest"
                      value={modalForm.penalties}
                      onChange={(e) => setModalForm({ ...modalForm, penalties: e.target.value })}
                      className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-2 text-[13px] text-white placeholder-white/30 focus:border-sky/60 focus:outline-none focus:ring-1 focus:ring-sky/60"
                    />
                  </div>
                </div>

                {/* Live Preview Banner */}
                <div className="rounded-2xl border border-sky/30 bg-sky/[0.06] p-3 text-[12px] text-white/75 flex items-start gap-2">
                  <Zap size={15} className="text-sky shrink-0 mt-0.5" />
                  <span>
                    Adding this loan will instantly recompute <b>Paytm 14% Consolidated EMI</b>,
                    recalculate <b>net monthly savings</b>, and regenerate the <b>Raah AI Counselor Pitch</b>.
                  </span>
                </div>

                {/* Modal Actions */}
                <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/10">
                  <button
                    type="button"
                    onClick={() => setIsAddModalOpen(false)}
                    className="rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-[13px] font-medium text-white/70 hover:bg-white/10 transition cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex items-center gap-2 rounded-2xl bg-sky px-5 py-2.5 font-display text-[13px] font-semibold text-navy hover:brightness-110 transition cursor-pointer shadow-md shadow-sky/20"
                  >
                    <Plus size={15} />
                    <span>Add Loan to Portfolio</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
