export const imgUrl = (pid: string, width: number): string =>
  `https://images.unsplash.com/photo-${pid}?w=${width}&q=80&auto=format`;

export const srcSet = (pid: string, widths: number[]): string =>
  widths.map((w) => `${imgUrl(pid, w)} ${w}w`).join(", ");
