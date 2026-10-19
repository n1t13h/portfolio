import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { pastSkipGrace } from "@/test/timing";
import { Intro, INTRO_KEY, shouldPlayIntro } from "./Intro";

describe("shouldPlayIntro", () => {
  it("plays once per session and never under reduced motion", () => {
    expect(shouldPlayIntro({ getItem: () => null }, false)).toBe(true);
    expect(shouldPlayIntro({ getItem: () => "1" }, false)).toBe(false);
    expect(shouldPlayIntro({ getItem: () => null }, true)).toBe(false);
  });
  it("treats an unavailable sessionStorage as already played", () => {
    expect(
      shouldPlayIntro(
        {
          getItem: () => {
            throw new Error("blocked");
          },
        },
        false,
      ),
    ).toBe(false);
  });
});

describe("<Intro />", () => {
  beforeEach(() => sessionStorage.removeItem(INTRO_KEY));
  afterEach(() => {
    vi.useRealTimers();
    document.body.style.overflow = "";
  });

  it("shows the wordmark and locks body scroll", async () => {
    render(<Intro onDone={() => {}} />);
    await act(async () => {});
    expect(screen.getByTestId("intro")).toHaveTextContent("nitish");
    expect(screen.getByTestId("intro")).toHaveTextContent("patel");
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("skips on keydown and marks the session", async () => {
    const done = vi.fn();
    render(<Intro onDone={done} />);
    await act(async () => {});
    await pastSkipGrace();
    await userEvent.keyboard("a");
    expect(done).toHaveBeenCalled();
    expect(sessionStorage.getItem(INTRO_KEY)).toBe("1");
    expect(document.body.style.overflow).toBe("");
  });

  it("finishes by itself after 3200ms", async () => {
    vi.useFakeTimers();
    const done = vi.fn();
    render(<Intro onDone={done} />);
    await act(async () => {});
    act(() => void vi.advanceTimersByTime(3199));
    expect(done).not.toHaveBeenCalled();
    act(() => void vi.advanceTimersByTime(1));
    expect(done).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem(INTRO_KEY)).toBe("1");
  });
});
