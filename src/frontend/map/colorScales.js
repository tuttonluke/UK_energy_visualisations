/**
 * Color palettes and MapLibre GL interpolation expression builders.
 *
 * Each energy source can define its own palette and scale stops.
 * Currently only solar is implemented; adding wind/hydro is a
 * matter of adding another palette + stops object.
 */

// ---------------------------------------------------------------------------
// Solar palette — matte 9-step scale
// ---------------------------------------------------------------------------

export const SOLAR_COLORS = {
  c0: '#1e293b', // Zero / Base Slate
  c1: '#7a6021', // Very Low / Dark Amber
  c2: '#9e7924', // Low / Amber
  c3: '#c49323', // Med-Low / Light Amber
  c4: '#d18b24', // Medium / Orange-Amber
  c5: '#d16a24', // Med-High / Orange
  c6: '#c24b1d', // High / Burnt Orange
  c7: '#a62d17', // Very High / Red
  c8: '#7a1811', // Max / Dark Red
}

/** Ordered array matching stop indices → colours. */
const SOLAR_COLOR_ARRAY = [
  SOLAR_COLORS.c0, SOLAR_COLORS.c1, SOLAR_COLORS.c2,
  SOLAR_COLORS.c3, SOLAR_COLORS.c4, SOLAR_COLORS.c5,
  SOLAR_COLORS.c6, SOLAR_COLORS.c7, SOLAR_COLORS.c8,
]

// ---------------------------------------------------------------------------
// Scale stops — the numeric breakpoints for each mode
// ---------------------------------------------------------------------------

export const NORMALIZED_STOPS = [0, 0.005, 0.015, 0.03, 0.06, 0.1, 0.2, 0.35, 0.5]
export const MACRO_ABSOLUTE_STOPS = [0, 250, 1000, 2500, 5000, 10000, 20000, 40000, 60000]
export const MICRO_ABSOLUTE_STOPS = [0, 25, 100, 250, 500, 1000, 2000, 3500, 5000]

// ---------------------------------------------------------------------------
// Expression builder
// ---------------------------------------------------------------------------

/**
 * Build a MapLibre GL JS `interpolate` expression for colouring features.
 *
 * @param {string} property  - GeoJSON property name to read (e.g. 'macroNormalized')
 * @param {number[]} stops   - Numeric breakpoints (must have exactly 9 entries)
 * @returns {Array}          - MapLibre GL expression
 */
export function buildColorExpression (property, stops) {
  const pairs = stops.flatMap((stop, i) => [stop, SOLAR_COLOR_ARRAY[i]])
  return ['interpolate', ['linear'], ['get', property], ...pairs]
}
