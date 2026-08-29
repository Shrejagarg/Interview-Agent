import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useSpeechRecognition } from "./useSpeechRecognition";
import {
  MockSpeechRecognition,
  installFakeSpeech,
  uninstallFakeSpeech,
} from "@/test/fakes/speech";

beforeEach(() => {
  installFakeSpeech();
});

describe("useSpeechRecognition", () => {
  it("reports unsupported cleanly when no SpeechRecognition global exists", () => {
    uninstallFakeSpeech();
    const { result } = renderHook(() => useSpeechRecognition());
    expect(result.current.supported).toBe(false);

    let outcome: { ok: boolean; error?: string } | undefined;
    act(() => {
      outcome = result.current.start();
    });
    expect(outcome!.ok).toBe(false);
    expect(outcome!.error).toMatch(/isn't supported/i);
    expect(result.current.recording).toBe(false);
  });

  it("starts listening and returns the recognised text on stop", async () => {
    const { result } = renderHook(() => useSpeechRecognition());
    let outcome: { ok: boolean; error?: string } | undefined;
    act(() => {
      outcome = result.current.start();
    });
    expect(outcome!.ok).toBe(true);
    expect(result.current.recording).toBe(true);
    expect(result.current.error).toBeNull();

    const rec = MockSpeechRecognition.last()!;
    act(() => rec.emitResult("my spoken answer", true));

    let text: string | null = null;
    await act(async () => {
      text = result.current.stop();
    });
    expect(text).toBe("my spoken answer");
    expect(result.current.recording).toBe(false);
  });

  it("prefers the final transcript over interim placeholders", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitResult("my spoken", false));
    act(() => rec.emitResult("my spoken answer", false));
    act(() => rec.emitResult("my spoken answer is clear", true));

    let text: string | null = null;
    act(() => {
      text = result.current.stop();
    });
    expect(text).toBe("my spoken answer is clear");
  });

  it("joins multiple final results into one answer", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitResult("first sentence.", true));
    act(() => rec.emitResult("second sentence.", true));

    let text: string | null = null;
    act(() => {
      text = result.current.stop();
    });
    expect(text).toBe("first sentence. second sentence.");
  });

  it("returns the interim transcript when nothing was finalised", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitResult("still talking", false));

    let text: string | null = null;
    act(() => {
      text = result.current.stop();
    });
    expect(text).toBe("still talking");
  });

  it("returns null when nothing was heard", async () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    let text: string | null = "x";
    await act(async () => {
      text = result.current.stop();
    });
    expect(text).toBeNull();
  });

  it("returns null when stop is called before recording starts", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    let text: string | null = "x";
    act(() => {
      text = result.current.stop();
    });
    expect(text).toBeNull();
  });

  it("ignores a second start while already listening", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    let second: { ok: boolean; error?: string } | undefined;
    act(() => {
      second = result.current.start();
    });
    expect(second!.ok).toBe(false);
    expect(MockSpeechRecognition.instances).toHaveLength(1);
    expect(MockSpeechRecognition.last()!.start).toHaveBeenCalledTimes(1);
  });

  it("treats a no-speech error as an empty result without a user-facing error", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitError("no-speech"));

    expect(result.current.recording).toBe(false);
    expect(result.current.error).toBeNull();

    let text: string | null = "x";
    act(() => {
      text = result.current.stop();
    });
    expect(text).toBeNull();
  });

  it("maps a permission denial to a friendly hint", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitError("not-allowed"));

    expect(result.current.error).toMatch(/permission/i);
    expect(result.current.recording).toBe(false);
  });

  it("maps service-not-allowed to a permission hint too", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitError("service-not-allowed"));

    expect(result.current.error).toMatch(/permission/i);
  });

  it("maps a network error to a connection hint", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitError("network"));

    expect(result.current.error).toMatch(/network error/i);
  });

  it("maps audio-capture failures to a hardware hint", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitError("audio-capture"));

    expect(result.current.error).toMatch(/any audio/i);
  });

  it("falls back to a generic message for unknown errors", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => rec.emitError("bad-grammar"));

    expect(result.current.error).toMatch(/try again/i);
  });

  it("ticks the elapsed timer only while listening", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSpeechRecognition());
    await act(async () => {
      result.current.start();
    });
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(result.current.elapsedSeconds).toBeGreaterThan(2.9);

    await act(async () => {
      await result.current.stop();
    });
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.elapsedSeconds).toBeLessThan(4);
    vi.useRealTimers();
  });

  it("ignores results arriving on a superseded recognition session", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const first = MockSpeechRecognition.last()!;
    act(() => first.emitResult("hello", true));
    let text: string | null = null;
    act(() => {
      text = result.current.stop();
    });
    expect(text).toBe("hello");

    // Stale result from the abandoned first session must not leak forward.
    act(() => first.emitResult("stale interjection", true));

    act(() => result.current.start());
    const second = MockSpeechRecognition.last()!;
    act(() => second.emitResult("world", true));
    act(() => {
      text = result.current.stop();
    });
    expect(text).toBe("world");
  });

  it("maps a thrown native start() to a friendly error", () => {
    class ThrowingRecognizer {
      lang = "";
      continuous = false;
      interimResults = true;
      maxAlternatives = 1;
      onstart: (() => void) | null = null;
      onresult: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onend: (() => void) | null = null;
      start() {
        throw new Error("engine down");
      }
      abort() {}
      stop() {}
    }
    Object.defineProperty(window, "SpeechRecognition", {
      configurable: true,
      writable: true,
      value: ThrowingRecognizer,
    });

    const { result } = renderHook(() => useSpeechRecognition());
    let outcome: { ok: boolean; error?: string } | undefined;
    act(() => {
      outcome = result.current.start();
    });
    expect(outcome!.ok).toBe(false);
    expect(outcome!.error).toMatch(/couldn't start/i);
    expect(result.current.recording).toBe(false);
  });

  it("stops cleanly when the native recognizer ends the session on its own", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;
    act(() => rec.emitResult("partial", true));

    act(() => rec.emitEnd());

    expect(result.current.recording).toBe(false);
    expect(result.current.error).toBeNull();

    let text: string | null = "x";
    act(() => {
      text = result.current.stop();
    });
    expect(text).toBeNull();
  });

  it("aborts the native recognition and stops timers on unmount", () => {
    const { result, unmount } = renderHook(() => useSpeechRecognition());
    act(() => result.current.start());
    const rec = MockSpeechRecognition.last()!;

    act(() => unmount());

    expect(rec.abort).toHaveBeenCalledTimes(1);
  });
});