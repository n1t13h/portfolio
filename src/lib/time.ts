export function formatIndiaTime(d: Date): string {
  const t = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(d);
  return `${t}, India`;
}
