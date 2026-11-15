/**
 * EMI Detox Logic & Debt Consolidation Engine for Raah (Paytm Fintech AI Agent)
 * 
 * Scans mocked UPI mandates and bank transaction history.
 * Detects multiple fragmented high-interest loans (BNPL, instant loan apps, credit cards)
 * and calculates the financial and mental benefits of consolidating into a single
 * 14% APR Paytm Refinance Loan.
 */

export interface ExistingEMI {
  id: string;
  lender: string;
  productName: string;
  type: "BNPL" | "Personal Loan" | "Credit Card" | "Consumer Durable";
  outstandingBalance: number;
  monthlyEMI: number;
  interestRateAPR: number; // e.g. 24, 30, 36
  dueDayOfMonth: number; // e.g. 5, 12, 22
  totalTenureMonths: number;
  remainingTenureMonths: number;
  riskLevel: "critical" | "high" | "moderate";
  platformFeeCharged: number;
  penaltyRiskDescription: string;
}

export interface EMIDetoxResult {
  hasHighInterestDebt: boolean;
  totalLoansCount: number;
  existingLoans: ExistingEMI[];
  totalOutstandingBalance: number;
  totalCurrentMonthlyPayout: number;
  weightedAverageInterestAPR: number;
  paytmConsolidatedAPR: number;
  consolidatedTenureMonths: number;
  paytmConsolidatedMonthlyEMI: number;
  monthlySavings: number;
  annualSavings: number;
  savingsPercentage: number;
  dueDatesConsolidatedTo: number; // 1 single date (e.g. 5th)
  datesReducedCount: number; // e.g. reduced from 3 dates to 1
  nachBounceRiskSavedPerYear: number;
  cibilBoostProjectionPoints: number;
  llmPitchText: string;
}

/**
 * Standard Indian Rupee currency formatter
 * Example: 15850 -> ₹15,850
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
 * Default mocked high-interest loans detected in UPI mandates & bank feeds
 */
export const MOCK_HIGH_INTEREST_EMIS: ExistingEMI[] = [
  {
    id: "emi_lazypay",
    lender: "LazyPay",
    productName: "BNPL Pay Later Revolving",
    type: "BNPL",
    outstandingBalance: 28000,
    monthlyEMI: 3850,
    interestRateAPR: 24,
    dueDayOfMonth: 5,
    totalTenureMonths: 9,
    remainingTenureMonths: 8,
    riskLevel: "high",
    platformFeeCharged: 350,
    penaltyRiskDescription: "₹500 late fee + 36% APR if unpaid by 5th",
  },
  {
    id: "emi_kreditbee",
    lender: "KreditBee",
    productName: "Instant Salary Loan",
    type: "Personal Loan",
    outstandingBalance: 45000,
    monthlyEMI: 5800,
    interestRateAPR: 30,
    dueDayOfMonth: 12,
    totalTenureMonths: 12,
    remainingTenureMonths: 9,
    riskLevel: "critical",
    platformFeeCharged: 1200,
    penaltyRiskDescription: "Daily 0.2% penalty + bureau report upon 1-day delay",
  },
  {
    id: "emi_hdfc_cc",
    lender: "HDFC Bank",
    productName: "Millennia Credit Card (Min Due + Revolving)",
    type: "Credit Card",
    outstandingBalance: 52000,
    monthlyEMI: 6200,
    interestRateAPR: 36,
    dueDayOfMonth: 22,
    totalTenureMonths: 12,
    remainingTenureMonths: 10,
    riskLevel: "critical",
    platformFeeCharged: 750,
    penaltyRiskDescription: "3.5% monthly finance charge + 18% GST compounding",
  },
];

/**
 * Alternative lightweight loans for personas with lower debt (e.g. entry level)
 */
export const MOCK_STUDENT_OR_LIGHT_EMIS: ExistingEMI[] = [
  {
    id: "emi_ring",
    lender: "Ring / Kissht",
    productName: "Merchant UPI Credit Line",
    type: "BNPL",
    outstandingBalance: 12000,
    monthlyEMI: 2400,
    interestRateAPR: 28,
    dueDayOfMonth: 7,
    totalTenureMonths: 6,
    remainingTenureMonths: 5,
    riskLevel: "high",
    platformFeeCharged: 250,
    penaltyRiskDescription: "₹350 bounce fee on auto-debit failure",
  },
  {
    id: "emi_bajaj_finserv",
    lender: "Bajaj Finserv",
    productName: "Mobile EMI Network Card",
    type: "Consumer Durable",
    outstandingBalance: 18000,
    monthlyEMI: 2850,
    interestRateAPR: 22,
    dueDayOfMonth: 18,
    totalTenureMonths: 8,
    remainingTenureMonths: 7,
    riskLevel: "moderate",
    platformFeeCharged: 450,
    penaltyRiskDescription: "₹450 NACH return charge per rejection",
  },
];

/**
 * Calculates the complete EMI Detox and Debt Consolidation breakdown.
 *
 * @param customLoans Optional list of existing loans (defaults to MOCK_HIGH_INTEREST_EMIS)
 * @param targetAPR Paytm consolidated APR (defaults to 14.0%)
 * @param targetTenure Proposed tenure for the consolidated loan in months (defaults to 12)
 */
export function calculateEMIDetox(
  customLoans: ExistingEMI[] = MOCK_HIGH_INTEREST_EMIS,
  targetAPR: number = 14.0,
  targetTenure: number = 12
): EMIDetoxResult {
  const existingLoans = customLoans.length > 0 ? customLoans : MOCK_HIGH_INTEREST_EMIS;

  // 1. Calculate totals across fragmented loans
  const totalOutstandingBalance = existingLoans.reduce(
    (sum, loan) => sum + loan.outstandingBalance,
    0
  );

  const totalCurrentMonthlyPayout = existingLoans.reduce(
    (sum, loan) => sum + loan.monthlyEMI,
    0
  );

  // 2. Weighted average interest rate based on loan sizes
  const weightedInterestSum = existingLoans.reduce(
    (sum, loan) => sum + loan.outstandingBalance * loan.interestRateAPR,
    0
  );
  const weightedAverageInterestAPR =
    totalOutstandingBalance > 0
      ? Number((weightedInterestSum / totalOutstandingBalance).toFixed(1))
      : 29.8;

  // 3. Calculate Paytm Consolidated EMI at 14% APR
  const paytmConsolidatedMonthlyEMI = calculateReducingEMI(
    totalOutstandingBalance,
    targetAPR,
    targetTenure
  );

  // 4. Calculate savings
  const monthlySavings = Math.max(0, totalCurrentMonthlyPayout - paytmConsolidatedMonthlyEMI);
  const annualSavings = monthlySavings * 12;
  const savingsPercentage =
    totalCurrentMonthlyPayout > 0
      ? Math.round((monthlySavings / totalCurrentMonthlyPayout) * 100)
      : 0;

  // 5. NACH penalty risk savings (avg bounce fee in India is ₹450-₹500 per loan per failed mandate)
  const nachBounceRiskSavedPerYear = existingLoans.length * 450 * 2; // assuming 2 missed dates risk avoided

  // 6. CIBIL score boost projection (closing multiple high-utilization short-term unsecured BNPLs)
  const cibilBoostProjectionPoints = existingLoans.length >= 3 ? 35 : 20;

  // 7. Conversational pitch for LLM voice agent
  const llmPitchText = `I noticed you are paying ${formatINR(
    totalCurrentMonthlyPayout
  )} a month across ${existingLoans.length} different loan apps at high interest (averaging ${weightedAverageInterestAPR}% APR). I can consolidate all of this into one single Paytm loan at 14% APR today. You will save ${formatINR(
    monthlySavings
  )} a month, and only have to remember one single date. Should I process this?`;

  return {
    hasHighInterestDebt: existingLoans.length > 1 && weightedAverageInterestAPR >= 20,
    totalLoansCount: existingLoans.length,
    existingLoans,
    totalOutstandingBalance,
    totalCurrentMonthlyPayout,
    weightedAverageInterestAPR,
    paytmConsolidatedAPR: targetAPR,
    consolidatedTenureMonths: targetTenure,
    paytmConsolidatedMonthlyEMI,
    monthlySavings,
    annualSavings,
    savingsPercentage,
    dueDatesConsolidatedTo: 5,
    datesReducedCount: existingLoans.length - 1,
    nachBounceRiskSavedPerYear,
    cibilBoostProjectionPoints,
    llmPitchText,
  };
}
