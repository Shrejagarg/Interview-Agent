import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MicButton } from "./MicButton";

function renderMic(overrides: Partial<Parameters<typeof MicButton>[0]> = {}) {
  const props = {
    recording: false,
    disabled: false,
    onStart: vi.fn(),
    onStop: vi.fn(),
    ...overrides,
  };
  render(<MicButton {...props} />);
  return props;
}

const POINTER = { pointerId: 1, pointerType: "mouse", isPrimary: true } as const;

describe("MicButton", () => {
  it("shows an idle label and aria-pressed=false by default", () => {
    renderMic();
    expect(screen.getByTestId("mic-label")).toHaveTextContent("Hold to speak");
    expect(screen.getByRole("button", { name: /hold to record/i })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });

  it("labels the recording state for assistive tech", () => {
    const props = renderMic({ recording: true });
    const btn = screen.getByRole("button", { name: /stop recording and send/i });
    expect(btn).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("mic-label")).toHaveTextContent("Release to send");
    expect(props.onStart).not.toHaveBeenCalled();
  });

  it("starts on pointer-down and stops on pointer-up (hold-to-talk)", () => {
    const props = renderMic();
    const mic = screen.getByRole("button", { name: /hold to record/i });

    fireEvent.pointerDown(mic, POINTER);
    expect(props.onStart).toHaveBeenCalledTimes(1);

    fireEvent.pointerUp(mic, POINTER);
    expect(props.onStop).toHaveBeenCalledTimes(1);
  });

  it("ignores an extra pointer-down while a hold is already in flight", () => {
    const props = renderMic();
    const mic = screen.getByRole("button", { name: /hold to record/i });

    fireEvent.pointerDown(mic, POINTER);
    fireEvent.pointerDown(mic, POINTER);
    expect(props.onStart).toHaveBeenCalledTimes(1);

    fireEvent.pointerUp(mic, POINTER);
    expect(props.onStop).toHaveBeenCalledTimes(1);
  });

  it("stops on pointer-cancel and pointer-leave as a safety net", () => {
    const props = renderMic();
    const mic = screen.getByRole("button", { name: /hold to record/i });

    fireEvent.pointerDown(mic, POINTER);
    fireEvent.pointerCancel(mic);
    expect(props.onStop).toHaveBeenCalledTimes(1);

    fireEvent.pointerDown(mic, POINTER);
    fireEvent.pointerLeave(mic);
    expect(props.onStop).toHaveBeenCalledTimes(2);
  });

  it("never starts or stops while disabled", () => {
    const props = renderMic({ disabled: true });
    const mic = screen.getByRole("button", { name: /hold to record/i });

    fireEvent.pointerDown(mic, POINTER);
    fireEvent.pointerUp(mic, POINTER);
    expect(props.onStart).not.toHaveBeenCalled();
    expect(props.onStop).not.toHaveBeenCalled();
    expect(mic).toBeDisabled();
    expect(mic).toHaveAttribute("aria-disabled", "true");
  });

  it("toggles on via Enter and ignores Space while the finger is down", async () => {
    const user = userEvent.setup();
    const props = renderMic();
    const mic = screen.getByRole("button", { name: /hold to record/i });
    mic.focus();

    await user.keyboard("{Enter}");
    expect(props.onStart).toHaveBeenCalledTimes(1);

    await user.keyboard(" ");
    expect(props.onStart).toHaveBeenCalledTimes(1);
    expect(props.onStop).not.toHaveBeenCalled();
  });

  it("stops an active recording via Enter or Space and never restarts", async () => {
    const user = userEvent.setup();
    const props = renderMic({ recording: true });
    const mic = screen.getByRole("button", { name: /stop recording and send/i });
    mic.focus();

    await user.keyboard("{Enter}");
    expect(props.onStop).toHaveBeenCalledTimes(1);
    expect(props.onStart).not.toHaveBeenCalled();

    await user.keyboard(" ");
    expect(props.onStop).toHaveBeenCalledTimes(2);
    expect(props.onStart).not.toHaveBeenCalled();
  });

  it("releases an in-flight hold when the element loses focus", () => {
    const props = renderMic();
    const mic = screen.getByRole("button", { name: /hold to record/i });

    mic.focus();
    fireEvent.pointerDown(mic, POINTER);
    mic.blur();

    expect(props.onStop).toHaveBeenCalledTimes(1);
    expect(props.onStart).toHaveBeenCalledTimes(1);
  });
});