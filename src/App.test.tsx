import { screen } from "@testing-library/react";
import { renderAt } from "@/test/utils";

describe("App routing", () => {
  it("routes /photos/:slug to the collection page", () => {
    renderAt("/photos/mumbai");
    expect(screen.getByTestId("page-photo-collection")).toBeInTheDocument();
  });
  it("does not render a theme toggle", () => {
    renderAt("/");
    expect(screen.queryByRole("button", { name: /toggle theme/i })).toBeNull();
  });
});
