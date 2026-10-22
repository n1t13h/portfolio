import { useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useAdmin } from "../AdminContext";
import { CollectionEditor } from "../components/CollectionEditor";
import { NewCollectionDialog } from "../components/NewCollectionDialog";
import { PhotoPicker } from "../components/PhotoPicker";
import { useAction, useAdminKeys, useCollections, usePhotos } from "../hooks";
import { moveItem } from "../lib/reorder";
import type { AdminPhoto } from "../api/types";

export function CollectionsPage() {
  const { api } = useAdmin();
  const run = useAction();
  const keys = useAdminKeys();
  const queryClient = useQueryClient();
  const collections = useCollections().data ?? [];
  const photos = usePhotos().data ?? [];

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [pickingFor, setPickingFor] = useState<string | null>(null); // chapter id

  const selected = collections.find((c) => c.id === selectedId) ?? collections[0] ?? null;
  const pickingChapter = selected?.chapters.find((ch) => ch.id === pickingFor) ?? null;

  async function reorderCollections(from: number, to: number) {
    if (from < 0 || to < 0 || to >= collections.length || from === to) return;
    const next = moveItem(collections, from, to);
    queryClient.setQueryData(keys.collections, next);
    await run(() => api.reorderCollections(next.map((c) => c.id)));
  }

  async function create(input: { slug: string; title: string }) {
    try {
      const created = await api.createCollection(input);
      setSelectedId(created.id);
    } finally {
      await queryClient.invalidateQueries({ queryKey: keys.collections });
    }
  }

  const whereIs = (photo: AdminPhoto): string | null => {
    for (const c of collections) {
      const chapter = c.chapters.find((ch) => ch.id === photo.chapterId);
      if (chapter) return `${c.title} › ${chapter.title || "Untitled"}`;
    }
    return null;
  };

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[clamp(30px,3vw,44px)] font-medium leading-[1.05] tracking-[-0.045em]">Collections</h1>
          <p className="mt-2 text-[15px] text-[#6b6b6b]">The essays on your photography page, in the order shown there.</p>
        </div>
        <Button onClick={() => setCreating(true)}>New collection</Button>
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[280px_minmax(0,1fr)]">
        <ul aria-label="Collections" className="space-y-2 self-start">
          {collections.map((c, index) => (
            <li
              key={c.id}
              draggable
              onDragStart={(e) => {
                e.dataTransfer?.setData("text/plain", c.id);
                setDraggedId(c.id);
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const from = collections.findIndex((x) => x.id === draggedId);
                setDraggedId(null);
                void reorderCollections(from, index);
              }}
              onDragEnd={() => setDraggedId(null)}
              className={`flex items-center gap-1 rounded-[3px] ${selected?.id === c.id ? "bg-[#f1f1f0]" : ""} ${
                draggedId === c.id ? "opacity-40" : ""
              }`}
            >
              <button
                type="button"
                aria-pressed={selected?.id === c.id}
                onClick={() => setSelectedId(c.id)}
                className="min-w-0 flex-1 px-3 py-2.5 text-left"
              >
                <span className="block truncate text-[15px]">{c.title}</span>
                <span className="block text-[12px] text-[#6b6b6b]">{c.status === "published" ? "Published" : "Draft"}</span>
              </button>
              <Button variant="ghost" size="sm" aria-label={`Move ${c.title} earlier`} disabled={index === 0} onClick={() => void reorderCollections(index, index - 1)}>
                <ArrowUp />
              </Button>
              <Button variant="ghost" size="sm" aria-label={`Move ${c.title} later`} disabled={index === collections.length - 1} onClick={() => void reorderCollections(index, index + 1)}>
                <ArrowDown />
              </Button>
            </li>
          ))}
          {collections.length === 0 && <li className="px-3 py-2 text-[15px] text-[#6b6b6b]">No collections yet.</li>}
        </ul>

        {selected && (
          <CollectionEditor
            key={selected.id}
            collection={selected}
            photos={photos}
            onSave={(changes) => void run(() => api.updateCollection(selected.id, changes))}
            onPublished={(on) =>
              void run(() => (on ? api.publishCollection(selected.id) : api.unpublishCollection(selected.id)))
            }
            onDelete={() => {
              setSelectedId(null);
              void run(() => api.deleteCollection(selected.id));
            }}
            onAddChapter={() => void run(() => api.createChapter(selected.id, {}))}
            onSaveChapter={(id, changes) => void run(() => api.updateChapter(id, changes))}
            onMoveChapter={(id, delta) => {
              const ids = selected.chapters.map((ch) => ch.id);
              const from = ids.indexOf(id);
              if (from + delta < 0 || from + delta >= ids.length) return;
              void run(() => api.reorderChapters(selected.id, moveItem(ids, from, from + delta)));
            }}
            onDeleteChapter={(id) => void run(() => api.deleteChapter(id))}
            onAddPhotos={setPickingFor}
            onRemovePhoto={(chapterId, photoId) => void run(() => api.removePhoto(chapterId, photoId))}
            onReorderPhotos={(chapterId, ids) => void run(() => api.reorderChapterPhotos(chapterId, ids))}
            onToggleCover={(photoId) => {
              const covers = selected.coverPhotoIds;
              const next = covers.includes(photoId) ? covers.filter((id) => id !== photoId) : [...covers, photoId];
              void run(() => api.setCovers(selected.id, next));
            }}
          />
        )}
      </div>

      <NewCollectionDialog open={creating} onClose={() => setCreating(false)} onCreate={create} />
      <PhotoPicker
        open={pickingChapter !== null}
        chapterName={pickingChapter?.title.trim() || "this chapter"}
        candidates={photos.filter((p) => p.chapterId !== pickingChapter?.id)}
        whereIs={whereIs}
        onClose={() => setPickingFor(null)}
        onAdd={(ids) => pickingChapter && void run(() => api.assignPhotos(pickingChapter.id, ids))}
      />
    </div>
  );
}
