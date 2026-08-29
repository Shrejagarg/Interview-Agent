import { afterEach, expect, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import * as axeMatchers from "vitest-axe/matchers";

expect.extend(axeMatchers);

declare module "vitest" {
  interface Assertion<T = any> {
    toHaveNoViolations(): void;
  }
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
  window.localStorage.clear();
});

if (typeof Element.prototype.scrollIntoView !== "function") {
  Element.prototype.scrollIntoView = () => {};
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

class MockIntersectionObserver {
  constructor(..._args: unknown[]) {}
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  root = null;
  rootMargin = "";
  thresholds = [];
}
Object.defineProperty(window, "IntersectionObserver", {
  writable: true,
  value: MockIntersectionObserver,
});

class MockResizeObserver {
  constructor(..._args: unknown[]) {}
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
Object.defineProperty(window, "ResizeObserver", {
  writable: true,
  value: MockResizeObserver,
});

if (typeof Navigator !== "undefined") {
  Object.defineProperty(Navigator.prototype, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: async () => {
        const err = new Error("Microphone denied by default test stub");
        err.name = "NotAllowedError";
        throw err;
      },
    },
  });
}