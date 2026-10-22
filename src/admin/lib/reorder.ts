/** A copy of `list` with the item at `from` moved to index `to`. Out-of-range moves change nothing. */
export function moveItem<T>(list: readonly T[], from: number, to: number): T[] {
  const copy = [...list];
  const inRange = (i: number) => i >= 0 && i < copy.length;
  if (!inRange(from) || !inRange(to) || from === to) return copy;
  const [item] = copy.splice(from, 1);
  copy.splice(to, 0, item);
  return copy;
}
