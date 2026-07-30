import { state } from './state.js'
import { COUNTRIES } from './countryRegistry.js'
import {
  NORMALIZED_STOPS,
  MACRO_ABSOLUTE_STOPS,
  MICRO_ABSOLUTE_STOPS,
  buildColorExpression,
} from './colorScales.js'
import { updateLegend } from './legend.js'

// ---------------------------------------------------------------------------
// Named constants for MapLibre source and layer IDs
// ---------------------------------------------------------------------------

export const SOURCE_IDS = {
  REGIONS: 'pes-regions-source',
  COUNTRIES: 'pes-countries-source',
}

export const LAYER_IDS = {
  REGIONS_FILL: 'pes-regions-fill',
  REGIONS_BORDERS: 'pes-regions-borders',
  COUNTRIES_BORDERS: 'pes-countries-borders',
}

// ---------------------------------------------------------------------------
// Map colour constants (single source of truth for the theme)
// ---------------------------------------------------------------------------

const MAP_COLORS = {
  DEFAULT_FILL: '#1e293b',   // Slate 800 — base fill before data loads
  BORDER: '#94a3b8',         // Slate 400 — region internal borders
  COUNTRY_OUTLINE: '#ffffff', // White — country outline on hover
  UNAVAILABLE: '#64748b',    // Slate 500 — greyed-out / no-data regions
}

// ---------------------------------------------------------------------------
// Layer creation
// ---------------------------------------------------------------------------

/**
 * Add all MapLibre sources and layers for the solar map.
 * Called once when data first arrives.
 *
 * @param {object} geojsonData        - Enriched region FeatureCollection
 * @param {object} outlineGeojsonData - Country outline FeatureCollection
 */
export function addMapLayers (geojsonData, outlineGeojsonData) {
  const map = state.mapInstance
  if (!map) return

  // Avoid duplicate additions (defensive — caller should check too)
  if (map.getSource(SOURCE_IDS.REGIONS)) return

  map.addSource(SOURCE_IDS.REGIONS, {
    type: 'geojson',
    data: geojsonData,
    promoteId: 'customId',
  })

  map.addSource(SOURCE_IDS.COUNTRIES, {
    type: 'geojson',
    data: outlineGeojsonData,
    promoteId: 'country',
  })

  // Region fill
  map.addLayer({
    id: LAYER_IDS.REGIONS_FILL,
    type: 'fill',
    source: SOURCE_IDS.REGIONS,
    paint: {
      'fill-color': MAP_COLORS.DEFAULT_FILL,
      'fill-opacity': 0.8,
    },
  })

  // Region internal borders
  map.addLayer({
    id: LAYER_IDS.REGIONS_BORDERS,
    type: 'line',
    source: SOURCE_IDS.REGIONS,
    paint: {
      'line-color': MAP_COLORS.BORDER,
      'line-width': 0.5,
      'line-opacity': 0,
    },
  })

  // Country outline borders
  map.addLayer({
    id: LAYER_IDS.COUNTRIES_BORDERS,
    type: 'line',
    source: SOURCE_IDS.COUNTRIES,
    paint: {
      'line-color': MAP_COLORS.COUNTRY_OUTLINE,
      'line-width': 2.5,
      'line-opacity': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        1.0,
        0.0,
      ],
    },
  })

  updateMapStyles()
}

// ---------------------------------------------------------------------------
// Style updates
// ---------------------------------------------------------------------------

/** Cache for the isMicro MapLibre expression, keyed by selected country. */
let _cachedIsMicro = { key: null, expr: null }

/**
 * Build the MapLibre expression that evaluates to true when a feature
 * belongs to the selected country and that country has micro data.
 *
 * Returns `['literal', false]` when the selected country has no micro
 * data (or nothing is selected), and a simple `['==', ...]` match
 * otherwise.  The result is cached by `selCountry` to avoid
 * rebuilding on every hover/toggle.
 */
function buildIsMicroExpression (selCountry) {
  if (_cachedIsMicro.key === selCountry) return _cachedIsMicro.expr

  const config = COUNTRIES[selCountry]
  const expr = config?.hasMicroData
    ? ['==', ['get', 'country'], selCountry]
    : ['literal', false]

  _cachedIsMicro = { key: selCountry, expr }
  return expr
}

/**
 * Re-apply all dynamic paint properties and update the legend.
 * Called on selection change, normalisation toggle, and data refresh.
 */
export function updateMapStyles () {
  const { mapInstance, selectedCountry, isNormalized } = state
  if (
    !mapInstance ||
    !mapInstance.getLayer(LAYER_IDS.REGIONS_FILL) ||
    !mapInstance.getLayer(LAYER_IDS.REGIONS_BORDERS) ||
    !mapInstance.getLayer(LAYER_IDS.COUNTRIES_BORDERS)
  ) return

  const selCountry = selectedCountry || 'none'
  const isMicro = buildIsMicroExpression(selCountry)

  // Reusable sub-expression: true when the feature is hovered
  const isHovered = ['boolean', ['feature-state', 'hover'], false]

  let macroColorExp, microColorExp
  const isMicroMode =
    selCountry !== 'none' && COUNTRIES[selCountry]?.hasMicroData === true

  if (isNormalized) {
    macroColorExp = buildColorExpression('macroNormalized', NORMALIZED_STOPS)
    microColorExp = buildColorExpression('microNormalized', NORMALIZED_STOPS)
  } else {
    macroColorExp = buildColorExpression('macroGeneration', MACRO_ABSOLUTE_STOPS)
    microColorExp = buildColorExpression('microGeneration', MICRO_ABSOLUTE_STOPS)
  }

  // Update legend (only DOM write when mode actually changes)
  updateLegend(isNormalized, isMicroMode)

  // Fill colour
  mapInstance.setPaintProperty(LAYER_IDS.REGIONS_FILL, 'fill-color', [
    'case',
    ['boolean', ['get', 'unavailable'], false],
    MAP_COLORS.UNAVAILABLE,
    ['all', isMicro, ['boolean', ['get', 'microUnavailable'], false]],
    MAP_COLORS.UNAVAILABLE,
    isMicro,
    microColorExp,
    macroColorExp,
  ])

  // Region borders: thick colored outline for hovered micro region,
  // default for other micro regions, soft for macro hover
  mapInstance.setPaintProperty(LAYER_IDS.REGIONS_BORDERS, 'line-color', [
    'case',
    ['all', isMicro, isHovered],
    microColorExp,
    MAP_COLORS.BORDER,
  ])

  mapInstance.setPaintProperty(LAYER_IDS.REGIONS_BORDERS, 'line-width', [
    'case',
    ['all', isMicro, isHovered],
    2.5,
    0.5,
  ])

  mapInstance.setPaintProperty(LAYER_IDS.REGIONS_BORDERS, 'line-opacity', [
    'case',
    ['all', isMicro, isHovered],
    1.0,   // thick coloured border on micro hover
    isMicro,
    1.0,   // normal internal borders when country is selected
    isHovered,
    0.6,   // soft internal borders on macro hover
    0.0,   // hidden otherwise
  ])

  // Country outline colour matched to fill via macro expression
  mapInstance.setPaintProperty(
    LAYER_IDS.COUNTRIES_BORDERS,
    'line-color',
    macroColorExp
  )

  // Opacity: highlight selected, fade others
  mapInstance.setPaintProperty(LAYER_IDS.REGIONS_FILL, 'fill-opacity', [
    'case',
    ['==', selCountry, 'none'],
    ['case', isHovered, 0.55, 0.45],            // no selection: slight brighten on hover
    ['==', ['get', 'country'], selCountry],
    ['case', isHovered, 0.55, 0.45],            // selected country: same hover treatment
    0.1,                                         // non-selected countries: heavily faded
  ])
}
