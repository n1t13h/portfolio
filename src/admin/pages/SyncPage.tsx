import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useAdmin } from "../AdminContext";
import { useAction, useAdminKeys } from "../hooks";

const POLL_MS = 3000;
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export function SyncPage() {
  const { api } = useAdmin();
  const keys = useAdminKeys();
  const run = useAction();
  const queryClient = useQueryClient();
  const [confirmFull, setConfirmFull] = useState(false);

  const status = useQuery({
    queryKey: keys.sync,
    queryFn: api.syncStatus,
    refetchInterval: (query) => (query.state.data?.running ? POLL_MS : false),
  });
  const data = status.data;

  // When a run finishes, new photos exist: refresh the photo list too.
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && data && !data.running) {
      void queryClient.invalidateQueries({ queryKey: keys.photos });
    }
    wasRunning.current = Boolean(data?.running);
  }, [data, queryClient, keys.photos]);

  async function start(full: boolean) {
    await run(() => (full ? api.startFullSync() : api.startSync()));
    await queryClient.invalidateQueries({ queryKey: keys.sync });
  }

  return (
    <div className="max-w-[640px]">
      <h1 className="text-[clamp(30px,3vw,44px)] font-medium leading-[1.05] tracking-[-0.045em]">Sync</h1>
      <p className="mt-2 text-[15px] text-[#6b6b6b]">
        Brings new photos from Unsplash into your library as drafts. It only fetches what it hasn't seen.
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Button disabled={!data || data.running} onClick={() => void start(false)}>
          Sync now
        </Button>
        <Button variant="outline" disabled={!data || data.running} onClick={() => setConfirmFull(true)}>
          Full resync
        </Button>
      </div>

      {data && (
        <section className="mt-8 space-y-3 rounded-[3px] bg-[#f1f1f0] p-5 text-[15px]">
          {data.running ? (
            <p>A sync is running… this page updates by itself.</p>
          ) : data.lastFinishedAt ? (
            <p>
              Last run {when(data.lastFinishedAt)}: {plural(data.lastImported, "photo")} imported.
            </p>
          ) : (
            <p>It hasn't run yet.</p>
          )}
          {data.pending > 0 && (
            <p className="text-[#6b6b6b]">{plural(data.pending, "photo")} waiting for the next run.</p>
          )}
          {data.rateLimitRemaining !== null && (
            <p className="text-[#6b6b6b]">{data.rateLimitRemaining} requests left this hour on Unsplash.</p>
          )}
          {data.lastError && (
            <p role="alert" className="text-destructive">
              {data.lastError}
            </p>
          )}
        </section>
      )}

      <AlertDialog open={confirmFull} onOpenChange={setConfirmFull}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Run a full resync?</AlertDialogTitle>
            <AlertDialogDescription>
              It walks your whole Unsplash library to find older photos it missed, and retries photos that failed
              before. It uses more of the hourly request limit than a normal sync. Photos you deleted stay deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => void start(true)}>Start full resync</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
