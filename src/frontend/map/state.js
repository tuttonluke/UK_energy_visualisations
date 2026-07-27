/**
 * Centralised mutable state for the solar map module.
 *
 * Every sub-module imports this single object rather than
 * maintaining its own module-level variables.  This makes
 * state transitions explicit and easy to trace.
 */
export const state = {
  /** @type {mapboxgl.Map | null} */
  mapInstance: null,

  /** @type {object | null} Solar generation data keyed by country */
  currentSolarData: null,

  /** @type {string | null} Currently selected country key */
  selectedCountry: null,

  /** @type {object | null} Cached raw TopoJSON boundary data */
  cachedTopoData: null,

  /** @type {boolean} Guards against concurrent loadMapData calls */
  isLoading: false,

  /** @type {{ type: 'macro' | 'micro', id?: string, country?: string } | null} */
  hoveredState: null,

  /** @type {boolean} Whether map events have been registered */
  eventsRegistered: false,

  /** @type {boolean} Whether the normalise-by-area toggle is active */
  isNormalized: true,

  /**
   * Map of country key → array of Mapbox feature IDs.
   * Rebuilt on every data refresh to avoid unbounded growth.
   * @type {Record<string, string[]>}
   */
  countryFeatureIds: {},
}
