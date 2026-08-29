import { test, expect, Page } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(fakeSpeechRecognition);
});

function fakeSpeechRecognition() {
  const TRANSCRIPT =
    "I recently improved reliability for a checkout service by adding better error handling and monitoring.";

  class FakeRecognition {
    lang = "en-US";
    continuous = false;
    interimResults = true;
    maxAlternatives = 1;
    onstart: (() => void) | null = null;
    onresult: ((event: unknown) => void) | null = null;
    onend: (() => void) | null = null;
    onerror: ((event: unknown) => void) | null = null;

    start() {
      window.setTimeout(() => this.onstart && this.onstart(), 50);
      // Record the transcript while still "recording". A real API keeps
      // producing results (and only ends after the user aborts), so we never
      // fire onend here — the hook returns the transcript on release.
      window.setTimeout(() => {
        this.onresult &&
          this.onresult({
            resultIndex: 0,
            results: [
              { isFinal: true, length: 1, 0: { transcript: TRANSCRIPT } },
            ],
          });
      }, 300);
    }
    stop() {}
    abort() {}
  }

  const win = window as unknown as {
    SpeechRecognition?: unknown;
    webkitSpeechRecognition?: unknown;
  };
  win.SpeechRecognition = FakeRecognition;
  win.webkitSpeechRecognition = FakeRecognition;
}

async function speakAnswer(page: Page) {
  const idleMic = page.getByRole("button", {
    name: "Hold to record your answer",
  });
  const recordingMic = page.getByRole("button", {
    name: "Stop recording and send your answer",
  });
  await expect(idleMic).toBeVisible();
  await idleMic.hover();
  await page.mouse.down();
  // Fake recognition is async (onstart -> onresult -> onend); keep the button
  // held until the final transcript lands so stop() returns it.
  await expect(recordingMic).toBeVisible();
  await page.waitForTimeout(500);
  await page.mouse.up();
  await expect(idleMic).toBeVisible();
}

test("candidate registers and completes a full voice interview", async ({
  page,
}) => {
  const email = `e2e-${Date.now()}@test.io`;

  await page.goto("/register");
  await page.getByPlaceholder("Jane Doe").fill("E2E Voice Candidate");
  await page.getByPlaceholder("you@example.com").fill(email);
  await page.getByPlaceholder("Min 6 characters").fill("Passw0rd123!");
  await page.getByRole("button", { name: "Create Account" }).click();

  // / redirects candidates to /interview once the session is set.
  await page.waitForURL("**/interview");
  await page.selectOption("#interview-domain", "software_engineering");
  await page.getByLabel("Questions").fill("2");
  await page.getByRole("button", { name: "Start Mock Interview" }).click();

  await page.waitForURL(/\/interview\/[^/]+\/[^/]+/);

  // VoiceInterview loads the first question via getQuestion.
  const questionSection = page.locator(
    'section[aria-label="Current question"]'
  );
  await expect(questionSection.getByText("Interviewer")).toBeVisible();
  const firstQuestion = ((await questionSection.textContent()) ?? "").trim();

  // Answer the first question with the (fake) voice; mock 2-question session
  // advances to question 2/2 with feedback from the first answer.
  await speakAnswer(page);
  await expect(page.getByRole("status").getByText(/^\d+\.\d$/)).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText("2/2", { exact: true })).toBeVisible();
  await expect(questionSection).not.toHaveText(firstQuestion, {
    timeout: 15_000,
  });

  await speakAnswer(page);
  await expect(page.getByText("Interview complete")).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("link", { name: "View your report" }).click();
  await expect(
    page.getByRole("heading", { name: "Interview Report" })
  ).toBeVisible();
  await expect(
    page.getByText(/questions answered/).first()
  ).toBeVisible();
});

test("demo company can sign in and see the dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("you@example.com").fill("company@test.io");
  await page.getByPlaceholder("••••••••").fill("Passw0rd123!");
  await page.getByRole("button", { name: "Sign In" }).click();

  await page.waitForURL("**/dashboard");
  await expect(page.getByRole("heading", { name: /Dashboard/i })).toBeVisible();
});