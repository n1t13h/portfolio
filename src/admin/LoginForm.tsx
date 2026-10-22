import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, type AdminApi } from "./api/client";

function explain(error: unknown): string {
  if (error instanceof ApiError && error.status === 429) {
    return "Too many attempts. Wait 15 minutes and try again.";
  }
  if (error instanceof ApiError && error.status === 401) {
    return "That didn't work. Check the details and try again.";
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}

export function LoginForm({ api, onSignedIn }: { api: AdminApi; onSignedIn: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login({ username, password, code: code.trim() });
      onSignedIn();
    } catch (e) {
      setError(explain(e));
      setCode("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-[420px] flex-col justify-center px-6">
      <h1 className="text-[34px] font-medium leading-[1.05] tracking-[-0.045em]">Sign in</h1>
      <p className="mt-3 text-[15px] text-[#6b6b6b]">Password, then the 6-digit code from your authenticator app.</p>
      <form onSubmit={submit} className="mt-8 space-y-5">
        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="code">2FA code</Label>
          <Input id="code" inputMode="numeric" autoComplete="one-time-code" placeholder="123456 or a recovery code" value={code} onChange={(e) => setCode(e.target.value)} required />
        </div>
        {error && (
          <p role="alert" className="text-[14px] text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </main>
  );
}
