import { ChevronLeft, ChevronRight } from "lucide-react";
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
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import type { AdminCollection, AdminPhoto } from "../api/types";
import { photoName } from "../lib/photo";

export interface PhotoSheetProps {
  photo: AdminPhoto | null;
  position: number; // 0-based index in the visible list
  count: number;
  collections: AdminCollection[];
  canMove: boolean;
  onClose: () => void;
  onStep: (delta: -1 | 1) => void;
  onSave: (changes: { title?: string; place?: string | null }) => void;
  onPublished: (published: boolean) => void;
  onAllowDownload: (allow: boolean) => void;
  onChapter: (chapterId: string) => void;
  onMove: (delta: -1 | 1) => void;
  onDelete: () => void;
}

function exifLine(exif: AdminPhoto["exif"]): string {
  const parts = [
    exif.camera,
    exif.focal_length ? `${exif.focal_length}mm` : null,
    exif.aperture ? `f/${exif.aperture}` : null,
    exif.shutter ? `${exif.shutter}s` : null,
    exif.iso ? `ISO ${exif.iso}` : null,
  ];
  return parts.filter(Boolean).join(" · ");
}

export function PhotoSheet(props: PhotoSheetProps) {
  const { photo, onClose } = props;
  return (
    <Sheet open={photo !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-[520px]">
        {photo && <SheetBody key={photo.id} {...props} photo={photo} />}
      </SheetContent>
    </Sheet>
  );
}

function SheetBody({
  photo,
  position,
  count,
  collections,
  canMove,
  onStep,
  onSave,
  onPublished,
  onAllowDownload,
  onChapter,
  onMove,
  onDelete,
}: PhotoSheetProps & { photo: AdminPhoto }) {
  const [title, setTitle] = useState(photo.title);
  const [place, setPlace] = useState(photo.place ?? "");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const changes: { title?: string; place?: string | null } = {};
  if (title !== photo.title) changes.title = title;
  if (place !== (photo.place ?? "")) changes.place = place.trim() === "" ? null : place;
  const dirty = Object.keys(changes).length > 0;
  const preview = photo.variants["1600"] ?? photo.variants["800"];

  return (
    <>
      <SheetHeader className="text-left">
        <SheetTitle className="truncate pr-8 tracking-[-0.02em]">{photoName(photo)}</SheetTitle>
        <SheetDescription className="sr-only">Edit this photo</SheetDescription>
      </SheetHeader>

      <div className="mt-4 flex items-center justify-between text-[13px] text-[#6b6b6b]">
        <span>
          {position + 1} of {count}
        </span>
        <div className="flex gap-1">
          <Button variant="outline" size="sm" aria-label="Previous photo" disabled={position === 0} onClick={() => onStep(-1)}>
            <ChevronLeft />
          </Button>
          <Button variant="outline" size="sm" aria-label="Next photo" disabled={position >= count - 1} onClick={() => onStep(1)}>
            <ChevronRight />
          </Button>
        </div>
      </div>

      <img src={preview} alt={photoName(photo)} className="mt-3 w-full rounded-[3px] bg-[#f1f1f0]" />
      {exifLine(photo.exif) && <p className="mt-2 text-[12px] text-[#6b6b6b]">{exifLine(photo.exif)}</p>}

      <form
        className="mt-6 space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (dirty) onSave(changes);
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="photo-title">Title</Label>
          <Input id="photo-title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="photo-place">Place</Label>
          <Input id="photo-place" value={place} onChange={(e) => setPlace(e.target.value)} />
        </div>
        <Button type="submit" disabled={!dirty}>
          Save
        </Button>
      </form>

      <div className="mt-8 space-y-5 border-t pt-6">
        <div className="flex items-center justify-between">
          <Label htmlFor="photo-published">Published</Label>
          <Switch id="photo-published" checked={photo.status === "published"} onCheckedChange={onPublished} />
        </div>
        <div className="flex items-center justify-between gap-6">
          <div>
            <Label htmlFor="photo-download">Allow downloads</Label>
            <p className="mt-1 text-[12px] text-[#6b6b6b]">Visitors get a 2400px copy. Your original stays private.</p>
          </div>
          <Switch id="photo-download" checked={photo.allowDownload} onCheckedChange={onAllowDownload} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="photo-chapter">Collection chapter</Label>
          <select
            id="photo-chapter"
            value={photo.chapterId ?? ""}
            onChange={(e) => onChapter(e.target.value)}
            className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">Not in a collection</option>
            {collections.map((c) => (
              <optgroup key={c.id} label={c.title}>
                {c.chapters.map((ch) => (
                  <option key={ch.id} value={ch.id}>
                    {ch.title || "Untitled chapter"}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t pt-6">
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={!canMove} onClick={() => onMove(-1)}>
            Move earlier
          </Button>
          <Button variant="outline" size="sm" disabled={!canMove} onClick={() => onMove(1)}>
            Move later
          </Button>
        </div>
        <Button variant="outline" size="sm" className="text-destructive" onClick={() => setConfirmDelete(true)}>
          Delete photo
        </Button>
      </div>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this photo?</AlertDialogTitle>
            <AlertDialogDescription>
              The photo and its files are removed for good. If it came from Unsplash it will not be re-imported.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
