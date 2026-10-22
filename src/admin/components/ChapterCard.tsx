import { ChevronDown, ChevronUp, Star, X } from "lucide-react";
import { useState } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { AdminChapter, AdminPhoto } from "../api/types";
import { photoName } from "../lib/photo";

interface Props {
  chapter: AdminChapter;
  index: number;
  count: number;
  /** This chapter's photos, in display order. */
  photos: AdminPhoto[];
  coverIds: string[];
  onSave: (changes: { title?: string; note?: string }) => void;
  onMove: (delta: -1 | 1) => void;
  onDelete: () => void;
  onAddPhotos: () => void;
  onRemovePhoto: (photoId: string) => void;
  onReorderPhotos: (ids: string[]) => void;
  onToggleCover: (photoId: string) => void;
}

export function ChapterCard(props: Props) {
  const { chapter, index, count, photos, coverIds, onMove, onDelete, onAddPhotos, onRemovePhoto, onToggleCover } = props;
  const [title, setTitle] = useState(chapter.title);
  const [note, setNote] = useState(chapter.note);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [draggedId, setDraggedId] = useState<string | null>(null);

  const changes: { title?: string; note?: string } = {};
  if (title !== chapter.title) changes.title = title;
  if (note !== chapter.note) changes.note = note;
  const dirty = Object.keys(changes).length > 0;
  const label = chapter.title.trim() || "Untitled";

  function dropOn(targetId: string) {
    const ids = photos.map((p) => p.id);
    const from = ids.indexOf(draggedId ?? "");
    const to = ids.indexOf(targetId);
    setDraggedId(null);
    if (from < 0 || to < 0 || from === to) return;
    const reordered = [...ids];
    reordered.splice(to, 0, reordered.splice(from, 1)[0]);
    props.onReorderPhotos(reordered);
  }

  return (
    <section aria-label={`Chapter ${label}`} className="rounded-[3px] border p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="grid flex-1 gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <div className="space-y-2">
            <Label htmlFor={`ct-${chapter.id}`}>Chapter title</Label>
            <Input id={`ct-${chapter.id}`} value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`cn-${chapter.id}`}>Chapter note</Label>
            <Textarea id={`cn-${chapter.id}`} rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <Button variant="outline" size="sm" aria-label="Move chapter up" disabled={index === 0} onClick={() => onMove(-1)}>
            <ChevronUp />
          </Button>
          <Button variant="outline" size="sm" aria-label="Move chapter down" disabled={index >= count - 1} onClick={() => onMove(1)}>
            <ChevronDown />
          </Button>
        </div>
      </div>

      <div className="mt-3 flex gap-2">
        <Button size="sm" disabled={!dirty} onClick={() => props.onSave(changes)}>
          Save chapter
        </Button>
        <Button variant="outline" size="sm" className="text-destructive" onClick={() => setConfirmDelete(true)}>
          Delete chapter
        </Button>
      </div>

      <ul aria-label={`Photos in ${label}`} className="mt-5 grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6">
        {photos.map((photo) => {
          const name = photoName(photo);
          const isCover = coverIds.includes(photo.id);
          return (
            <li
              key={photo.id}
              draggable
              onDragStart={(e) => {
                e.dataTransfer?.setData("text/plain", photo.id);
                setDraggedId(photo.id);
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                dropOn(photo.id);
              }}
              onDragEnd={() => setDraggedId(null)}
              className={`group relative overflow-hidden rounded-[3px] bg-[#f1f1f0] ${draggedId === photo.id ? "opacity-40" : ""}`}
            >
              <img src={photo.variants["800"]} alt={name} draggable={false} className="aspect-[4/3] w-full object-cover" />
              <button
                type="button"
                aria-label={`Use ${name} as cover`}
                aria-pressed={isCover}
                onClick={() => onToggleCover(photo.id)}
                className={`absolute left-1.5 top-1.5 rounded-full bg-white/90 p-1 ${isCover ? "" : "opacity-0 focus:opacity-100 group-hover:opacity-100"}`}
              >
                <Star className={`h-3.5 w-3.5 ${isCover ? "fill-[#0b0b0b]" : ""}`} />
              </button>
              <button
                type="button"
                aria-label={`Remove ${name} from chapter`}
                onClick={() => onRemovePhoto(photo.id)}
                className="absolute right-1.5 top-1.5 rounded-full bg-white/90 p-1 opacity-0 focus:opacity-100 group-hover:opacity-100"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          );
        })}
      </ul>
      <Button variant="outline" size="sm" className="mt-3" onClick={onAddPhotos}>
        Add photos
      </Button>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete the chapter "{label}"?</AlertDialogTitle>
            <AlertDialogDescription>Its photos stay in your library; they just leave this collection.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}
