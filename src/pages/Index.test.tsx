import { describe, it, expect, vi, afterEach } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderAt } from "@/test/utils";
import { site } from "@/content/site";

afterEach(() => {
  delete window.Calendly;
});

describe("Index", () => {
  it("renders without the intro when sessionStorage access throws", () => {
    const spy = vi.spyOn(window, "sessionStorage", "get").mockImplementation(() => {
      throw new Error("blocked");
    });
    try {
      renderAt("/");
      expect(screen.getByTestId("page-home")).toBeInTheDocument();
      expect(screen.queryByTestId("intro")).toBeNull();
    } finally {
      spy.mockRestore();
    }
  });

  it("renders headline, three work cards and experience rows", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { level: 1, name: site.hero.headline })).toBeInTheDocument();
    expect(within(document.getElementById("work")!).getAllByRole("heading", { level: 3 })).toHaveLength(3);
    expect(within(document.getElementById("experience")!).getByText("Incubyte")).toBeInTheDocument();
    ["work", "about", "experience", "lens", "contact"].forEach((id) =>
      expect(document.getElementById(id)).not.toBeNull(),
    );
  });

  it("opens the Calendly popup from Book a call", async () => {
    const init = vi.fn();
    window.Calendly = { initPopupWidget: init };
    renderAt("/");
    await userEvent.click(screen.getByRole("button", { name: /book a call/i }));
    expect(init).toHaveBeenCalledWith({ url: "https://calendly.com/nitishp74/30min" });
  });

  it("falls back to mailto when Calendly is unavailable", async () => {
    const original = window.location;
    const loc = { href: "http://localhost/" };
    renderAt("/");
    delete window.location;
    (window as unknown as { location: unknown }).location = loc;
    try {
      await userEvent.click(screen.getByRole("button", { name: /book a call/i }));
      expect(loc.href).toBe("mailto:contact@ntshptl.in");
    } finally {
      (window as unknown as { location: unknown }).location = original;
    }
  });

  it("renders social links", () => {
    renderAt("/");
    const contact = within(document.getElementById("contact")!);
    expect(contact.getByRole("link", { name: /github/i })).toHaveAttribute("href", site.links.github);
    expect(contact.getByRole("link", { name: /email/i })).toHaveAttribute("href", `mailto:${site.links.email}`);
  });

  it("lens strip links each photo to the lightbox", async () => {
    renderAt("/");
    const links = await within(document.getElementById("lens")!).findAllByRole("link", { name: /photo:/i });
    expect(links.length).toBeGreaterThanOrEqual(12);
    expect(links[0].getAttribute("href")).toMatch(/^\/photos\?photo=/);
  });

  it("reserves the lens strip height so hash landings don't shift", () => {
    renderAt("/");
    expect(screen.getByTestId("lens-strip").className).toMatch(/min-h-\[220px\]/);
  });
});
