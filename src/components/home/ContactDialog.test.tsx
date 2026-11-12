import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderAt } from "@/test/utils";
import { apiBase } from "@/lib/api";
import { ContactDialog } from "./ContactDialog";

afterEach(() => vi.unstubAllGlobals());

const reply = (status: number, body: unknown = {}) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));

function Harness() {
  const [open, setOpen] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        reopen
      </button>
      <ContactDialog open={open} onOpenChange={setOpen} />
    </>
  );
}

async function fill(name = "Asha", email = "asha@example.com", message = "Let's build something.") {
  const dialog = screen.getByRole("dialog");
  if (name) await userEvent.type(within(dialog).getByLabelText("Name"), name);
  if (email) await userEvent.type(within(dialog).getByLabelText("Email"), email);
  if (message) await userEvent.type(within(dialog).getByLabelText("What's on your mind?"), message);
}

const send = () => userEvent.click(screen.getByRole("button", { name: "Send message" }));
// The dialog also has the built-in × (screen-reader name "Close"); the success state's own
// Close button renders before it.
const closeAfterSending = async () =>
  userEvent.click((await screen.findAllByRole("button", { name: "Close" }))[0]);

describe("ContactDialog", () => {
  it("opens from the Contact section on the home page", async () => {
    renderAt("/");
    await userEvent.click(await screen.findByRole("button", { name: "Send a message →" }));
    expect(await screen.findByRole("dialog", { name: "Send a message" })).toHaveTextContent(
      "Tell me a bit about it. I usually reply within a day.",
    );
  });

  it("catches a bad email before sending anything", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    render(<Harness />);
    await fill("Asha", "nitish@");
    await send();
    expect(screen.getByText("That email doesn't look right.")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("sends the message to the API and thanks the visitor", async () => {
    const fetch = vi.fn(() => reply(202, { status: "received" }));
    vi.stubGlobal("fetch", fetch);
    render(<Harness />);
    await fill();
    await send();

    expect(await screen.findByText("Thanks, got it.")).toBeInTheDocument();
    expect(screen.getByText("I'll reach out shortly.")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${apiBase()}/contact`);
    expect(init.method).toBe("POST");
    expect(init.credentials ?? "same-origin").not.toBe("include");
    expect(JSON.parse(init.body as string)).toEqual({
      name: "Asha",
      email: "asha@example.com",
      message: "Let's build something.",
      website: "",
    });

    await closeAfterSending();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("sends only once when Send is pressed twice", async () => {
    let finish: (r: Response) => void = () => {};
    const fetch = vi.fn(() => new Promise<Response>((resolve) => (finish = resolve)));
    vi.stubGlobal("fetch", fetch);
    render(<Harness />);
    await fill();
    await send();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(fetch).toHaveBeenCalledTimes(1);
    finish(new Response("{}", { status: 202 }));
    expect(await screen.findByText("Thanks, got it.")).toBeInTheDocument();
  });

  it.each([
    ["too many messages", () => reply(429, { detail: "too many messages, try again later" })],
    ["the server failing", () => reply(502)],
    ["no network", () => Promise.reject(new TypeError("Failed to fetch"))],
  ])("keeps what was typed when sending fails (%s)", async (_, failure) => {
    vi.stubGlobal("fetch", vi.fn(failure));
    render(<Harness />);
    await fill();
    await send();
    expect(
      await screen.findByText("Couldn't send that. Try again in a bit, or email contact@ntshptl.in."),
    ).toBeInTheDocument();
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("Name")).toHaveValue("Asha");
    expect(within(dialog).getByLabelText("Email")).toHaveValue("asha@example.com");
    expect(within(dialog).getByLabelText("What's on your mind?")).toHaveValue("Let's build something.");
  });

  it("shows the server's verdict on a field under that field", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => reply(422, { detail: [{ loc: ["body", "email"], msg: "string does not match pattern" }] })),
    );
    render(<Harness />);
    await fill();
    await send();
    expect(await screen.findByText("That email doesn't look right.")).toBeInTheDocument();
  });

  it("starts empty again after a message was sent", async () => {
    vi.stubGlobal("fetch", vi.fn(() => reply(202)));
    render(<Harness />);
    await fill();
    await send();
    await screen.findByText("Thanks, got it.");
    await closeAfterSending();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await userEvent.click(screen.getByRole("button", { name: "reopen" }));
    expect(within(await screen.findByRole("dialog")).getByLabelText("Name")).toHaveValue("");
  });
});
