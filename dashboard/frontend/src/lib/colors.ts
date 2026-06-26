// True gradient color interpolation
const STOPS = [
  { t: 0.0, r: 0xF4, g: 0xD3, b: 0x5E },  // #F4D35E
  { t: 0.25, r: 0xF2, g: 0xA5, b: 0x41 }, // #F2A541
  { t: 0.5, r: 0xEE, g: 0x6C, b: 0x2C },  // #EE6C2C
  { t: 0.75, r: 0xE8, g: 0x40, b: 0x2B }, // #E8402B
  { t: 1.0, r: 0xC6, g: 0x28, b: 0x28 },  // #C62828
];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function hex(r: number, g: number, b: number): string {
  return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;
}

export function interpolateColor(value: number, min: number, max: number): string {
  if (max <= min) return hex(STOPS[0].r, STOPS[0].g, STOPS[0].b);
  let t = (value - min) / (max - min);
  t = Math.max(0, Math.min(1, t));
  
  // Find which segment t falls into
  for (let i = 0; i < STOPS.length - 1; i++) {
    const s0 = STOPS[i];
    const s1 = STOPS[i+1];
    if (t >= s0.t && t <= s1.t) {
      const segT = (t - s0.t) / (s1.t - s0.t);
      const r = Math.round(lerp(s0.r, s1.r, segT));
      const g = Math.round(lerp(s0.g, s1.g, segT));
      const b = Math.round(lerp(s0.b, s1.b, segT));
      return hex(r, g, b);
    }
  }
  return hex(STOPS[STOPS.length-1].r, STOPS[STOPS.length-1].g, STOPS[STOPS.length-1].b);
}

export function getDemandColorExpression(gradientMax: number): (string | number | (string | number | string[])[])[] {
  return [
    'interpolate',
    ['linear'],
    ['get', 'demand_mw'],
    0, '#F4D35E',
    gradientMax * 0.25, '#F2A541',
    gradientMax * 0.5, '#EE6C2C',
    gradientMax * 0.75, '#E8402B',
    gradientMax, '#C62828'
  ];
}