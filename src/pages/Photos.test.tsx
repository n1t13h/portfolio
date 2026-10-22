import { describe, it, expect, afterEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderAt, mockMatchMedia } from "@/test/utils";
import { getPhotos } from "@/data/photos";

afterEach(() => mockMatchMedia("", false));

describe("Photos index", () => {
  it("lists collections as links to their essays", async () => {
    renderAt("/photos");
    const row = await screen.findByRole("link", { name: /ujjain · omkareshwar · indore/i });
    expect(row).toHaveAttribute("href", "/photos/ujjain-omkareshwar-indore");
    expect(row).toHaveTextContent("22 frames");
  });
  it("renders every non-excluded photo in the contact sheet", async () => {
    renderAt("/photos");
    expect(await screen.findAllByTestId("sheet-photo")).toHaveLength((await getPhotos()).length);
  });
  it("does not render the cursor stack on touch devices", async () => {
    mockMatchMedia("(hover: none)", true);
    renderAt("/photos");
    await screen.findAllByTestId("sheet-photo");
    expect(screen.queryByTestId("cursor-stack")).toBeNull();
  });
  it("renders the cursor stack on hover-capable devices", async () => {
    mockMatchMedia("(hover: hover)", true);
    renderAt("/photos");
    await screen.findAllByTestId("sheet-photo");
    expect(screen.getByTestId("cursor-stack")).toBeInTheDocument();
  });
  it("disables hover motion under reduced motion (class presence)", async () => {
    renderAt("/photos");
    const row = await screen.findByRole("link", { name: /ujjain · omkareshwar · indore/i });
    const title = row.querySelector("span:nth-child(2)")!;
    expect(title.className).toContain("motion-reduce:transition-none");
    expect(title.className).toContain("motion-reduce:group-hover/row:translate-x-0");
    expect(row.className).toContain("motion-reduce:transition-none");
    const [first] = await screen.findAllByTestId("sheet-photo");
    expect(first.querySelector("img")!.className).toContain("motion-reduce:transition-none");
  });
});
