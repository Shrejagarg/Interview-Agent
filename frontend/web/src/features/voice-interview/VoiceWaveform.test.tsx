import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { VoiceWaveform } from "./VoiceWaveform";

describe("VoiceWaveform", () => {
  it("renders 24 idle bars, hidden from the a11y tree", () => {
    const { container } = render(<VoiceWaveform active={false} />);
    const waveform = container.querySelector("[data-testid='voice-waveform']");
    expect(waveform).not.toBeNull();
    expect(waveform!.querySelectorAll(".voice-bar")).toHaveLength(24);
    expect(waveform!.querySelectorAll(".voice-bar-active")).toHaveLength(0);
    expect(waveform!.getAttribute("aria-hidden")).toBe("true");
    expect(waveform!.getAttribute("role")).toBe("presentation");
  });

  it("activates every bar while recording", () => {
    const { container } = render(<VoiceWaveform active={true} />);
    const waveform = container.querySelector("[data-testid='voice-waveform']")!;
    expect(waveform.querySelectorAll(".voice-bar-active")).toHaveLength(24);
    expect(
      waveform.querySelectorAll(".voice-bar-active:not([style])")
    ).toHaveLength(0);
  });

  it("renders the same bar count across states", () => {
    const idle = render(<VoiceWaveform active={false} />);
    const active = render(<VoiceWaveform active={true} />);
    expect(
      idle.container.querySelectorAll(".voice-bar").length
    ).toBe(active.container.querySelectorAll(".voice-bar").length);
  });
});