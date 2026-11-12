import { useState, type FormEvent } from "react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { site } from "@/content/site";
import { apiBase } from "@/lib/api";

type Field = "name" | "email" | "message";
type Fields = Record<Field, string>;
type FieldErrors = Partial<Record<Field, string>>;
type SendResult = "sent" | { fieldErrors: FieldErrors } | "failed";

const copy = site.contact.message;
// Mirrors backend/app/schemas/contact.py.
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const FIELDS: Field[] = ["name", "email", "message"];
const EMPTY: Fields = { name: "", email: "", message: "" };

function fieldError(field: Field): string {
  return field === "email" ? copy.badEmail : copy.badField;
}

function check(v: Fields): FieldErrors {
  const errors: FieldErrors = {};
  const name = v.name.trim();
  const email = v.email.trim();
  const message = v.message.trim();
  if (!name || name.length > 100) errors.name = fieldError("name");
  if (email.length > 254 || !EMAIL.test(email)) errors.email = fieldError("email");
  if (!message || message.length > 5000) errors.message = fieldError("message");
  return errors;
}

/** POSTs the message to the API. `website` is the honeypot: real visitors leave it empty. */
async function sendMessage(body: Fields & { website: string }): Promise<SendResult> {
  try {
    const res = await fetch(`${apiBase()}/contact`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.ok) return "sent";
    if (res.status === 422) {
      const data = (await res.json().catch(() => null)) as { detail?: { loc?: unknown[] }[] } | null;
      const fieldErrors: FieldErrors = {};
      for (const d of Array.isArray(data?.detail) ? data.detail : []) {
        const field = d.loc?.[1];
        if (FIELDS.includes(field as Field)) fieldErrors[field as Field] = fieldError(field as Field);
      }
      if (Object.keys(fieldErrors).length > 0) return { fieldErrors };
    }
    return "failed";
  } catch {
    return "failed";
  }
}

const label = "block text-[13px] text-[#6b6b6b]";
const input =
  "mt-1 block w-full border-0 border-b border-line bg-transparent px-0 py-2 text-[15px] outline-none focus:border-ink";
const error = "mt-1 block text-[13px] text-[#b42318]";
const pill =
  "mt-2 inline-flex min-h-11 items-center rounded-full bg-ink px-5 text-[15px] text-white disabled:opacity-50";

export function ContactDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [values, setValues] = useState<Fields>(EMPTY);
  const [website, setWebsite] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [state, setState] = useState<"idle" | "sending" | "sent" | "failed">("idle");

  const change = (open: boolean) => {
    if (!open && state === "sent") {
      setValues(EMPTY);
      setWebsite("");
      setState("idle");
    }
    onOpenChange(open);
  };

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (state === "sending") return;
    const found = check(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setState("sending");
    const result = await sendMessage({
      name: values.name.trim(),
      email: values.email.trim(),
      message: values.message.trim(),
      website,
    });
    if (result === "sent") setState("sent");
    else if (result === "failed") setState("failed");
    else {
      setErrors(result.fieldErrors);
      setState("idle");
    }
  }

  const field = (name: Field, text: string, area = false) => {
    const id = `contact-${name}`;
    const props = {
      id,
      className: area ? `${input} resize-none` : input,
      value: values[name],
      "aria-invalid": Boolean(errors[name]),
      "aria-describedby": errors[name] ? `${id}-error` : undefined,
    };
    return (
      <div>
        <label htmlFor={id} className={label}>
          {text}
        </label>
        {area ? (
          <textarea rows={4} {...props} onChange={(e) => setValues({ ...values, [name]: e.target.value })} />
        ) : (
          <input
            type={name === "email" ? "email" : "text"}
            autoComplete={name}
            {...props}
            onChange={(e) => setValues({ ...values, [name]: e.target.value })}
          />
        )}
        {errors[name] && (
          <span id={`${id}-error`} className={error}>
            {errors[name]}
          </span>
        )}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={change}>
      <DialogContent className="max-w-[440px] rounded-[10px] font-sans">
        {state === "sent" ? (
          <div className="py-2">
            <DialogTitle className="text-xl font-medium tracking-[-0.02em]">{copy.sentTitle}</DialogTitle>
            <DialogDescription className="mb-4 mt-1.5 text-sm text-[#6b6b6b]">{copy.sentLine}</DialogDescription>
            <button type="button" className={pill} onClick={() => change(false)}>
              {copy.close}
            </button>
          </div>
        ) : (
          <form noValidate onSubmit={submit} className="grid gap-3">
            <div>
              <DialogTitle className="text-xl font-medium tracking-[-0.02em]">{copy.title}</DialogTitle>
              <DialogDescription className="mt-1 text-sm text-[#6b6b6b]">{copy.subtitle}</DialogDescription>
            </div>
            {field("name", copy.nameLabel)}
            {field("email", copy.emailLabel)}
            {field("message", copy.messageLabel, true)}
            <input
              type="text"
              name="website"
              tabIndex={-1}
              autoComplete="off"
              aria-hidden="true"
              className="sr-only"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
            />
            {state === "failed" && <p className="text-[13px] text-[#b42318]">{copy.failed}</p>}
            <div>
              <button type="submit" className={pill} disabled={state === "sending"}>
                {copy.send}
              </button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
