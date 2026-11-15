import { NextRequest, NextResponse } from "next/server";
import { calculateEMIDetox, EMIDetoxResult } from "@/lib/emi-logic";

const SARVAM_BASE_URL = "https://api.sarvam.ai";

const LANG_MAP: Record<string, { code: string; name: string }> = {
  en: { code: "en-IN", name: "Indian English" },
  hi: { code: "hi-IN", name: "Hindi" },
  mr: { code: "mr-IN", name: "Marathi" },
};

/**
 * Call Sarvam Speech-to-Text (Saaras:v4 / Saaras:v3)
 */
async function callSarvamSTT(
  audioBuffer: ArrayBuffer,
  mimeType: string,
  apiKey: string,
  model: string = "saaras:v4",
  lang: string = "en"
): Promise<{ transcript: string; languageCode?: string }> {
  const formData = new FormData();
  const cleanMime = (mimeType || "audio/webm").split(";")[0].trim().toLowerCase();
  const ext = cleanMime.includes("wav")
    ? "wav"
    : cleanMime.includes("mp4")
    ? "mp4"
    : cleanMime.includes("ogg")
    ? "ogg"
    : "webm";
  const blob = new Blob([audioBuffer], { type: cleanMime });
  formData.append("file", blob, `user_speech.${ext}`);
  formData.append("model", model);
  formData.append("mode", "transcribe");
  formData.append("language_code", "unknown");

  const response = await fetch(`${SARVAM_BASE_URL}/speech-to-text`, {
    method: "POST",
    headers: {
      "api-subscription-key": apiKey,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error("[chat-voice] Sarvam STT failed:", response.status, errorText);
    throw new Error(`Sarvam STT failed (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  const transcript = (data.transcript || "").trim();
  const languageCode = data.language_code || "";
  return { transcript, languageCode };
}

/**
 * Call Sarvam Text-to-Speech (Bulbul:v4-flash / Bulbul:v3)
 */
async function callSarvamTTS(
  text: string,
  targetLangCode: string,
  apiKey: string,
  model: string = "bulbul:v4-flash",
  speaker?: string
): Promise<{ audio_b64: string; mime: string } | null> {
  const cleanText = text
    .replace(/[#*_~`]/g, "")
    .replace(/\n+/g, " ")
    .trim();

  if (!cleanText) return null;

  const payload: Record<string, unknown> = {
    text: cleanText.slice(0, 2400),
    target_language_code: targetLangCode || "en-IN",
    model,
  };
  if (speaker) {
    payload.speaker = speaker;
  }

  const response = await fetch(`${SARVAM_BASE_URL}/text-to-speech`, {
    method: "POST",
    headers: {
      "api-subscription-key": apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errText = await response.text();
    console.error("[chat-voice] Sarvam TTS error:", response.status, errText);
    return null;
  }

  const data = await response.json();
  const audios: string[] = data.audios || [];
  if (audios.length === 0 || !audios[0]) {
    return null;
  }

  return {
    audio_b64: audios[0],
    mime: "audio/wav",
  };
}

/**
 * Call Sarvam-105B Indic Conversational LLM
 */
async function callSarvamLLM(
  systemPrompt: string,
  userMessage: string,
  apiKey: string,
  model: string = "sarvam-105b-conversations"
): Promise<string> {
  const response = await fetch(`${SARVAM_BASE_URL}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "api-subscription-key": apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userMessage },
      ],
      temperature: 0.3,
      max_tokens: 450,
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    console.error("[chat-voice] Sarvam LLM error:", response.status, errText);
    throw new Error(`Sarvam LLM failed (${response.status}): ${errText}`);
  }

  const data = await response.json();
  let text = data.choices?.[0]?.message?.content || "";
  text = text.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
  return text;
}

export async function POST(req: NextRequest) {
  try {
    const sarvamApiKey = process.env.SARVAM_API_KEY || "";
    const sttModel = process.env.SARVAM_STT_MODEL || "saaras:v4";
    const ttsModel = process.env.SARVAM_TTS_MODEL || "bulbul:v4-flash";
    const llmModel = process.env.SARVAM_LLM_MODEL || "sarvam-105b-conversations";

    const contentType = req.headers.get("content-type") || "";
    let userQuery = "";
    let lang = "en";

    // 1. Calculate EMI Detox facts
    const emiDetoxData: EMIDetoxResult = calculateEMIDetox();

    // 2. Parse Audio or Text Input
    if (contentType.includes("multipart/form-data")) {
      const formData = await req.formData();
      const file = formData.get("file") as File | null;
      const textParam = formData.get("text") as string | null;
      const langParam = formData.get("lang") as string | null;

      if (langParam) lang = langParam;

      if (file && file.size > 0) {
        if (!sarvamApiKey) {
          return NextResponse.json(
            { error: "SARVAM_API_KEY is not configured" },
            { status: 500 }
          );
        }
        const arrayBuffer = await file.arrayBuffer();
        const sttResult = await callSarvamSTT(
          arrayBuffer,
          file.type || "audio/webm",
          sarvamApiKey,
          sttModel,
          lang
        );
        userQuery = sttResult.transcript;
      } else if (textParam) {
        userQuery = textParam.trim();
      }
    } else if (contentType.includes("application/json")) {
      const jsonBody = await req.json();
      userQuery = jsonBody.message || jsonBody.text || "";
      if (jsonBody.lang) lang = jsonBody.lang;
    }

    if (!userQuery) {
      userQuery = "What are my loan options and can you review my debt?";
    }

    const langName = LANG_MAP[lang]?.name || "Indian English";
    const ttsSpeaker =
      lang === "mr"
        ? process.env.SARVAM_SPEAKER_MR || "nilesh_mr_conversation"
        : lang === "hi"
        ? process.env.SARVAM_SPEAKER_HI || "shubh_enhi_banking"
        : process.env.SARVAM_SPEAKER_EN || "shubh_enhi_banking";

    // 3. Strict System Prompt with EMI Detox & Alternative Loan Instructions
    const systemPrompt = `You are Raah, a warm, respectful and proactive fintech AI agent built by Team Alltra inside the Paytm app.
You are assisting a customer named Ravi whose recent personal loan was rejected, and who is currently paying multiple fragmented high-interest loans.

TARGET LANGUAGE: Reply in ${langName}. Common financial terms like loan, EMI, credit card, FD, UPI and CIBIL may stay in English.
Keep your response to 2 or 3 short, conversational sentences that sound completely natural when spoken aloud via voice TTS. Do not use bullet points or markdown symbols.

CRITICAL INSTRUCTION FOR EMI DETOX (PROACTIVE DEBT CONSOLIDATION):
If the user asks about their finances, loans, EMIs, or you detect high-interest loans in their data, proactively pitch the EMI Detox.
Say:
"I noticed you are paying ₹15,000 a month across 3 different loan apps at high interest. I can consolidate all of this into one single Paytm loan today. You will save ₹3,000 a month, and only have to remember one date. Should I process this?"

FACTS TO GROUND YOUR RESPONSE:
- Current Fragmented EMIs: LazyPay BNPL (24% APR, ₹3,850), KreditBee (30% APR, ₹5,800), HDFC Credit Card (36% APR, ₹6,200).
- Total current monthly outflow: ₹15,850 across 3 separate due dates (5th, 12th, 22nd).
- Paytm Consolidated Refinance: 1 Single Loan at 14% APR Flat.
- New Paytm Monthly EMI: ₹11,224 on the 5th of every month.
- Verified Monthly Cash Savings: ₹4,626/month (Over ₹55,000/year).
- Alternative Credit Builder: If they ask about rebuilding CIBIL, offer the FD-Backed Card (₹10,000 deposit earning 6.5% interest, gives instant ₹9,000 limit).

Strict Rule: Output only the agent's spoken reply.`;

    let replyText = "";
    if (sarvamApiKey) {
      try {
        replyText = await callSarvamLLM(systemPrompt, userQuery, sarvamApiKey, llmModel);
      } catch (llmErr) {
        console.warn("[chat-voice] Sarvam LLM failed, using grounded template pitch:", llmErr);
        replyText = `I noticed you are paying ₹15,000 a month across 3 different loan apps at high interest. I can consolidate all of this into one single Paytm loan today. You will save ₹3,000 a month, and only have to remember one date. Should I process this?`;
      }
    } else {
      replyText = `I noticed you are paying ₹15,000 a month across 3 different loan apps at high interest. I can consolidate all of this into one single Paytm loan today. You will save ₹3,000 a month, and only have to remember one date. Should I process this?`;
    }

    // 4. Generate Voice Playback via Sarvam Bulbul TTS
    let audioPayload: { audio_b64: string; mime: string } | null = null;
    if (sarvamApiKey) {
      try {
        const targetLangCode = LANG_MAP[lang]?.code || "en-IN";
        audioPayload = await callSarvamTTS(
          replyText,
          targetLangCode,
          sarvamApiKey,
          ttsModel,
          ttsSpeaker
        );
      } catch (ttsErr) {
        console.warn("[chat-voice] Sarvam TTS error:", ttsErr);
      }
    }

    return NextResponse.json({
      success: true,
      transcript: userQuery,
      reply: replyText,
      audio_b64: audioPayload?.audio_b64 || null,
      mime: audioPayload?.mime || "audio/wav",
      hasAudio: Boolean(audioPayload?.audio_b64),
      lang,
      emiDetox: emiDetoxData,
    });
  } catch (error: unknown) {
    console.error("[chat-voice] Unhandled error:", error);
    const msg = error instanceof Error ? error.message : "Internal Server Error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
