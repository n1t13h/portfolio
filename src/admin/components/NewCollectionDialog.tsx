import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { slugify } from "../lib/slug";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Resolves when created; rejects with the server's reason, which is shown in the dialog. */
  onCreate: (input: { slug: string; title: string }) => Promise<void>;
}

export function NewCollectionDialog({ open, onClose, onCreate }: Props) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>{open && <Form onClose={onClose} onCreate={onCreate} />}</DialogContent>
    </Dialog>
  );
}

function Form({ onClose, onCreate }: Pick<Props, "onClose" | "onCreate">) {
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onCreate({ slug, title: title.trim() });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the collection.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>New collection</DialogTitle>
        <DialogDescription>It starts as a draft. Publish it when it's ready.</DialogDescription>
      </DialogHeader>
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="new-title">Title</Label>
          <Input
            id="new-title"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (!slugEdited) setSlug(slugify(e.target.value));
            }}
            required
            autoFocus
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="new-slug">Slug</Label>
          <Input
            id="new-slug"
            value={slug}
            onChange={(e) => {
              setSlug(e.target.value);
              setSlugEdited(true);
            }}
            required
          />
          <p className="text-[12px] text-[#6b6b6b]">The address of the page: /photos/{slug || "…"}</p>
        </div>
        {error && (
          <p role="alert" className="text-[14px] text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" disabled={busy || !title.trim() || !slug}>
          Create
        </Button>
      </form>
    </>
  );
}
