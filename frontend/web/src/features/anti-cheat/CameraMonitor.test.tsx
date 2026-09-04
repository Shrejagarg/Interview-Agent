import { describe, expect, it } from "vitest";
import { createRef } from "react";
import { render, screen } from "@testing-library/react";
import { CameraMonitor } from "./CameraMonitor";

describe("CameraMonitor (presentational)", () => {
  it("renders nothing when disabled", () => {
    const { container } = render(
      <CameraMonitor enabled={false} videoRef={createRef()} status="prompting" />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the preview video and status label when active", () => {
    render(<CameraMonitor videoRef={createRef()} status="active" />);
    expect(screen.getByLabelText("Interview camera preview")).toBeInTheDocument();
    expect(screen.getByText("CAMERA ON")).toBeInTheDocument();
  });

  it("shows a quiet chip (no preview) when permission is denied", () => {
    render(<CameraMonitor videoRef={createRef()} status="denied" />);
    expect(screen.getByText("CAMERA BLOCKED")).toBeInTheDocument();
    expect(screen.queryByLabelText("Interview camera preview")).not.toBeInTheDocument();
  });

  it("shows CAMERA UNAVAILABLE when no device was found", () => {
    render(<CameraMonitor videoRef={createRef()} status="unsupported" />);
    expect(screen.getByText("CAMERA UNAVAILABLE")).toBeInTheDocument();
  });

  it("shows FACE OUT OF VIEW when the face is lost", () => {
    render(<CameraMonitor videoRef={createRef()} status="face_lost" />);
    expect(screen.getByText("FACE OUT OF VIEW")).toBeInTheDocument();
  });
});
