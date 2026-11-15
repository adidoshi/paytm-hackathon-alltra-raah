"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Audio as AudioPayload, Lang } from "./api";
import { SPEECH_CODE } from "./strings";

function base64ToBlob(b64: string, mime: string = "audio/wav"): Blob {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mime });
}

/** Plays Sarvam audio when the API returns it, and falls back to the browser's own voice otherwise. */
export function useSpeaker() {
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.onerror = null;
      audioRef.current.onended = null;
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    if (typeof window !== "undefined") {
      window.speechSynthesis?.cancel();
    }
    setSpeaking(false);
  }, []);

  const play = useCallback(
    (audio: AudioPayload, fallbackText: string, lang: Lang, onEnd?: () => void) => {
      stop();

      const playFallback = () => {
        if (typeof window === "undefined" || !window.speechSynthesis) {
          setSpeaking(false);
          onEnd?.();
          return;
        }
        window.speechSynthesis.cancel();
        const cleanText = fallbackText.replace(/[#*`_]/g, "").trim();
        const u = new SpeechSynthesisUtterance(cleanText);
        u.lang = SPEECH_CODE[lang] || "en-IN";
        u.rate = 1.0;
        u.onend = () => {
          setSpeaking(false);
          onEnd?.();
        };
        u.onerror = (e) => {
          console.warn("[speaker] Browser speechSynthesis error:", e);
          setSpeaking(false);
          onEnd?.();
        };
        setSpeaking(true);
        window.speechSynthesis.speak(u);
      };

      if (audio && audio.audio_b64) {
        try {
          const b64 = audio.audio_b64.trim();
          const mime = audio.mime || "audio/wav";
          const audioSrc = b64.startsWith("data:") ? b64 : `data:${mime};base64,${b64}`;
          const el = new Audio(audioSrc);
          el.volume = 1.0;
          audioRef.current = el;

          const finish = () => {
            el.onerror = null;
            el.onended = null;
            setSpeaking(false);
            onEnd?.();
          };

          el.onended = finish;
          el.onerror = (e) => {
            console.warn("[speaker] HTMLAudioElement error, falling back to browser speech:", e);
            finish();
            playFallback();
          };

          setSpeaking(true);
          const p = el.play();
          if (p !== undefined) {
            p.catch((err) => {
              console.warn("[speaker] play() was blocked or rejected, falling back to speech synthesis:", err);
              finish();
              playFallback();
            });
          }
          return;
        } catch (err) {
          console.warn("[speaker] Failed to construct audio from base64:", err);
          playFallback();
          return;
        }
      }

      playFallback();
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
    // 1. Explicit Secure Context check before attempting media access
    const isLocalhost = typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
    if (typeof window !== "undefined" && !window.isSecureContext && !isLocalhost) {
      console.error("[useRecorder] Microphone access failed: Browser is not in a Secure Context (HTTPS required).");
      throw new Error("Microphone requires HTTPS or localhost");
    }

    if (!navigator?.mediaDevices?.getUserMedia) {
      console.error("[useRecorder] Microphone access failed: navigator.mediaDevices.getUserMedia is not supported on this browser.");
      throw new Error("getUserMedia not supported");
    }

    try {
      // 1. getUserMedia wrapped in try/catch block
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/mp4")
        ? "audio/mp4"
        : "";

      const r = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      chunks.current = [];

      // 2. Accumulate chunks continuously
      r.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.current.push(e.data);
      };

      r.start(100);
      rec.current = r;
      setRecording(true);
      setTimeout(() => r.state === "recording" && r.stop(), 28000);
    } catch (err: unknown) {
      // 1. Specifically check if failed due to missing Secure Context or denied permissions
      const error = err as { name?: string };
      if (error?.name === "NotAllowedError" || error?.name === "PermissionDeniedError") {
        console.error("[useRecorder] Microphone access DENIED: The user or system blocked microphone permission.", err);
      } else if (typeof window !== "undefined" && !window.isSecureContext && !isLocalhost) {
        console.error("[useRecorder] Microphone access failed: Missing Secure Context (HTTPS required).", err);
      } else {
        console.error("[useRecorder] Unexpected error during getUserMedia:", err);
      }
      setRecording(false);
      throw err;
    }
  }, []);

  const stop = useCallback(
    () =>
      new Promise<Blob | null>((resolve) => {
        const r = rec.current;
        if (!r) return resolve(null);

        // 2. Wait for recorder.onstop event to assemble the Blob from audioChunks array
        r.onstop = () => {
          r.stream.getTracks().forEach((t) => t.stop());
          setRecording(false);
          rec.current = null;

          const finalBlob = chunks.current.length
            ? new Blob(chunks.current, { type: r.mimeType || "audio/webm" })
            : null;

          // 3. console.log the size of the final audio Blob (in bytes) to ensure not empty
          if (finalBlob) {
            console.log(`[useRecorder] Final audio Blob assembled: size=${finalBlob.size} bytes, type=${finalBlob.type}`);
          } else {
            console.error("[useRecorder] Final audio Blob is null or 0 bytes.");
          }

          resolve(finalBlob && finalBlob.size > 0 ? finalBlob : null);
        };

        // 2. Calling stop() triggers the onstop event; do NOT send immediately before onstop fires
        if (r.state === "recording") {
          r.stop();
        } else {
          r.onstop?.(new Event("stop"));
        }
      }),
    [],
  );

  return { recording, start, stop };
}
