import { X } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import type { UploadResult } from "../lib/upload";

interface Props {
  /** Files in flight: name -> fraction sent (0..1). */
  active: Record<string, number>;
  /** Outcome of the last finished batch, if any. */
  results: UploadResult[] | null;
  onDismiss: () => void;
}

export function UploadSummary({ active, results, onDismiss }: Props) {
  const names = Object.keys(active);
  if (names.length === 0 && !results) return null;

  const failed = (results ?? []).filter((r): r is Extract<UploadResult, { ok: false }> => !r.ok);
  const uploaded = (results ?? []).length - failed.length;

  return (
    <section aria-live="polite" className="mb-6 rounded-[3px] bg-[#f1f1f0] p-4 text-[14px]">
      {names.length > 0 ? (
        <>
          <p className="mb-3">Uploading {names.length} {names.length === 1 ? "photo" : "photos"}…</p>
          <ul className="space-y-2">
            {names.map((name) => (
              <li key={name} className="flex items-center gap-3">
                <span className="w-48 truncate text-[#6b6b6b]">{name}</span>
                <Progress value={Math.round(active[name] * 100)} className="h-1.5 flex-1" />
              </li>
            ))}
          </ul>
        </>
      ) : (
        <div className="flex items-start justify-between gap-4">
          <div>
            <p>
              {uploaded} uploaded{failed.length > 0 ? ` · ${failed.length} failed` : ""}. New photos start as drafts.
            </p>
            {failed.length > 0 && (
              <ul className="mt-2 space-y-1 text-destructive">
                {failed.map((r) => (
                  <li key={r.name}>
                    {r.name} — {r.error}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button type="button" aria-label="Dismiss" onClick={onDismiss} className="p-1 text-[#6b6b6b] hover:text-ink">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </section>
  );
}
