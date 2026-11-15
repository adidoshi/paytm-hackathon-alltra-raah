// Records the Raah demo: drives the real app in Chrome like a user and captures frames.
// Run from the repo root, with the API (8000) and web (3000) running:
//   node demo/record.mjs
// Then build the video:  api/.venv/Scripts/python -m demo.build
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "demo", "out");
const FRAMES = path.join(OUT, "frames");
const WEB = process.env.DEMO_WEB || "http://localhost:3000";
const API = process.env.DEMO_API || "http://localhost:8000";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";

const scenes = Object.fromEntries(JSON.parse(fs.readFileSync(path.join(ROOT, "demo", "scenes.json"), "utf8")).map((s) => [s.id, s]));
const durations = JSON.parse(fs.readFileSync(path.join(OUT, "durations.json"), "utf8"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => Date.now() / 1000;

fs.rmSync(FRAMES, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });

// ------------------------------------------------------------------ overlay drawn inside the page
const OVERLAY = () => {
  if (window.__demo) return;
  const css = document.createElement("style");
  css.textContent = `
    nextjs-portal, [data-nextjs-toast], #__next-build-watcher { display: none !important; }
    #d-cursor { position: fixed; z-index: 99999; left: 960px; top: 1200px; width: 30px; height: 30px; pointer-events: none;
      transition: left .65s cubic-bezier(.4,0,.2,1), top .65s cubic-bezier(.4,0,.2,1); filter: drop-shadow(0 3px 6px rgba(0,0,0,.45)); }
    .d-ripple { position: fixed; z-index: 99998; width: 18px; height: 18px; margin: -9px 0 0 -9px; border-radius: 50%;
      border: 3px solid #7cb9f7; pointer-events: none; animation: d-rip .6s ease-out forwards; }
    @keyframes d-rip { to { transform: scale(3.4); opacity: 0; } }
    #d-caption { position: fixed; z-index: 99997; left: 50%; bottom: 26px; transform: translateX(-50%) translateY(20px); opacity: 0;
      max-width: 1300px; padding: 14px 28px; border-radius: 999px; background: rgba(7,14,26,.92); color: #fff;
      font: 600 26px/1.3 var(--font-grotesk), system-ui, sans-serif; letter-spacing: -.01em; text-align: center;
      box-shadow: 0 12px 40px rgba(0,0,0,.45), 0 0 0 1.5px rgba(124,185,247,.45); transition: all .45s ease; pointer-events: none; }
    #d-caption.on { opacity: 1; transform: translateX(-50%) translateY(0); }
    #d-spot { position: fixed; z-index: 99990; border-radius: 26px; pointer-events: none; opacity: 0;
      box-shadow: 0 0 0 9999px rgba(3,8,16,.55), 0 0 0 3px #7cb9f7, 0 0 40px 6px rgba(124,185,247,.55); transition: all .55s ease; }
    #d-card { position: fixed; inset: 0; z-index: 99995; display: flex; flex-direction: column; align-items: center; justify-content: center;
      background: radial-gradient(1100px 600px at 50% 0%, #1b4f9c 0%, #0d1829 62%); color: #fff; opacity: 0; transition: opacity .7s ease;
      pointer-events: none; text-align: center; font-family: var(--font-grotesk), system-ui, sans-serif; }
    #d-card.on { opacity: 1; }
    #d-card .k { font: 700 18px/1 var(--font-inter), sans-serif; letter-spacing: .18em; text-transform: uppercase; color: #7cb9f7; }
    #d-card .t { margin-top: 26px; font-weight: 700; font-size: 150px; line-height: 1; letter-spacing: -.04em; }
    #d-card .s { margin-top: 26px; font-size: 48px; font-weight: 500; color: rgba(255,255,255,.92); }
    #d-card .f { margin-top: 56px; font: 500 22px/1.4 var(--font-inter), sans-serif; color: rgba(255,255,255,.6); }
    #d-card .pills { margin-top: 40px; display: flex; gap: 18px; align-items: center; font: 700 24px var(--font-inter), sans-serif; }
    #d-card .no { padding: 10px 24px; border-radius: 999px; border: 2px solid #f39a3d; color: #f39a3d; }
    #d-card .yes { padding: 10px 24px; border-radius: 999px; background: #7cb9f7; color: #0d1829; }
  `;
  document.head.appendChild(css);
  const mk = (id, html = "") => { const d = document.createElement("div"); d.id = id; d.innerHTML = html; document.body.appendChild(d); return d; };
  mk("d-spot");
  mk("d-card");
  mk("d-caption");
  mk("d-cursor", `<svg viewBox="0 0 24 24" width="30" height="30"><path d="M4 2l16 9-7 2-3 7z" fill="#fff" stroke="#0d1829" stroke-width="1.6" stroke-linejoin="round"/></svg>`);
  window.__demo = {
    move(x, y) { const c = document.getElementById("d-cursor"); c.style.left = x - 4 + "px"; c.style.top = y - 2 + "px"; },
    ripple(x, y) { const r = document.createElement("div"); r.className = "d-ripple"; r.style.left = x + "px"; r.style.top = y + "px"; document.body.appendChild(r); setTimeout(() => r.remove(), 700); },
    caption(text) {
      const c = document.getElementById("d-caption");
      if (!text) { c.classList.remove("on"); return; }
      c.classList.remove("on");
      setTimeout(() => { c.textContent = text; c.classList.add("on"); }, 180);
    },
    spot(rect) {
      const s = document.getElementById("d-spot");
      if (!rect) { s.style.opacity = 0; return; }
      const p = 10;
      Object.assign(s.style, { left: rect.x - p + "px", top: rect.y - p + "px", width: rect.width + 2 * p + "px", height: rect.height + 2 * p + "px", opacity: 1 });
    },
    card(html) { const c = document.getElementById("d-card"); if (html) { c.innerHTML = html; c.classList.add("on"); } else c.classList.remove("on"); },
  };
};

// ------------------------------------------------------------------ helpers
const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ["--hide-scrollbars", "--force-device-scale-factor=1"] });
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const events = [];
const frames = [];

async function overlay() {
  await page.evaluate(OVERLAY);
}

async function caption(text) {
  await page.evaluate((t) => window.__demo.caption(t), text);
}

async function moveTo(locator) {
  await locator.scrollIntoViewIfNeeded();
  await sleep(250);
  const b = await locator.boundingBox();
  if (!b) throw new Error("not visible: " + locator);
  const x = b.x + b.width / 2, y = b.y + b.height / 2;
  await page.evaluate(([x, y]) => window.__demo.move(x, y), [x, y]);
  await sleep(720);
  return [x, y];
}

async function click(locator, after = 500) {
  const [x, y] = await moveTo(locator);
  await page.evaluate(([x, y]) => window.__demo.ripple(x, y), [x, y]);
  await locator.click();
  await sleep(after);
}

const btn = (text, exact = false) => page.getByRole("button", { name: text, exact }).first();

async function spot(locator) {
  if (!locator) return page.evaluate(() => window.__demo.spot(null));
  const b = await locator.boundingBox();
  await page.evaluate((r) => window.__demo.spot(r), b);
}

const phone = () => page.locator('div[class*="rounded-[46px]"]').first();
const card = (text) => page.locator("div.rounded-3xl", { hasText: text }).last();

// Scene runner: optional actions before the narration, then narration and actions together.
async function scene(id, during = async () => {}, { before = async () => {}, min = 0, audio = true } = {}) {
  await before();
  const s = scenes[id];
  await caption(s.caption);
  const start = now();
  if (audio && s.say) events.push({ id, t: start, file: `audio/${id}.wav` });
  await during();
  const need = Math.max(durations[id] || 0, min) + 0.7;
  const left = need - (now() - start);
  if (left > 0) await sleep(left * 1000);
  console.log(`scene ${id.padEnd(16)} ${(now() - start).toFixed(1)}s`);
}

// ------------------------------------------------------------------ record
await fetch(`${API}/api/demo/reset`, { method: "POST" });
await page.goto(WEB, { waitUntil: "networkidle", timeout: 120000 });
await sleep(1500);
await overlay();

// frame capture straight from Chrome
const cdp = await ctx.newCDPSession(page);
cdp.on("Page.screencastFrame", async (f) => {
  const file = `f${String(frames.length).padStart(5, "0")}.jpg`;
  fs.writeFileSync(path.join(FRAMES, file), Buffer.from(f.data, "base64"));
  frames.push({ file, t: now() });
  try { await cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }); } catch {}
});
await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
await sleep(300);

const TITLE = `<div class="k">Paytm Build for India AI Hackathon · Pune · Track 2</div>
  <div class="t">Raah</div><div class="s">No loan rejection is a dead end.</div>
  <div class="pills"><span class="no">Rejected</span><span style="color:#7cb9f7">→</span><span class="yes">Approved</span></div>
  <div class="f">Team Alltra · Atharva Bhosale, Aditya Doshi</div>`;
const CLOSE = `<div class="t" style="font-size:110px">Every “no” becomes<br/>“not yet.”</div>
  <div class="s" style="font-size:34px;margin-top:40px">Raah · Team Alltra</div>
  <div class="f">Sarvam-105B · Bulbul · Saaras · LangGraph · Account Aggregator · rules engine</div>`;

await page.evaluate((h) => window.__demo.card(h), TITLE);
await scene("title", async () => {}, { min: 4.5 });
await page.evaluate(() => window.__demo.card(null));
await sleep(700);

await scene("apply", async () => {
  await click(btn("पर्सनल लोन"), 900);
  await sleep(600);
  await click(btn("आता अर्ज करा"), 300);
});

await scene("rejected", async () => { await sleep(4200); });

await scene("hook", async () => {
  await sleep(500);
  await click(btn("मला राह दाखवा"), 600);
});

// Raah's own Marathi explanation, played from the same audio the app uses
const j = await (await fetch(`${API}/api/journey/ravi?lang=mr`)).json();
const tts = await (await fetch(`${API}/api/tts`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ text: j.explanation.text, lang: "mr" }) })).json();
fs.writeFileSync(path.join(OUT, "audio", "raah_mr.wav"), Buffer.from(tts.audio_b64, "base64"));
await scene("raah_voice", async () => {
  events.push({ id: "raah_voice", t: now(), file: "audio/raah_mr.wav", maxlen: 15 });
  await spot(phone());
}, { min: 15 });
await spot(null);

await scene("english", async () => {
  await sleep(2600);
  await click(btn("English", true), 1200);
});

await scene("consent", async () => {
  await click(btn("Proof", true), 1600);
  await spot(phone());
  await sleep(3500);
  await spot(null);
  await click(btn("Share statements securely"), 300);
});

await scene("findings", async () => {
  await sleep(2500);
  await spot(phone());
  await sleep(5000);
  await moveTo(page.getByText("Income found").first());
});

await scene("accuracy", async () => {
  await spot(null);
  await sleep(300);
  const panel = card("Statement reader");
  await moveTo(panel.getByText("right").first());
  await spot(panel);
});
await spot(null);

await scene("today", async () => {
  await click(btn("See what you can get today"), 900);
  await spot(card("Cash-flow loan of"));
  await sleep(3800);
  await spot(null);
  await click(page.getByRole("button", { name: "Start with this" }).nth(1), 600);
});

await scene("plan", async () => {
  await click(btn("Plan", true), 900);
  for (let i = 0; i < 3; i++) await click(btn("Simulate +30 days"), 1700);
}, { min: 9 });

await scene("consent_reapply", async () => {
  await click(btn("You now qualify"), 900);
  await click(btn("Review and re-apply"), 600);
});

await scene("approved", async () => {
  await click(btn("I agree, re-apply"), 400);
}, { min: 4 });

await scene("trace", async () => {
  await spot(page.locator("aside").first());
  await moveTo(page.locator("aside").getByText("Lender decision: APPROVED").last());
}, { min: 13 });
await spot(null);

await scene("priya_intro", async () => {
  await click(btn("Priya Kulkarni"), 900);
  await click(btn("Personal Loan"), 600);
  await click(btn("Apply now"), 300);
  await sleep(3800);
  await click(btn("Show me the way"), 700);
  await click(btn("Proof", true), 700);
  await click(btn("Share statements securely"), 300);
}, { min: 0 });

await scene("priya", async () => {
  await sleep(1200);
  await spot(phone());
  await moveTo(page.getByText("This debt is not on your credit report").first());
}, { min: 10 });
await spot(null);

await page.evaluate((h) => window.__demo.card(h), CLOSE);
await caption("");
await scene("close", async () => {}, { min: 5 });
await caption("");
await sleep(800);

await cdp.send("Page.stopScreencast");
await sleep(300);
fs.writeFileSync(path.join(OUT, "timeline.json"), JSON.stringify({ frames, events, end: now() }, null, 1));
console.log(`${frames.length} frames, ${(now() - frames[0].t).toFixed(1)}s`);
await browser.close();
