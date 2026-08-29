import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test/test-utils";
import InterviewSetupPage from "./page";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ user: null }) }));
vi.mock("@/lib/api", () => ({
  listDomains: vi.fn(() =>
    Promise.resolve({
      domains: [{ slug: "backend", name: "Backend", description: "" }],
    })
  ),
  startInterview: vi.fn(() =>
    Promise.resolve({ session_id: "sess_mock_1" })
  ),
}));

beforeEach(() => {
  pushMock.mockClear();
});

describe("InterviewSetupPage", () => {
  it("defaults to the voice-first interface", async () => {
    render(<InterviewSetupPage />);
    await screen.findByText("Interview Agent");
    const voice = screen.getByRole("button", { name: /voice-first/i });
    const typing = screen.getByRole("button", { name: /typing only/i });
    expect(voice).toBeInTheDocument();
    expect(typing).toBeInTheDocument();
    expect(voice.className.includes("border-teal-500")).toBe(true);
  });

  it("blocks starting until a domain is selected", async () => {
    const user = userEvent.setup();
    render(<InterviewSetupPage />);
    await screen.findByText("Interview Agent");
    const start = screen.getByRole("button", { name: /start mock interview/i });
    expect(start).toBeDisabled();

    await user.selectOptions(screen.getByLabelText("Domain"), "backend");
    expect(start).toBeEnabled();
  });

  it("routes to the session with mode=voice by default", async () => {
    const user = userEvent.setup();
    render(<InterviewSetupPage />);
    await screen.findByText("Interview Agent");
    await user.selectOptions(screen.getByLabelText("Domain"), "backend");
    await user.click(screen.getByRole("button", { name: /start mock interview/i }));

    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/interview/backend/sess_mock_1?mode=voice")
    );
  });

  it("routes with mode=text when the typing interface is chosen", async () => {
    const user = userEvent.setup();
    render(<InterviewSetupPage />);
    await screen.findByText("Interview Agent");
    await user.selectOptions(screen.getByLabelText("Domain"), "backend");
    await user.click(screen.getByRole("button", { name: /typing only/i }));
    await user.click(screen.getByRole("button", { name: /start mock interview/i }));

    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/interview/backend/sess_mock_1?mode=text")
    );
  });
});