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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { AdminCollection, AdminPhoto, CollectionInput } from "../api/types";
import { ChapterCard } from "./ChapterCard";

export interface CollectionEditorProps {
  collection: AdminCollection;
  photos: AdminPhoto[];
  onSave: (changes: Partial<CollectionInput>) => void;
  onPublished: (published: boolean) => void;
  onDelete: () => void;
  onAddChapter: () => void;
  onSaveChapter: (chapterId: string, changes: { title?: string; note?: string }) => void;
  onMoveChapter: (chapterId: string, delta: -1 | 1) => void;
  onDeleteChapter: (chapterId: string) => void;
  onAddPhotos: (chapterId: string) => void;
  onRemovePhoto: (chapterId: string, photoId: string) => void;
  onReorderPhotos: (chapterId: string, ids: string[]) => void;
  onToggleCover: (photoId: string) => void;
}

type Field = "title" | "slug" | "place" | "year" | "intro";

export function CollectionEditor(props: CollectionEditorProps) {
  const { collection, photos } = props;
  const [values, setValues] = useState<Record<Field, string>>({
    title: collection.title,
    slug: collection.slug,
    place: collection.place,
    year: collection.year,
    intro: collection.intro,
  });
  const [confirmDelete, setConfirmDelete] = useState(false);

  const changes: Partial<CollectionInput> = {};
  (Object.keys(values) as Field[]).forEach((f) => {
    if (values[f] !== collection[f]) changes[f] = values[f];
  });
  const dirty = Object.keys(changes).length > 0;
  const set = (f: Field) => (e: { target: { value: string } }) => setValues((v) => ({ ...v, [f]: e.target.value }));
  const byId = new Map(photos.map((p) => [p.id, p]));

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-[26px] font-medium tracking-[-0.03em]">{collection.title}</h2>
        <div className="flex items-center gap-3">
          <Label htmlFor="collection-published">Published</Label>
          <Switch id="collection-published" checked={collection.status === "published"} onCheckedChange={props.onPublished} />
        </div>
      </div>

      <form
        className="mt-6 grid gap-4 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (dirty) props.onSave(changes);
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="c-title">Title</Label>
          <Input id="c-title" value={values.title} onChange={set("title")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="c-slug">Slug</Label>
          <Input id="c-slug" value={values.slug} onChange={set("slug")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="c-place">Place</Label>
          <Input id="c-place" value={values.place} onChange={set("place")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="c-year">Year</Label>
          <Input id="c-year" value={values.year} onChange={set("year")} />
        </div>
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="c-intro">Intro</Label>
          <Textarea id="c-intro" rows={3} value={values.intro} onChange={set("intro")} />
        </div>
        <div className="flex gap-2 sm:col-span-2">
          <Button type="submit" disabled={!dirty}>
            Save details
          </Button>
          <Button type="button" variant="outline" className="text-destructive" onClick={() => setConfirmDelete(true)}>
            Delete collection
          </Button>
        </div>
      </form>

      <h3 className="mt-12 text-[20px] font-medium tracking-[-0.03em]">Chapters</h3>
      <p className="mt-1 text-[14px] text-[#6b6b6b]">
        Star photos to make them the collection's covers. Drag photos to reorder them within a chapter.
      </p>
      <div className="mt-5 space-y-5">
        {collection.chapters.length === 0 && <p className="text-[15px] text-[#6b6b6b]">No chapters yet.</p>}
        {collection.chapters.map((chapter, index) => (
          <ChapterCard
            key={chapter.id}
            chapter={chapter}
            index={index}
            count={collection.chapters.length}
            photos={chapter.photoIds.map((id) => byId.get(id)).filter((p): p is AdminPhoto => Boolean(p))}
            coverIds={collection.coverPhotoIds}
            onSave={(changes) => props.onSaveChapter(chapter.id, changes)}
            onMove={(delta) => props.onMoveChapter(chapter.id, delta)}
            onDelete={() => props.onDeleteChapter(chapter.id)}
            onAddPhotos={() => props.onAddPhotos(chapter.id)}
            onRemovePhoto={(photoId) => props.onRemovePhoto(chapter.id, photoId)}
            onReorderPhotos={(ids) => props.onReorderPhotos(chapter.id, ids)}
            onToggleCover={props.onToggleCover}
          />
        ))}
      </div>
      <Button variant="outline" className="mt-5" onClick={props.onAddChapter}>
        Add chapter
      </Button>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{collection.title}"?</AlertDialogTitle>
            <AlertDialogDescription>
              Its chapters go too, but every photo stays in your library.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={props.onDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
