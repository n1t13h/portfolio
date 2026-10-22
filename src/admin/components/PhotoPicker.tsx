import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { AdminPhoto } from "../api/types";
import { photoName } from "../lib/photo";

interface Props {
  open: boolean;
  chapterName: string;
  /** Every library photo that is not already in this chapter, in library order. */
  candidates: AdminPhoto[];
  /** Where a photo currently lives ("Goa › Arrival"), or null if it is not in a collection. */
  whereIs: (photo: AdminPhoto) => string | null;
  onClose: () => void;
  onAdd: (photoIds: string[]) => void;
}

export function PhotoPicker(props: Props) {
  return (
    <Dialog open={props.open} onOpenChange={(o) => !o && props.onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[760px]">
        {props.open && <Body {...props} />}
      </DialogContent>
    </Dialog>
  );
}

function Body({ chapterName, candidates, whereIs, onClose, onAdd }: Props) {
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const toggle = (id: string) =>
    setChosen((s) => {
      const next = new Set(s);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  return (
    <>
      <DialogHeader>
        <DialogTitle>Add photos to {chapterName}</DialogTitle>
        <DialogDescription>A photo can be in one chapter at a time; choosing one that is elsewhere moves it.</DialogDescription>
      </DialogHeader>

      {candidates.length === 0 ? (
        <p className="py-8 text-center text-[15px] text-[#6b6b6b]">No other photos in your library yet.</p>
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {candidates.map((photo) => {
            const name = photoName(photo);
            const where = whereIs(photo);
            return (
              <li key={photo.id} className={`relative overflow-hidden rounded-[3px] bg-[#f1f1f0] ${chosen.has(photo.id) ? "ring-2 ring-ink" : ""}`}>
                <label className="block cursor-pointer">
                  <img src={photo.variants["800"]} alt={name} loading="lazy" className="aspect-[4/3] w-full object-cover" />
                  <span className="block truncate px-2 pt-1.5 text-[13px]">{name}</span>
                  <span className="block truncate px-2 pb-1.5 text-[11px] text-[#6b6b6b]">
                    {where ? `In ${where}` : photo.status === "draft" ? "Draft" : "Not in a collection"}
                  </span>
                  <input
                    type="checkbox"
                    aria-label={`Select ${name}`}
                    checked={chosen.has(photo.id)}
                    onChange={() => toggle(photo.id)}
                    className="absolute left-2 top-2 h-5 w-5 accent-[#0b0b0b]"
                  />
                </label>
              </li>
            );
          })}
        </ul>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button
          disabled={chosen.size === 0}
          onClick={() => {
            // Keep library order, not click order.
            onAdd(candidates.filter((p) => chosen.has(p.id)).map((p) => p.id));
            onClose();
          }}
        >
          Add selected
        </Button>
      </div>
    </>
  );
}
