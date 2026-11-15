import { NextRequest, NextResponse } from "next/server";
import { EMIDetoxUser, CalculatedDetoxMath } from "@/lib/mockData";

const SARVAM_BASE_URL = "https://api.sarvam.ai";

export interface DetoxAIAnalysis {
  counselorPitch: string;
  partnerRouting: {
    partnerName: string;
    riskTier: string;
    interestOffered: string;
    routingJustification: string;
  };
  paytmROIJustification: string;
  source: "llm" | "fallback";
}

/**
 * Intelligent deterministic fallback generator if network or API key is unavailable
 */
function getPrecomputedAnalysis(user: EMIDetoxUser, math: CalculatedDetoxMath): DetoxAIAnalysis {
  if (user.userId === "priya" || user.cibilScore >= 700) {
    return {
      counselorPitch: `Priya, paying ₹${Math.round(math.totalCurrentMonthlyPayout).toLocaleString("en-IN")} across multiple revolving cards after your move is exhausting your hard-earned salary. Consolidating this into a single ₹${Math.round(math.paytmConsolidatedMonthlyEMI).toLocaleString("en-IN")} Paytm EMI cuts your finance charges from 38% down to 14% and puts ₹${Math.round(math.netMonthlySavings).toLocaleString("en-IN")} back in your pocket every month.`,
      partnerRouting: {
        partnerName: "Tata Capital / Aditya Birla Capital",
        riskTier: "Prime Tier (CIBIL 700+)",
        interestOffered: "14.0% APR Fixed",
        routingJustification: "Priya's stable IT salary (₹45,000) and 712 CIBIL score make her an ideal candidate for Tata Capital's prime refinance line, delivering instant balance transfer to clear HDFC and SBI cards.",
      },
      paytmROIJustification: `By consolidating ₹${Math.round(math.totalOutstandingAmount).toLocaleString("en-IN")} of competitor credit card balances, Paytm captures a prime customer with a 28-month clean bureau streak, earns 14% interest spread with near-zero credit loss, and locks in primary salary account stickiness.`,
      source: "fallback",
    };
  }

  if (user.userId === "sameer" || (user.cibilScore >= 650 && user.cibilScore < 700)) {
    return {
      counselorPitch: `Sameer, having 5 apps demanding payments on different dates is creating unnecessary panic and penalty fees after that seasonal dip. With one single Paytm EMI of ₹${Math.round(math.paytmConsolidatedMonthlyEMI).toLocaleString("en-IN")} on the 5th, your bike and cash loans are settled instantly, saving you ₹${Math.round(math.netMonthlySavings).toLocaleString("en-IN")} each month.`,
      partnerRouting: {
        partnerName: "Hero Fincorp (Paytm Lending Partner)",
        riskTier: "Near-Prime Tier (CIBIL 660-699)",
        interestOffered: "14.0% APR Refinance",
        routingJustification: "Hero Fincorp specializes in MSME and retail shop supervisor refinancing, overlooking the isolated 34-day bike DPD in favor of Sameer's steady shop cash flows.",
      },
      paytmROIJustification: `Paytm rescues an active merchant/retail employee on the verge of predatory loan delinquency, replacing 3 hostile creditors with a single Paytm UPI AutoPay mandate while earning a profitable 14% yield with zero customer acquisition cost.`,
      source: "fallback",
    };
  }

  // Default / Ravi
  return {
    counselorPitch: `Ravi, we understand you took these emergency loans for your family and bike repairs, but 32% APR and 3 different due dates are draining your delivery earnings. Let Paytm clear all 3 loans today into one simple EMI of ₹${Math.round(math.paytmConsolidatedMonthlyEMI).toLocaleString("en-IN")}, giving you ₹${Math.round(math.netMonthlySavings).toLocaleString("en-IN")} in monthly breathing room.`,
    partnerRouting: {
      partnerName: "In-House Paytm NBFC / KrazyBee Credit",
      riskTier: "Alternative Cash-Flow Underwriting (CIBIL 620-650)",
      interestOffered: "14.0% APR Refinance",
      routingJustification: "Traditional lenders reject Ravi due to thin bureau history, but Paytm's verified daily Swiggy payouts (₹28,000/mo) support a secure debt consolidation under in-house alternative credit models.",
    },
    paytmROIJustification: `By refinancing ₹${Math.round(math.totalOutstandingAmount).toLocaleString("en-IN")} of high-cost gig debt, Paytm protects a vital delivery earner from default, earns a clean 14% annual return, and secures 100% of his daily digital payment transactions on the Paytm platform.`,
    source: "fallback",
  };
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const user = body.user as EMIDetoxUser;
    const math = body.math as CalculatedDetoxMath;

    if (!user || !math) {
      return NextResponse.json({ error: "Missing user or math payload" }, { status: 400 });
    }

    const sarvamApiKey = process.env.SARVAM_API_KEY || "";
    const llmModel = process.env.SARVAM_LLM_MODEL || "sarvam-105b-conversations";

    if (!sarvamApiKey) {
      const fallback = getPrecomputedAnalysis(user, math);
      return NextResponse.json(fallback);
    }

    const systemPrompt = `You are the "Empathy & Conversion Engine" for Raah, Paytm's Fintech AI Agent.
You are evaluating a customer for the "EMI Detox" (Debt Consolidation) feature.

HARD CONSTRAINTS:
1. YOU MUST NOT CALCULATE OR INVENT MATH NUMBERS. All numbers are provided to you in the prompt by deterministic TypeScript code. Use these exact figures.
2. Return ONLY a valid JSON object matching the required schema. Do not write markdown, code blocks, or explanations outside the JSON.

JSON SCHEMA:
{
  "counselorPitch": "A highly empathetic, personalized 2-sentence pitch to the user acknowledging their specific behavioralContext stress and explaining how this Paytm consolidation loan gives them breathing room to maximize conversion.",
  "partnerRouting": {
    "partnerName": "Name of best lending partner (e.g. Tata Capital, Aditya Birla Capital, Hero Fincorp, or In-House Paytm NBFC)",
    "riskTier": "Prime (700+) / Near-Prime (660-699) / Alternative Underwriting (<650)",
    "interestOffered": "14.0% APR Fixed",
    "routingJustification": "Specific reason why this partner matches their CIBIL score and debt-to-income profile."
  },
  "paytmROIJustification": "A 1-2 sentence business note for hackathon judges explaining why rescuing this specific user is highly profitable for Paytm (yield, CAC savings, ecosystem lock-in)."
}`;

    const userMessage = `Customer Name: ${user.name}
Monthly Income: ₹${user.income.toLocaleString("en-IN")}
CIBIL Bureau Score: ${user.cibilScore}
Behavioral Context: ${user.behavioralContext}
Current High-Interest Debt:
- Outstanding: ₹${Math.round(math.totalOutstandingAmount).toLocaleString("en-IN")} across ${user.currentEMIs.length} loans
- Current Monthly Outflow: ₹${Math.round(math.totalCurrentMonthlyPayout).toLocaleString("en-IN")} (DTI: ${math.dtiBefore}%)
- Current Weighted Interest: ${math.weightedAverageAPR}% APR
- Paytm Consolidated Single Loan: ₹${Math.round(math.paytmConsolidatedMonthlyEMI).toLocaleString("en-IN")}/mo at ${math.paytmAPR}% APR
- Net Monthly Cash Savings: ₹${Math.round(math.netMonthlySavings).toLocaleString("en-IN")} (DTI reduced to ${math.dtiAfter}%)
- Due dates reduced from ${math.dueDatesCountBefore} separate dates to 1 single auto-debit on the 5th.`;

    try {
      const response = await fetch(`${SARVAM_BASE_URL}/v1/chat/completions`, {
        method: "POST",
        headers: {
          "api-subscription-key": sarvamApiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: llmModel,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userMessage },
          ],
          temperature: 0.2,
          max_tokens: 600,
        }),
      });

      if (!response.ok) {
        throw new Error(`Sarvam LLM failed with status ${response.status}`);
      }

      const data = await response.json();
      let rawContent = data.choices?.[0]?.message?.content || "";
      rawContent = rawContent.replace(/<think>[\s\S]*?<\/think>/g, "").trim();

      // Extract JSON if wrapped in markdown
      const jsonMatch = rawContent.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        return NextResponse.json({
          counselorPitch: parsed.counselorPitch,
          partnerRouting: parsed.partnerRouting,
          paytmROIJustification: parsed.paytmROIJustification,
          source: "llm",
        });
      }
      throw new Error("Could not parse JSON from LLM response");
    } catch (llmErr) {
      console.warn("[emi-detox] LLM call failed, returning calibrated precomputed analysis:", llmErr);
      const fallback = getPrecomputedAnalysis(user, math);
      return NextResponse.json(fallback);
    }
  } catch (error: unknown) {
    console.error("[emi-detox] Fatal error:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
