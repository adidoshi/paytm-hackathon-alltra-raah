"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Audio as AudioPayload, Lang } from "./api";
import { SPEECH_CODE } from "./strings";

/** Plays Sarvam audio when the API returns it, and falls back to the browser's own voice otherwise. */
export function useSpeaker() {
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stop = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    if (typeof window !== "undefined") window.speechSynthesis?.cancel();
    setSpeaking(false);
  }, []);

  const play = useCallback(
    (audio: AudioPayload, fallbackText: string, lang: Lang) => {
      stop();
      if (audio) {
        const el = new Audio(`data:${audio.mime};base64,${audio.audio_b64}`);
        audioRef.current = el;
        el.onended = () => setSpeaking(false);
        el.onerror = () => setSpeaking(false);
        setSpeaking(true);
        el.play().catch(() => setSpeaking(false));
        return;
      }
      if (typeof window === "undefined" || !window.speechSynthesis) return;
      const u = new SpeechSynthesisUtterance(fallbackText);
      u.lang = SPEECH_CODE[lang];
      u.rate = 0.95;
      u.onend = () => setSpeaking(false);
      u.onerror = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(u);
    },
    [stop],
  );

  useEffect(() => stop, [stop]);
  return { speaking, play, stop };
}

/** Push-to-talk recorder. start() begins, stop() resolves with the recorded audio. */
export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "";
    const r = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    chunks.current = [];
    r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
    r.start();
    rec.current = r;
    setRecording(true);
    // Sarvam's sync speech-to-text takes up to 30 seconds of audio.
    setTimeout(() => r.state === "recording" && r.stop(), 28000);
  }, []);

  const stop = useCallback(
    () =>
      new Promise<Blob | null>((resolve) => {
        const r = rec.current;
        if (!r) return resolve(null);
        r.onstop = () => {
          r.stream.getTracks().forEach((t) => t.stop());
          setRecording(false);
          rec.current = null;
          resolve(chunks.current.length ? new Blob(chunks.current, { type: r.mimeType || "audio/webm" }) : null);
        };
        if (r.state === "recording") r.stop();
        else r.onstop?.(new Event("stop"));
      }),
    [],
  );

  return { recording, start, stop };
}
