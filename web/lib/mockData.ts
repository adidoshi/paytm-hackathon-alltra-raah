/**
 * Mock Database & TypeScript Mathematical Engine for Raah EMI Detox Agent
 * 
 * Strict rule: All math (EMI, totals, savings, DTI, interest averages) is executed
 * in deterministic TypeScript, NOT hallucinated by the LLM.
 */

export interface ExistingLoanItem {
  id: string;
  lenderName: string;
  loanType: "BNPL" | "Instant Loan" | "Credit Card" | "Consumer Durable" | "Two-Wheeler Loan";
  accountNumber?: string;
  outstandingAmount: number;
  monthlyEMI: number;
  interestRate: number; // Annual Percentage Rate (APR) in %
  dueDayOfMonth: number; // e.g. 5, 12, 22
  tenureRemainingMonths: number;
  penalties: string;
  riskCategory: "critical" | "high" | "moderate";
  isManual?: boolean;
}

export interface EMIDetoxUser {
  userId: string;
  name: string;
  firstName: string;
  age: number;
  city: string;
  occupation: string;
  income: number; // Monthly income in INR
  cibilScore: number;
  behavioralContext: string;
  originalRejectedProduct: string;
  originalRejectedAmount: number;
  currentEMIs: ExistingLoanItem[];
}

export interface CalculatedDetoxMath {
  totalOutstandingAmount: number;
  totalCurrentMonthlyPayout: number;
  weightedAverageAPR: number;
  paytmAPR: number; // Standard 14.0%
  tenureMonths: number; // 12 or 18 months
  paytmConsolidatedMonthlyEMI: number;
  netMonthlySavings: number;
  netAnnualSavings: number;
  savingsPercentage: number;
  dtiBefore: number; // Debt to Income %
  dtiAfter: number;
  dueDatesCountBefore: number;
  dueDatesCountAfter: number; // Always 1 (5th of month)
  nachBounceRiskSavingsPerYear: number;
  projectedCibilBoostPoints: number;
}

/**
 * Format currency in Indian numbering format (e.g. ₹1,25,000)
 */
export function formatINR(amount: number): string {
  return "₹" + Math.round(amount).toLocaleString("en-IN");
}

/**
 * Standard Reducing Balance EMI calculation
 * EMI = [P x R x (1+R)^N] / [(1+R)^N - 1]
 */
export function calculateReducingEMI(
  principal: number,
  annualInterestRate: number,
  tenureMonths: number
): number {
  if (principal <= 0 || tenureMonths <= 0) return 0;
  if (annualInterestRate <= 0) return Math.round(principal / tenureMonths);

  const monthlyRate = annualInterestRate / (12 * 100);
  const factor = Math.pow(1 + monthlyRate, tenureMonths);
  const emi = (principal * monthlyRate * factor) / (factor - 1);
  return Math.round(emi);
}

/**
 * Deterministic calculation of EMI Detox financial metrics
 */
export function calculateDetoxMetrics(
  user: EMIDetoxUser,
  targetAPR: number = 14.0,
  tenureMonths: number = 12
): CalculatedDetoxMath {
  const loans = user.currentEMIs;
  const totalOutstandingAmount = loans.reduce((sum, item) => sum + item.outstandingAmount, 0);
  const totalCurrentMonthlyPayout = loans.reduce((sum, item) => sum + item.monthlyEMI, 0);

  const weightedInterestSum = loans.reduce(
    (sum, item) => sum + item.outstandingAmount * item.interestRate,
    0
  );
  const weightedAverageAPR =
    totalOutstandingAmount > 0
      ? Number((weightedInterestSum / totalOutstandingAmount).toFixed(1))
      : 30.0;

  const paytmConsolidatedMonthlyEMI = calculateReducingEMI(
    totalOutstandingAmount,
    targetAPR,
    tenureMonths
  );

  const netMonthlySavings = Math.max(0, totalCurrentMonthlyPayout - paytmConsolidatedMonthlyEMI);
  const netAnnualSavings = netMonthlySavings * 12;
  const savingsPercentage =
    totalCurrentMonthlyPayout > 0
      ? Math.round((netMonthlySavings / totalCurrentMonthlyPayout) * 100)
      : 0;

  const dtiBefore =
    user.income > 0 ? Number(((totalCurrentMonthlyPayout / user.income) * 100).toFixed(1)) : 50.0;
  const dtiAfter =
    user.income > 0 ? Number(((paytmConsolidatedMonthlyEMI / user.income) * 100).toFixed(1)) : 25.0;

  const nachBounceRiskSavingsPerYear = loans.length * 450 * 2; // avg 2 bounce attempts avoided per loan
  const projectedCibilBoostPoints = user.cibilScore < 650 ? 45 : user.cibilScore < 700 ? 32 : 20;

  return {
    totalOutstandingAmount,
    totalCurrentMonthlyPayout,
    weightedAverageAPR,
    paytmAPR: targetAPR,
    tenureMonths,
    paytmConsolidatedMonthlyEMI,
    netMonthlySavings,
    netAnnualSavings,
    savingsPercentage,
    dtiBefore,
    dtiAfter,
    dueDatesCountBefore: loans.length,
    dueDatesCountAfter: 1,
    nachBounceRiskSavingsPerYear,
    projectedCibilBoostPoints,
  };
}

/**
 * Mock Database of users for EMI Detox & Debt Consolidation
 */
export const EMI_DETOX_USERS: Record<string, EMIDetoxUser> = {
  ravi: {
    userId: "ravi",
    name: "Ravi Jadhav",
    firstName: "Ravi",
    age: 27,
    city: "Pune",
    occupation: "Delivery partner (Gig economy)",
    income: 28000,
    cibilScore: 624,
    behavioralContext:
      "Ravi took multiple instant BNPL and short-term salary loans to cover emergency bike repairs and his mother's clinic bills. Fragmented due dates and 32% compounding interest consume 47% of his monthly take-home pay, keeping him trapped in a debt cycle.",
    originalRejectedProduct: "Personal loan ₹1,00,000",
    originalRejectedAmount: 100000,
    currentEMIs: [
      {
        id: "l1",
        lenderName: "LazyPay BNPL",
        loanType: "BNPL",
        outstandingAmount: 24000,
        monthlyEMI: 3600,
        interestRate: 26,
        dueDayOfMonth: 5,
        tenureRemainingMonths: 8,
        penalties: "₹500 late fee per billing cycle + 36% penal interest",
        riskCategory: "high",
      },
      {
        id: "l2",
        lenderName: "KreditBee Quick Loan",
        loanType: "Instant Loan",
        outstandingAmount: 38000,
        monthlyEMI: 4900,
        interestRate: 32,
        dueDayOfMonth: 12,
        tenureRemainingMonths: 10,
        penalties: "0.2% per day overdue fine + immediate bureau strike",
        riskCategory: "critical",
      },
      {
        id: "l3",
        lenderName: "Ring / Kissht UPI Credit",
        loanType: "BNPL",
        outstandingAmount: 18000,
        monthlyEMI: 2650,
        interestRate: 36,
        dueDayOfMonth: 20,
        tenureRemainingMonths: 7,
        penalties: "₹350 auto-debit bounce penalty per failed NACH attempt",
        riskCategory: "critical",
      },
    ],
  },

  priya: {
    userId: "priya",
    name: "Priya Kulkarni",
    firstName: "Priya",
    age: 31,
    city: "Pune",
    occupation: "Salaried, IT support executive",
    income: 45000,
    cibilScore: 712,
    behavioralContext:
      "Priya has high revolving balances across two credit cards and a consumer electronics EMI after an expensive apartment relocation. She pays ₹15,400 monthly in minimum dues at 38% APR, barely touching the principal while bank finance charges compound.",
    originalRejectedProduct: "Personal loan ₹3,00,000",
    originalRejectedAmount: 300000,
    currentEMIs: [
      {
        id: "p1",
        lenderName: "HDFC Millennia Credit Card",
        loanType: "Credit Card",
        outstandingAmount: 62000,
        monthlyEMI: 6500,
        interestRate: 38,
        dueDayOfMonth: 8,
        tenureRemainingMonths: 12,
        penalties: "3.6% monthly finance charges (43.2% p.a.) + 18% GST",
        riskCategory: "critical",
      },
      {
        id: "p2",
        lenderName: "SBI SimplyCLICK Card",
        loanType: "Credit Card",
        outstandingAmount: 45000,
        monthlyEMI: 4800,
        interestRate: 36,
        dueDayOfMonth: 16,
        tenureRemainingMonths: 12,
        penalties: "₹750 late fee per month + interest on entire unpaid statement",
        riskCategory: "high",
      },
      {
        id: "p3",
        lenderName: "Bajaj Finserv Consumer EMI",
        loanType: "Consumer Durable",
        outstandingAmount: 32000,
        monthlyEMI: 4100,
        interestRate: 22,
        dueDayOfMonth: 25,
        tenureRemainingMonths: 8,
        penalties: "₹450 NACH return charge per rejection",
        riskCategory: "moderate",
      },
    ],
  },

  sameer: {
    userId: "sameer",
    name: "Sameer Shaikh",
    firstName: "Sameer",
    age: 34,
    city: "Pimpri-Chinchwad",
    occupation: "Shop supervisor / retail merchant",
    income: 32000,
    cibilScore: 668,
    behavioralContext:
      "Sameer fell behind on his bike loan after seasonal shop sales dipped, resulting in a 34-day DPD flag. He subsequently applied on 5 mobile loan apps in panic, incurring multiple hard enquiries and high-interest daily loans.",
    originalRejectedProduct: "Personal loan ₹1,50,000",
    originalRejectedAmount: 150000,
    currentEMIs: [
      {
        id: "s1",
        lenderName: "TVS Credit Two-Wheeler",
        loanType: "Two-Wheeler Loan",
        outstandingAmount: 48000,
        monthlyEMI: 4200,
        interestRate: 22,
        dueDayOfMonth: 4,
        tenureRemainingMonths: 14,
        penalties: "₹450 ECS bounce fee + 2% per month penal rate",
        riskCategory: "moderate",
      },
      {
        id: "s2",
        lenderName: "MoneyView Personal Loan",
        loanType: "Instant Loan",
        outstandingAmount: 35000,
        monthlyEMI: 4600,
        interestRate: 30,
        dueDayOfMonth: 14,
        tenureRemainingMonths: 9,
        penalties: "₹500 dishonour charge + bureau default warning",
        riskCategory: "critical",
      },
      {
        id: "s3",
        lenderName: "Fibe (EarlySalary) Advance",
        loanType: "Instant Loan",
        outstandingAmount: 22000,
        monthlyEMI: 3100,
        interestRate: 28,
        dueDayOfMonth: 23,
        tenureRemainingMonths: 8,
        penalties: "₹400 bounce charge per failed UPI AutoPay attempt",
        riskCategory: "high",
      },
    ],
  },
};
