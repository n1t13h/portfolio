import { useQueryClient } from "@tanstack/react-query";
import { ChangeEvent, DragEvent, useRef, useState } from "react";
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
import { PhotoSheet } from "../components/PhotoSheet";
import { PhotoTile } from "../components/PhotoTile";
import { UploadSummary } from "../components/UploadSummary";
import { useAction, useAdminKeys, useCollections, usePhotos } from "../hooks";
import { moveItem } from "../lib/reorder";
import { uploadPhotos, type UploadResult } from "../lib/upload";

type Filter = "all" | "draft" | "published";

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes("Files");

export function PhotosPage() {
  const { api } = useAdmin();
  const run = useAction();
  const queryClient = useQueryClient();
  const keys = useAdminKeys();
  const photosQuery = usePhotos();
  const collectionsQuery = useCollections();
  const photos = photosQuery.data ?? [];
  const collections = collectionsQuery.data ?? [];

  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [openId, setOpenId] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [active, setActive] = useState<Record<string, number>>({});
  const [results, setResults] = useState<UploadResult[] | null>(null);
  const [dropping, setDropping] = useState(false);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const published = photos.filter((p) => p.status === "published").length;
  const drafts = photos.length - published;
  const visible = photos.filter((p) => filter === "all" || p.status === filter);
  const open = photos.find((p) => p.id === openId) ?? null;
  const openPosition = visible.findIndex((p) => p.id === openId);

  // ---- ordering -------------------------------------------------------------------------

  async function reorder(ids: string[]) {
    const byId = new Map(photos.map((p) => [p.id, p]));
    queryClient.setQueryData(keys.photos, ids.map((id) => byId.get(id)!)); // show it at once
    await run(() => api.reorderPhotos(ids));
  }

  function dropOn(targetId: string) {
    const from = photos.findIndex((p) => p.id === draggedId);
    const to = photos.findIndex((p) => p.id === targetId);
    setDraggedId(null);
    if (from < 0 || to < 0 || from === to) return;
    void reorder(moveItem(photos, from, to).map((p) => p.id));
  }

  function moveOpen(delta: -1 | 1) {
    const from = photos.findIndex((p) => p.id === openId);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= photos.length) return;
    void reorder(moveItem(photos, from, to).map((p) => p.id));
  }

  // ---- uploads --------------------------------------------------------------------------

  async function startUpload(files: File[]) {
    if (files.length === 0) return;
    setResults(null);
    setActive(Object.fromEntries(files.map((f) => [f.name, 0])));
    const outcome = await uploadPhotos(api, files, {
      onProgress: ({ name, fraction }) => setActive((a) => ({ ...a, [name]: fraction })),
    });
    setActive({});
    setResults(outcome);
    await queryClient.invalidateQueries({ queryKey: keys.photos });
  }

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    e.target.value = ""; // so choosing the same files again still fires
    void startUpload(files);
  }

  // ---- selection and bulk actions -------------------------------------------------------

  const toggle = (id: string) =>
    setSelected((s) => {
      const next = new Set(s);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  async function bulk(action: (id: string) => Promise<unknown>, only: (id: string) => boolean = () => true) {
    const ids = [...selected].filter(only);
    await run(async () => {
      for (const id of ids) await action(id);
    });
    setSelected(new Set());
  }

  const isDraft = (id: string) => photos.find((p) => p.id === id)?.status === "draft";
  const isPublished = (id: string) => photos.find((p) => p.id === id)?.status === "published";

  // ---- render ---------------------------------------------------------------------------

  const filterButton = (value: Filter, label: string) => (
    <Button variant={filter === value ? "default" : "outline"} size="sm" onClick={() => setFilter(value)}>
      {label}
    </Button>
  );

  return (
    <div
      onDragOver={(e) => {
        if (!hasFiles(e)) return;
        e.preventDefault();
        setDropping(true);
      }}
      onDragLeave={(e) => e.currentTarget === e.target && setDropping(false)}
      onDrop={(e) => {
        if (!hasFiles(e)) return;
        e.preventDefault();
        setDropping(false);
        void startUpload(Array.from(e.dataTransfer.files));
      }}
      className={dropping ? "rounded-[3px] outline-dashed outline-2 outline-offset-8 outline-[#0b0b0b]" : ""}
    >
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[clamp(30px,3vw,44px)] font-medium leading-[1.05] tracking-[-0.045em]">Photos</h1>
          <p className="mt-2 text-[15px] text-[#6b6b6b]">
            {photosQuery.isSuccess
              ? `${plural(photos.length, "photo")} · ${published} published · ${plural(drafts, "draft")}`
              : "Loading…"}
          </p>
        </div>
        <div>
          <input
            ref={fileInput}
            type="file"
            multiple
            accept="image/jpeg,.jpg,.jpeg"
            aria-label="Choose photo files"
            aria-hidden
            tabIndex={-1}
            onChange={onPick}
            className="sr-only"
          />
          <Button onClick={() => fileInput.current?.click()}>Upload photos</Button>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-2">
        {filterButton("all", "All")}
        {filterButton("draft", `Drafts (${drafts})`)}
        {filterButton("published", `Published (${published})`)}
        <span className="ml-2 text-[13px] text-[#6b6b6b]">
          {filter === "all" ? "Drag photos to reorder." : "Switch to All to reorder."}
        </span>
      </div>

      {selected.size > 0 && (
        <div className="sticky top-16 z-[5] mt-4 flex flex-wrap items-center gap-2 rounded-[3px] bg-[#0b0b0b] px-4 py-2 text-[14px] text-white">
          <span className="mr-2">{selected.size} selected</span>
          <Button size="sm" variant="secondary" onClick={() => void bulk((id) => api.publishPhoto(id), isDraft)}>
            Publish selected
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void bulk((id) => api.unpublishPhoto(id), isPublished)}>
            Unpublish selected
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setConfirmBulkDelete(true)}>
            Delete selected
          </Button>
          <Button size="sm" variant="ghost" className="ml-auto hover:bg-white/10 hover:text-white" onClick={() => setSelected(new Set())}>
            Clear
          </Button>
        </div>
      )}

      <div className="mt-6">
        <UploadSummary active={active} results={results} onDismiss={() => setResults(null)} />
      </div>

      {photosQuery.isSuccess && photos.length === 0 ? (
        <div className="mt-6 rounded-[3px] bg-[#f1f1f0] px-6 py-16 text-center">
          <p className="text-[20px] tracking-[-0.02em]">No photos yet.</p>
          <p className="mt-2 text-[15px] text-[#6b6b6b]">Choose JPEGs with the button above, or drop them anywhere on this page.</p>
        </div>
      ) : (
        <ul className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
          {visible.map((photo) => (
            <PhotoTile
              key={photo.id}
              photo={photo}
              selected={selected.has(photo.id)}
              draggable={filter === "all"}
              dragging={draggedId === photo.id}
              onToggleSelect={() => toggle(photo.id)}
              onOpen={() => setOpenId(photo.id)}
              onDragStart={() => setDraggedId(photo.id)}
              onDrop={() => dropOn(photo.id)}
              onDragEnd={() => setDraggedId(null)}
            />
          ))}
        </ul>
      )}

      <PhotoSheet
        photo={open}
        position={Math.max(openPosition, 0)}
        count={visible.length}
        collections={collections}
        canMove
        onClose={() => setOpenId(null)}
        onStep={(delta) => {
          const next = visible[openPosition + delta];
          if (next) setOpenId(next.id);
        }}
        onSave={(changes) => open && void run(() => api.updatePhoto(open.id, changes))}
        onPublished={(on) =>
          open && void run(() => (on ? api.publishPhoto(open.id) : api.unpublishPhoto(open.id)))
        }
        onAllowDownload={(allow) => open && void run(() => api.setAllowDownload(open.id, allow))}
        onChapter={(chapterId) =>
          open &&
          void run(async () => {
            if (chapterId === "") {
              if (open.chapterId) await api.removePhoto(open.chapterId, open.id);
            } else {
              await api.assignPhotos(chapterId, [open.id]);
            }
          })
        }
        onMove={moveOpen}
        onDelete={() => {
          if (!open) return;
          const id = open.id;
          setOpenId(null);
          void run(() => api.deletePhoto(id));
        }}
      />

      <AlertDialog open={confirmBulkDelete} onOpenChange={setConfirmBulkDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {plural(selected.size, "photo")}?</AlertDialogTitle>
            <AlertDialogDescription>
              They and their files are removed for good. Photos that came from Unsplash will not be re-imported.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => void bulk((id) => api.deletePhoto(id))}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
