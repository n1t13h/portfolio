import { screen } from "@testing-library/react";
import { it, expect } from "vitest";
import { renderAt } from "@/test/utils";

it("renders title, facts and numbered chapters", async () => {
  renderAt("/photos/ujjain-omkareshwar-indore");
  expect(await screen.findByRole("heading", { level: 1, name: "Ujjain · Omkareshwar · Indore" })).toBeInTheDocument();
  expect(screen.getByText("Sony ZV-E10")).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual(["Ujjain", "Omkareshwar", "Indore, Rajwada & Sarafa", "Indore Zoo"]);
});

it("shows a not-found state for an unknown slug", async () => {
  renderAt("/photos/nope");
  expect(await screen.findByText(/collection not found/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /all collections/i })).toHaveAttribute("href", "/photos");
});

it("links to the next collection, wrapping to the first", async () => {
  renderAt("/photos/elsewhere");
  expect(await screen.findByRole("link", { name: /next collection/i })).toHaveAttribute("href", "/photos/ujjain-omkareshwar-indore");
});
