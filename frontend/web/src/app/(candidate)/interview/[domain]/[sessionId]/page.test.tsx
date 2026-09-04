import { beforeEach, describe, expect, it, vi } from "vitest";
import { createRef } from "react";
import { screen } from "@testing-library/react";
import { render } from "@/test/test-utils";
import InterviewRoomPage from "./page";

const { pushMock, cameraMock } = vi.hoisted(() => ({ pushMock: vi.fn(), cameraMock: vi.fn() }));

const DEFAULT_CAMERA = {
  videoRef: createRef<HTMLVideoElement>(),
  status: "active" as const,
  permission: null,
  error: null,
};

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  useParams: () => ({ sessionId: "sess_1", domain: "backend" }),
  useSearchParams: () => ({ get: () => "text" }),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: { id: "u1" }, loading: false }),
}));

vi.mock("@/lib/api", () => ({
  getQuestion: vi.fn(() =>
    Promise.resolve({
      id: "q1",
      topic: undefined,
      difficulty: "Medium",
      question: "How do you design an API?",
      index: 1,
      total: 5,
    })
  ),
  submitAnswer: vi.fn(),
  submitFollowup: vi.fn(),
}));

vi.mock("@/features/anti-cheat/useAntiCheat", () => ({
  useAntiCheat: () => ({ integrityScore: 100, reportFaceLost: vi.fn() }),
}));

vi.mock("@/features/anti-cheat/useCameraMonitor", () => ({
  useCameraMonitor: (...args: unknown[]) => cameraMock(...args),
}));

beforeEach(() => {
  pushMock.mockClear();
  cameraMock.mockReturnValue(DEFAULT_CAMERA);
});

describe("InterviewRoomPage (text mode)", () => {
  it("renders the question instead of crashing when topic is missing", async () => {
    render(<InterviewRoomPage />);
    expect(await screen.findByText(/How do you design an API\?/i)).toBeInTheDocument();
  });

  it("shows a paused banner and disables inputs while the face is lost", async () => {
    cameraMock.mockReturnValue({ ...DEFAULT_CAMERA, status: "face_lost" });
    render(<InterviewRoomPage />);
    await screen.findByText(/CAMERA CHECK — INPUTS PAUSED/i);

    expect(screen.getByText(/Look back at the camera to resume/i)).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText(/TYPE YOUR ANSWER HERE/i);
    expect(textarea).toBeDisabled();

    const submit = screen.getByRole("button", { name: /SUBMIT ANSWER/i });
    expect(submit).toBeDisabled();

    const skip = screen.getByRole("button", { name: /SKIP QUESTION/i });
    expect(skip).toBeDisabled();
  });

  it("keeps inputs enabled while the camera is active", async () => {
    cameraMock.mockReturnValue(DEFAULT_CAMERA);
    render(<InterviewRoomPage />);
    await screen.findByPlaceholderText(/TYPE YOUR ANSWER HERE/i);

    const textarea = screen.getByPlaceholderText(/TYPE YOUR ANSWER HERE/i);
    expect(textarea).not.toBeDisabled();
  });
});
