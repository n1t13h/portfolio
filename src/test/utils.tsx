import { render } from "@testing-library/react";
import App from "@/App";

export { mockMatchMedia } from "./matchMedia";

export function renderAt(path: string) {
  window.history.pushState({}, "", path);
  return render(<App />);
}
