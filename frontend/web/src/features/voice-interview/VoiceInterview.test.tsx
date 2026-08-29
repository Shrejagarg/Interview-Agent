import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { axe } from "vitest-axe";
import { render } from "@/test/test-utils";
import { VoiceInterview } from "./VoiceInterview";
import {
  MockSpeechRecognition,
  MockUtterance,
  installFakeSpeech,
  resetFakeSpeech,
  uninstallFakeSpeech,
} from "@/test/fakes/speech";

const SESSION = "sess_123";
const DOMAIN = "backend";
const Q1 = "Walk me through your last production incident.";
const Q2 = "How do you review a pull request?";
const Q3 = "Tell me about a time you had to say no to a stakeholder.";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: pushMock }),
  usePathname: () => "/voice",
  useSearchParams: () => new URLSearchParams(),
  useServerInsertedHTML: () => null,
}));

let answerCalls = 0;
let followupCalls = 0;
let lastAnswerBody: Record<string, unknown> | null = null;
let lastAuthHeader: string | null = null;

function questionResponse(
  question: string,
  index: number,
  total: number,
  id = `q${index}`
) {
  return { id, topic: "Backend", difficulty: "medium", question, index, total };
}

function standardRequests() {
  return [
    http.get(
      `http://localhost:8000/api/interviews/${SESSION}/question`,
      () => HttpResponse.json(questionResponse(Q1, 1, 3))
    ),
    http.post(
      `http://localhost:8000/api/interviews/${SESSION}/answer`,
      async ({ request }) => {
        answerCalls += 1;
        lastAuthHeader = request.headers.get("authorization");
        lastAnswerBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          session_id: SESSION,
          answer_recorded: true,
          evaluation: {
            overall_score: 7.2,
            strengths: ["Clear structure"],
            weaknesses: ["Missing metrics"],
            follow_up: "",
          },
          has_next: true,
          next_question: questionResponse(Q2, 2, 3),
          progress: "2/3",
        });
      }
    ),
    http.post(
      `http://localhost:8000/api/interviews/${SESSION}/followup`,
      async ({ request }) => {
        followupCalls += 1;
        lastAnswerBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          session_id: SESSION,
          followup_evaluation: {
            score: 8.1,
            is_serious: true,
            improved: true,
            notes: "Good elaboration",
          },
          merged_score: 8.1,
          has_next: true,
          next_question: questionResponse(Q2, 2, 3),
          progress: "2/3",
        });
      }
    ),
  ];
}

const server = setupServer(...standardRequests());

beforeEach(() => {
  installFakeSpeech();
  localStorage.setItem("auth_token", "tok_voice");
  answerCalls = 0;
  followupCalls = 0;
  lastAnswerBody = null;
  lastAuthHeader = null;
  pushMock.mockClear();
});

afterEach(() => {
  server.resetHandlers();
  resetFakeSpeech();
  localStorage.removeItem("interview:voice-muted");
});

beforeAll(() => {
  server.listen();
});

afterAll(() => {
  server.close();
});

async function holdAndSay(text: string) {
  const mic = screen.getByRole("button", { name: /hold to record/i });
  fireEvent.pointerDown(mic);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /stop recording and send/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    )
  );
  act(() => {
    MockSpeechRecognition.last()?.emitResult(text, true);
  });
  fireEvent.pointerUp(mic);
}

async function holdAndRelease() {
  const mic = screen.getByRole("button", { name: /hold to record/i });
  fireEvent.pointerDown(mic);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /stop recording and send/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    )
  );
  fireEvent.pointerUp(mic);
}

function questionSection() {
  return screen.getByLabelText("Current question");
}

async function expectQuestion(text: string) {
  await waitFor(() =>
    expect(within(questionSection()).getByText(text)).toBeInTheDocument()
  );
}

describe("VoiceInterview", () => {
  it("loads the first question from /question and speaks it aloud", async () => {
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);

    await expectQuestion(Q1);
    expect(MockUtterance.last()!.text).toBe(Q1);
    expect(screen.getByText("1/3")).toBeInTheDocument();
    expect(screen.getByText("AI voice on")).toBeInTheDocument();
    expect(screen.getByLabelText("Current question")).toBeInTheDocument();
  });

  it("transcribes a held answer and submits standard text to /answer", async () => {
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    await expectQuestion(Q1);

    await holdAndSay("I debugged a memory leak in production.");

    // Standard text POST with question id + auth header
    await waitFor(() => expect(answerCalls).toBe(1));
    expect(lastAuthHeader).toBe("Bearer tok_voice");
    expect(lastAnswerBody).toEqual({
      question_id: "q1",
      answer_text: "I debugged a memory leak in production.",
      answer_time_seconds: expect.any(Number),
    });

    // Score bubble
    expect(await screen.findByText("7.2")).toBeInTheDocument();
    expect(screen.getByText(/clear structure/i)).toBeInTheDocument();
    expect(screen.getByText(/missing metrics/i)).toBeInTheDocument();

    // Next question loaded + spoken
    await expectQuestion(Q2);
    expect(MockUtterance.last()!.text).toBe(Q2);

    // Transcript log keeps a record for a11y/backup
    const transcript = screen.getByTestId("voice-transcript");
    expect(within(transcript).getByText(/memory leak/i)).toBeInTheDocument();
  });

  it("shows a hint and submits nothing when nothing was heard", async () => {
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    await expectQuestion(Q1);

    await holdAndRelease();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /didn't catch that/i
    );
    expect(answerCalls).toBe(0);
    expect(within(questionSection()).getByText(Q1)).toBeInTheDocument();
  });

  it("surfaces a mid-session mic error on release instead of submitting", async () => {
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    await expectQuestion(Q1);

    const mic = screen.getByRole("button", { name: /hold to record/i });
    fireEvent.pointerDown(mic);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /stop recording and send/i })).toHaveAttribute(
        "aria-pressed",
        "true"
      )
    );
    act(() => {
      MockSpeechRecognition.last()?.emitError("not-allowed");
    });
    fireEvent.pointerUp(mic);

    expect(await screen.findByRole("alert")).toHaveTextContent(/permission/i);
    expect(answerCalls).toBe(0);
  });

  it("mutes the AI voice, persists the choice, and replays on unmute", async () => {
    const user = userEvent.setup();
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    await expectQuestion(Q1);

    await user.click(screen.getByRole("button", { name: /mute ai voice/i }));
    expect(screen.getByRole("button", { name: /unmute ai voice/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(localStorage.getItem("interview:voice-muted")).toBe("1");
    expect(screen.getByText("AI voice muted")).toBeInTheDocument();

    // Speaking while muted is remembered, not spoken.
    const before = MockUtterance.instances.length;
    await holdAndSay("Muted answer still recorded");
    await expectQuestion(Q2);
    expect(MockUtterance.instances.length).toBe(before);

    // Unmuting replays the last line immediately.
    await user.click(screen.getByRole("button", { name: /unmute ai voice/i }));
    expect(localStorage.getItem("interview:voice-muted")).toBe("0");
    expect(MockUtterance.last()!.text).toBe(Q2);
  });

  it("recovers from a submit failure and lets the candidate try again", async () => {
    const user = userEvent.setup();
    let failing = false;
    server.use(
      http.post(
        `http://localhost:8000/api/interviews/${SESSION}/answer`,
        async ({ request }) => {
          answerCalls += 1;
          lastAnswerBody = (await request.json()) as Record<string, unknown>;
          if (failing) {
            return HttpResponse.json({ detail: "Model timed out" }, { status: 500 });
          }
          return HttpResponse.json({
            session_id: SESSION,
            answer_recorded: true,
            evaluation: {
              overall_score: 7.2,
              strengths: ["Clear structure"],
              weaknesses: [],
              follow_up: "",
            },
            has_next: true,
            next_question: questionResponse(Q2, 2, 3),
            progress: "2/3",
          });
        }
      )
    );
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    await expectQuestion(Q1);

    failing = true;
    await holdAndSay("First attempt");
    expect(await screen.findByRole("alert")).toHaveTextContent(/model timed out/i);
    expect(within(questionSection()).getByText(Q1)).toBeInTheDocument();

    failing = false;
    await holdAndSay("Second attempt");
    expect(await screen.findByText("7.2")).toBeInTheDocument();
    await expectQuestion(Q2);
    expect(answerCalls).toBe(2);
  });

  it("ends the session with a report link when there is no next question", async () => {
    server.use(
      http.post(
        `http://localhost:8000/api/interviews/${SESSION}/answer`,
        () =>
          HttpResponse.json({
            session_id: SESSION,
            answer_recorded: true,
            evaluation: {
              overall_score: 9.0,
              strengths: [],
              weaknesses: [],
              follow_up: "",
            },
            has_next: false,
            next_question: null,
            progress: "3/3",
          })
      )
    );
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    await expectQuestion(Q1);

    await holdAndSay("My final answer");
    expect(await screen.findByText("Interview complete")).toBeInTheDocument();
    expect(screen.getByText("9.0/10")).toBeInTheDocument();
    const reportLink = screen.getByRole("link", { name: /view your report/i });
    expect(reportLink).toHaveAttribute("href", `/results/${SESSION}`);
  });

  it("asks a follow-up, submits it to /followup, and merges the score", async () => {
    server.use(
      http.post(
        `http://localhost:8000/api/interviews/${SESSION}/answer`,
        () => {
          answerCalls += 1;
          return HttpResponse.json({
            session_id: SESSION,
            answer_recorded: true,
            evaluation: {
              overall_score: 6.3,
              strengths: ["Clear structure"],
              weaknesses: ["Light on detail"],
              follow_up: "Can you expand on that?",
            },
            has_next: false,
            next_question: null,
            follow_up: "Can you expand on that? Give me a concrete example.",
            progress: "1/2",
          });
        }
      )
    );
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    await expectQuestion(Q1);

    await holdAndSay("I handle incidents by focusing on impact first.");
    await waitFor(() => expect(answerCalls).toBe(1));
    expect(await screen.findByText("6.3")).toBeInTheDocument();

    // The follow-up becomes the live question and is spoken.
    await expectQuestion("Can you expand on that? Give me a concrete example.");
    expect(MockUtterance.last()!.text).toBe(
      "Can you expand on that? Give me a concrete example."
    );

    await holdAndSay("For example, the queue pileup last month…");
    await waitFor(() => expect(followupCalls).toBe(1));
    expect(lastAnswerBody).toEqual({
      answer_text: "For example, the queue pileup last month…",
      answer_time_seconds: expect.any(Number),
    });

    expect(await screen.findByText("8.1")).toBeInTheDocument();

    // Follow-up unlocked the next regular question.
    await expectQuestion(Q2);
    expect(MockUtterance.last()!.text).toBe(Q2);
  });

  it("surfaces a session-level load failure and retries it", async () => {
    const user = userEvent.setup();
    let failing = true;
    server.use(
      http.get(`http://localhost:8000/api/interviews/${SESSION}/question`, () => {
        if (failing) {
          return HttpResponse.json({ detail: "Backend warming up" }, { status: 503 });
        }
        return HttpResponse.json(questionResponse(Q1, 1, 3));
      })
    );

    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/backend warming up/i);

    failing = false;
    await user.click(screen.getByRole("button", { name: /try again/i }));

    await expectQuestion(Q1);
  });

  it("degrades gracefully when the browser has no speech recognition", async () => {
    uninstallFakeSpeech();
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);

    await expectQuestion(Q1);
    expect(
      screen.getByText(/live voice isn't available in this browser/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /hold to record/i })).toHaveAttribute(
      "aria-disabled",
      "true"
    );
  });

  it("switches to the typing mode via the session route", async () => {
    const user = userEvent.setup();
    render(<VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />);
    await expectQuestion(Q1);

    await user.click(screen.getByRole("button", { name: /type instead/i }));
    expect(pushMock).toHaveBeenCalledWith(
      `/interview/${DOMAIN}/${SESSION}?mode=text`
    );
  });

  it("has no axe accessibility violations in the question phase", async () => {
    const { container } = render(
      <VoiceInterview sessionId={SESSION} domainSlug={DOMAIN} />
    );
    await expectQuestion(Q1);
    await waitFor(() => expect(MockUtterance.last()?.text).toBe(Q1));
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});