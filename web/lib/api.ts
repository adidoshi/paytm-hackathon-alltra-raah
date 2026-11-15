export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Lang = "en" | "hi" | "mr";

export type Persona = {
  user_id: string;
  name: string;
  first_name: string;
  age: number;
  city: string;
  occupation: string;
  language: Lang;
  monthly_income: number;
  application: { product: string; amount: number; tenure_months: number };
};

export type Action = {
  id: string;
  reason_code: string;
  title: string;
  detail: string;
  binary: boolean;
  start: string;
  current: string;
  target: string;
  progress: number;
  done: boolean;
  due_day: number;
  paytm_action: { type: string; amount: number } | null;
};

export type Offer = {
  id: string;
  name: string;
  tagline: string;
  why: string;
  facts: [string, string][];
  accepted: boolean;
};

export type Journey = {
  user: Persona;
  lang: Lang;
  status: "new" | "rejected" | "eligible" | "approved" | "approved_direct";
  day: number;
  can_advance: boolean;
  application: { product: string; amount: number; tenure_months: number; emi: number; reference: string | null };
  reasons: { code: string; title: string; detail: string; resolved: boolean }[];
  explanation: { text: string; source: "llm" | "template"; model?: string } | null;
  offers: Offer[];
  plan: { readiness: number; eligible: boolean; actions: Action[] };
  notifications: { id: number; day: number; kind: "month" | "done" | "eligible"; title: string; body: string }[];
  feed: { day: number; source: string; text: string; amount: number; dir: "in" | "out" }[];
  snapshot: { score: number | null; utilisation: number | null; foir: number; on_time_cycles: number };
};

export type Health = {
  ok: boolean;
  llm: boolean;
  voice: boolean;
  explain_models: string[];
  agent_models: string[];
  tts: string | null;
  stt: string | null;
  speakers: Record<Lang, string>;
  mcp: string;
};

export type TraceEntry = { id: number; ts: number; kind: string; title: string; detail: string };

export type Audio = { audio_b64: string; mime: string; cached: boolean } | null;

export type ChatReply = {
  reply: string;
  tools: string[];
  card: "consent" | null;
  source: "llm" | "template";
  model?: string;
  lang: Lang;
  audio: Audio;
  transcript?: string;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API + path, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

const post = <T,>(path: string, body: unknown) =>
  call<T>(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  health: () => call<Health>("/api/health"),
  personas: () => call<Persona[]>("/api/personas"),
  journey: (user_id: string, lang: Lang) => call<Journey>(`/api/journey/${user_id}?lang=${lang}`),
  apply: (user_id: string, amount: number, tenure_months: number, lang: Lang) =>
    post<Journey>("/api/applications", { user_id, amount, tenure_months, lang }),
  acceptOffer: (user_id: string, offer_id: string, lang: Lang) =>
    post<Journey>("/api/offers/accept", { user_id, offer_id, lang }),
  advance: (user_id: string, lang: Lang) => post<Journey>("/api/simulate/advance", { user_id, lang }),
  reapply: (user_id: string, lang: Lang) => post<Journey>("/api/reapply", { user_id, lang, consent: true }),
  trace: (user_id: string, after: number) =>
    call<{ entries: TraceEntry[]; consents: { ts: number; scope: string; detail: string }[] }>(
      `/api/trace/${user_id}?after=${after}`,
    ),
  reset: () => post<{ ok: boolean }>("/api/demo/reset", {}),
  tts: (user_id: string, text: string, lang: Lang) =>
    post<NonNullable<Audio>>(`/api/tts?user_id=${user_id}`, { text, lang }),
  chat: (user_id: string, message: string, lang: Lang, speak: boolean) =>
    post<ChatReply>("/api/chat", { user_id, message, lang, speak }),
  voiceAsk: (user_id: string, lang: Lang, blob: Blob) => {
    const form = new FormData();
    form.append("user_id", user_id);
    form.append("lang", lang);
    form.append("file", blob, "question.webm");
    return call<ChatReply>("/api/voice/ask", { method: "POST", body: form });
  },
};

/** Indian digit grouping: 100000 -> ₹1,00,000 */
export const inr = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");

export function emi(principal: number, annualRate: number, months: number) {
  const r = annualRate / 12;
  const f = Math.pow(1 + r, months);
  return Math.round((principal * r * f) / (f - 1));
}
