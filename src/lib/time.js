// Adapted from Sindara's production core.ts helpers. All time values are seconds.
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const progress = (t, start, duration) => clamp((t - start) / duration);
export const easeOut = (x) => 1 - (1 - clamp(x)) ** 3;
export const easeInOut = (x) => {const k = clamp(x); return k * k * (3 - 2 * k);};
export const keys = (t, points, ease = easeInOut) => {
  if (points.length === 0) throw new Error('keys() needs at least one point');
  for (let i = 0; i < points.length - 1; i++) {
    if (t < points[i + 1][0]) {
      return lerp(points[i][1], points[i + 1][1], ease(progress(t, points[i][0], points[i + 1][0] - points[i][0])));
    }
  }
  return points[points.length - 1][1];
};
