import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { SiteNav } from "./SiteNav";
import { site } from "@/content/site";

describe("SiteNav", () => {
  it("underlines Photography on /photos routes", () => {
    render(<MemoryRouter initialEntries={["/photos/mumbai"]}><SiteNav /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Photography" })).toHaveAttribute("aria-current", "page");
  });
  it("points section links at the home page hashes", () => {
    render(<MemoryRouter initialEntries={["/photos"]}><SiteNav /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Work" })).toHaveAttribute("href", "/#work");
    expect(screen.getByRole("link", { name: "Résumé" })).toHaveAttribute("href", site.links.resume);
  });
  it("offers Résumé and Contact in the phone menu sheet", async () => {
    render(<MemoryRouter initialEntries={["/"]}><SiteNav /></MemoryRouter>);
    await userEvent.click(screen.getByRole("button", { name: "Menu" }));
    const sheet = within(await screen.findByRole("dialog"));
    expect(sheet.getByRole("link", { name: "Résumé" })).toHaveAttribute("href", site.links.resume);
    expect(sheet.getByRole("link", { name: "Contact" })).toHaveAttribute("href", "/#contact");
  });
});
