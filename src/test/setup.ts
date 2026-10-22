import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach } from "vitest";
import { resetMatchMedia } from "./matchMedia";

resetMatchMedia();

class IntersectionObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}
Object.defineProperty(window, "IntersectionObserver", {
  writable: true,
  configurable: true,
  value: IntersectionObserverStub,
});

beforeEach(() => {
  sessionStorage.setItem("intro-played", "1");
});

afterEach(() => {
  resetMatchMedia();
  sessionStorage.clear();
});

// jsdom does not implement scrolling
window.scrollTo = (() => {}) as typeof window.scrollTo;
Element.prototype.scrollIntoView = () => {};
