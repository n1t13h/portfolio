import { Download } from "lucide-react";
import type { DragEvent } from "react";
import type { AdminPhoto } from "../api/types";
import { photoName } from "../lib/photo";

interface Props {
  photo: AdminPhoto;
  selected: boolean;
  draggable: boolean;
  dragging: boolean;
  onToggleSelect: () => void;
  onOpen: () => void;
  onDragStart: () => void;
  onDrop: () => void;
  onDragEnd: () => void;
}

export function PhotoTile({
  photo,
  selected,
  draggable,
  dragging,
  onToggleSelect,
  onOpen,
  onDragStart,
  onDrop,
  onDragEnd,
}: Props) {
  const name = photoName(photo);
  const handleDragStart = (e: DragEvent) => {
    e.dataTransfer?.setData("text/plain", photo.id); // Firefox only starts a drag if data is set
    onDragStart();
  };
  return (
    <li
      draggable={draggable}
      onDragStart={handleDragStart}
      onDragOver={(e) => draggable && e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        onDrop();
      }}
      onDragEnd={onDragEnd}
      className={`group relative overflow-hidden rounded-[3px] bg-[#f1f1f0] ${dragging ? "opacity-40" : ""} ${
        selected ? "ring-2 ring-ink" : ""
      }`}
    >
      <button type="button" aria-label={`Edit ${name}`} onClick={onOpen} className="block w-full text-left">
        <img
          src={photo.variants["800"]}
          alt={name}
          loading="lazy"
          draggable={false}
          className="aspect-[4/3] w-full object-cover"
        />
        <span className="block truncate px-2.5 py-2 text-[13px] text-[#333]">{name}</span>
      </button>
      <input
        type="checkbox"
        aria-label={`Select ${name}`}
        checked={selected}
        onChange={onToggleSelect}
        className={`absolute left-2 top-2 h-5 w-5 cursor-pointer accent-[#0b0b0b] ${
          selected ? "" : "opacity-0 focus:opacity-100 group-hover:opacity-100"
        }`}
      />
      <div className="pointer-events-none absolute right-2 top-2 flex items-center gap-1.5">
        {photo.allowDownload && (
          <span title="Downloads allowed" className="rounded-full bg-white/90 p-1">
            <Download className="h-3 w-3" aria-label="Downloads allowed" />
          </span>
        )}
        {photo.status === "draft" && (
          <span className="rounded-full bg-white/90 px-2 py-0.5 text-[11px] font-medium">Draft</span>
        )}
      </div>
    </li>
  );
}
