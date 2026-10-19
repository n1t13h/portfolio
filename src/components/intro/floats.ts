// Positions/offsets follow the landing mockup (3 extra frames fill the 9-photo spread).
export const FLOATS: {
  style: React.CSSProperties;
  dx: number;
  dy: number;
  delay: number;
  w: number;
}[] = [
  { style: { left: "3%", top: "-4%", width: "20%", height: "30%" }, dx: -40, dy: -30, delay: 0.05, w: 600 },
  { style: { left: "44%", top: "-6%", width: "18%", height: "18%" }, dx: 0, dy: -40, delay: 0.15, w: 500 },
  { style: { right: "-3%", top: "22%", width: "24%", height: "32%" }, dx: 40, dy: 0, delay: 0.1, w: 500 },
  { style: { left: "-1%", top: "55%", width: "17%", height: "21%" }, dx: -40, dy: 20, delay: 0.2, w: 600 },
  { style: { left: "24%", bottom: "-8%", width: "19%", height: "22%" }, dx: 0, dy: 40, delay: 0.25, w: 500 },
  { style: { right: "20%", bottom: "-6%", width: "20%", height: "30%" }, dx: 20, dy: 40, delay: 0.12, w: 600 },
  { style: { left: "22%", top: "8%", width: "12%", height: "16%" }, dx: -30, dy: -20, delay: 0.18, w: 400 },
  { style: { right: "8%", top: "-3%", width: "14%", height: "17%" }, dx: 30, dy: -30, delay: 0.08, w: 400 },
  { style: { right: "6%", bottom: "6%", width: "13%", height: "16%" }, dx: 30, dy: 30, delay: 0.22, w: 400 },
];
export const FLOAT_COUNT = FLOATS.length;
