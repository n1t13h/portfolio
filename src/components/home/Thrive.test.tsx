import { describe, it, expect, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { mockMatchMedia } from "@/test/utils";
import { BlurWords } from "./Thrive";

describe("BlurWords", () => {
  it("shows every word solid under reduced motion", () => {
    mockMatchMedia("(prefers-reduced-motion: reduce)", true);
    render(<BlurWords text="one two three" />);
    const words = screen.getAllByTestId("blur-word");
    expect(words).toHaveLength(3);
    words.forEach((w) => expect(w).toHaveAttribute("data-in", "true"));
  });

  it("starts blurred below the fold and reveals words as it scrolls in", () => {
    const rect = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect");
    rect.mockReturnValue({ top: 2000, height: 200 } as DOMRect);
    render(<BlurWords text="one two three" />);
    screen.getAllByTestId("blur-word").forEach((w) => expect(w).toHaveAttribute("data-in", "false"));
    rect.mockReturnValue({ top: -400, height: 200 } as DOMRect);
    act(() => {
      window.dispatchEvent(new Event("scroll"));
    });
    screen.getAllByTestId("blur-word").forEach((w) => expect(w).toHaveAttribute("data-in", "true"));
    rect.mockRestore();
  });
});
