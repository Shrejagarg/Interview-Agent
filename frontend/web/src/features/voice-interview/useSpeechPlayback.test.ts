import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useSpeechSynthesis } from "./useSpeechSynthesis";
import {
  MockSpeechSynthesis,
  MockUtterance,
  installFakeSpeech,
  resetFakeSpeech,
  uninstallFakeSpeech,
} from "@/test/fakes/speech";

beforeEach(() => {
  installFakeSpeech();
});

describe("useSpeechSynthesis", () => {
  it("speaks text via the native speechSynthesis API", async () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("What is your approach to incidents?");
    });
    const utterance = MockUtterance.last()!;
    expect(utterance.text).toBe("What is your approach to incidents?");
    expect(MockSpeechSynthesis.last()!.speak).toHaveBeenCalledWith(utterance);
    await act(async () => {});
    expect(result.current.speaking).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("supersedes the previous utterance when a new one is spoken", async () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("A");
    });
    const first = MockUtterance.last()!;

    act(() => {
      result.current.say("B");
    });
    const second = MockUtterance.last()!;
    expect(second.text).toBe("B");
    expect(MockSpeechSynthesis.last()!.cancel).toHaveBeenCalledTimes(2);
    expect(second).not.toBe(first);
    await act(async () => {});
    expect(result.current.speaking).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("ignores an error from an utterance that was already superseded", async () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("A");
    });
    const first = MockUtterance.last()!;
    act(() => {
      result.current.say("B");
    });

    await act(async () => {
      first.onerror?.({ error: "synthesis-failed" });
    });
    expect(result.current.speaking).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("does not surface cancellation or interruption as errors", async () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("ABC");
    });
    const utterance = MockUtterance.last()!;

    await act(async () => {
      utterance.onerror?.({ error: "canceled" });
    });
    expect(result.current.error).toBeNull();
    expect(result.current.speaking).toBe(false);

    act(() => {
      result.current.say("DEF");
    });
    const second = MockUtterance.last()!;
    await act(async () => {
      second.onerror?.({ error: "interrupted" });
    });
    expect(result.current.error).toBeNull();
  });

  it("surfaces a real synthesis failure and stops speaking", async () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("DEF");
    });
    const utterance = MockUtterance.last()!;

    await act(async () => {
      utterance.onerror?.({ error: "synthesis-failed" });
    });
    expect(result.current.speaking).toBe(false);
    expect(result.current.error).toMatch(/voice playback failed/i);
  });

  it("surfaces an autoplay block as a specific error", async () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("ABC");
    });
    const utterance = MockUtterance.last()!;

    await act(async () => {
      utterance.onerror?.({ error: "not-allowed" });
    });
    expect(result.current.speaking).toBe(false);
    expect(result.current.error).toMatch(/isn't allowed/i);
  });

  it("recovers when speechSynthesis.speak throws", () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    MockSpeechSynthesis.last()!.speak.mockImplementationOnce(() => {
      throw new Error("engine down");
    });

    act(() => {
      result.current.say("ABC");
    });
    expect(result.current.speaking).toBe(false);
    expect(result.current.error).toBe("Voice playback failed.");
  });

  it("persists the mute preference, skips speech while muted, and replays the last line on unmute", () => {
    const { result, unmount } = renderHook(() => useSpeechSynthesis());

    expect(result.current.muted).toBe(false);
    act(() => {
      result.current.toggleMuted();
    });
    expect(result.current.muted).toBe(true);
    expect(localStorage.getItem("interview:voice-muted")).toBe("1");
    expect(MockSpeechSynthesis.last()!.cancel).toHaveBeenCalled();

    // Muted speech is remembered but not spoken out loud.
    act(() => {
      result.current.say("Silently remembered");
    });
    expect(MockUtterance.instances).toHaveLength(0);
    expect(MockSpeechSynthesis.last()!.speak).not.toHaveBeenCalled();

    // Unmuting replays the most recent line immediately.
    act(() => {
      result.current.toggleMuted();
    });
    expect(result.current.muted).toBe(false);
    expect(localStorage.getItem("interview:voice-muted")).toBe("0");
    expect(MockUtterance.last()!.text).toBe("Silently remembered");
    expect(MockSpeechSynthesis.last()!.speak).toHaveBeenCalledTimes(1);

    const auto = MockUtterance.last()!;
    act(() => auto.onstart?.());
    // A reload keeps the preference.
    unmount();
    const { result: reloaded } = renderHook(() => useSpeechSynthesis());
    expect(reloaded.current.muted).toBe(false);
  });

  it("honours an existing mute preference on mount", () => {
    localStorage.setItem("interview:voice-muted", "1");
    const { result } = renderHook(() => useSpeechSynthesis());
    expect(result.current.muted).toBe(true);
    act(() => {
      result.current.say("Ignored while muted");
    });
    expect(MockUtterance.instances).toHaveLength(0);
  });

  it("retry() replays the last spoken line", () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("Original");
    });
    expect(MockSpeechSynthesis.last()!.speak).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.retry();
    });
    const utterance = MockUtterance.last()!;
    expect(utterance.text).toBe("Original");
    expect(MockSpeechSynthesis.last()!.speak).toHaveBeenCalledTimes(2);
  });

  it("stop() cancels the queue and invalidates pending completion", async () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("Ongoing");
    });
    const utterance = MockUtterance.last()!;
    expect(result.current.speaking).toBe(true);

    act(() => {
      result.current.stop();
    });
    expect(result.current.speaking).toBe(false);
    expect(MockSpeechSynthesis.last()!.cancel).toHaveBeenCalled();

    await act(async () => {
      utterance.onend?.();
    });
    expect(result.current.speaking).toBe(false);
  });

  it("tolerates broken storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage denied");
    });
    const { result } = renderHook(() => useSpeechSynthesis());
    expect(result.current.muted).toBe(false);
    act(() => {
      result.current.toggleMuted();
    });
    expect(result.current.muted).toBe(true);
  });

  it("treats missing speech synthesis globals as graceful no-ops", () => {
    uninstallFakeSpeech();
    const { result } = renderHook(() => useSpeechSynthesis());
    expect(result.current.supported).toBe(false);
    expect(() => {
      act(() => {
        result.current.say("hello");
        result.current.retry();
        result.current.toggleMuted();
        result.current.stop();
      });
    }).not.toThrow();
    expect(result.current.speaking).toBe(false);
    expect(result.current.muted).toBe(true);
  });

  it("cancels pending speech on unmount", () => {
    const { result, unmount } = renderHook(() => useSpeechSynthesis());
    act(() => {
      result.current.say("Cleanup me");
    });
    expect(result.current.speaking).toBe(true);

    act(() => unmount());
    const synth = MockSpeechSynthesis.last()!;
    expect(synth.cancel).toHaveBeenCalled();
    expect(synth.speaking).toBe(false);
  });

  afterEach(() => {
    resetFakeSpeech();
  });
});