import { describe, expect, it, vi } from "vitest";
import { uploadPhotos, type UploadApi, type UploadProgress } from "./upload";

const jpeg = (name: string, size = 10) =>
  new File([new Uint8Array(size)], name, { type: "image/jpeg" });

function fakeApi(overrides: Partial<UploadApi> = {}): UploadApi & {
  requested: number;
  confirmed: string[];
} {
  const state = { requested: 0, confirmed: [] as string[] };
  const api: UploadApi = {
    requestUpload: async () => {
      state.requested += 1;
      return { photoId: `p${state.requested}`, putUrl: `http://store/p${state.requested}`, key: "k" };
    },
    confirmUpload: async (id) => {
      state.confirmed.push(id);
      return { id } as never;
    },
    ...overrides,
  };
  return Object.assign(api, {
    get requested() {
      return state.requested;
    },
    confirmed: state.confirmed,
  });
}

describe("uploadPhotos", () => {
  it("asks for a link, sends the file there, then confirms it", async () => {
    const api = fakeApi();
    const put = vi.fn(async () => {});

    const results = await uploadPhotos(api, [jpeg("a.jpg")], { put });

    expect(put).toHaveBeenCalledWith("http://store/p1", expect.any(File), expect.any(Function));
    expect(api.confirmed).toEqual(["p1"]);
    expect(results).toEqual([{ name: "a.jpg", ok: true, photoId: "p1" }]);
  });

  it("refuses anything that is not a JPEG without touching the server", async () => {
    const api = fakeApi();
    const png = new File(["x"], "scan.png", { type: "image/png" });
    const put = vi.fn(async () => {});

    const results = await uploadPhotos(api, [png], { put });

    expect(api.requested).toBe(0);
    expect(put).not.toHaveBeenCalled();
    expect(results[0]).toMatchObject({ name: "scan.png", ok: false });
    expect(results[0].ok === false && results[0].error).toMatch(/JPEG/);
  });

  it("accepts .jpeg and uppercase extensions even when the browser gives no type", async () => {
    const api = fakeApi();
    const files = [new File(["x"], "A.JPG"), new File(["x"], "b.jpeg")];
    const results = await uploadPhotos(api, files, { put: async () => {} });
    expect(results.map((r) => r.ok)).toEqual([true, true]);
  });

  it("keeps going when one file fails and reports why", async () => {
    const api = fakeApi();
    const put = vi.fn(async (url: string) => {
      if (url.endsWith("/p2")) throw new Error("network down");
    });

    const results = await uploadPhotos(api, [jpeg("1.jpg"), jpeg("2.jpg"), jpeg("3.jpg")], {
      put,
      concurrency: 1,
    });

    expect(results.map((r) => r.ok)).toEqual([true, false, true]);
    expect(results[1]).toMatchObject({ name: "2.jpg", error: "network down" });
    expect(api.confirmed).toEqual(["p1", "p3"]);
  });

  it("surfaces the server's reason when confirming fails", async () => {
    const api = fakeApi({
      confirmUpload: async () => {
        throw new Error("image too large");
      },
    });
    const results = await uploadPhotos(api, [jpeg("big.jpg")], { put: async () => {} });
    expect(results[0]).toMatchObject({ ok: false, error: "image too large" });
  });

  it("never runs more than `concurrency` uploads at once", async () => {
    const api = fakeApi();
    let active = 0;
    let peak = 0;
    const put = async () => {
      active += 1;
      peak = Math.max(peak, active);
      await new Promise((r) => setTimeout(r, 5));
      active -= 1;
    };

    await uploadPhotos(api, Array.from({ length: 6 }, (_, i) => jpeg(`${i}.jpg`)), {
      put,
      concurrency: 2,
    });

    expect(peak).toBe(2);
  });

  it("reports progress per file as a fraction", async () => {
    const api = fakeApi();
    const seen: UploadProgress[] = [];
    const put = async (_url: string, _file: File, onProgress: (f: number) => void) => {
      onProgress(0.5);
      onProgress(1);
    };

    await uploadPhotos(api, [jpeg("a.jpg")], { put, onProgress: (p) => seen.push(p) });

    expect(seen).toContainEqual({ name: "a.jpg", fraction: 0.5 });
    expect(seen).toContainEqual({ name: "a.jpg", fraction: 1 });
  });
});
