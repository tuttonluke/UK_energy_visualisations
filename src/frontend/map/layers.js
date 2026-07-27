import { state } from './state.js'
import { COUNTRIES, COUNTRY_KEYS } from './countryRegistry.js'
import {
  NORMALIZED_STOPS,
  MACRO_ABSOLUTE_STOPS,
  MICRO_ABSOLUTE_STOPS,
  buildColorExpression,
} from './colorScales.js'
import { updateLegend } from './legend.js'

// ---------------------------------------------------------------------------
// Named constants for Mapbox source and layer IDs
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
// Layer creation
// ---------------------------------------------------------------------------

/**
 * Add all Mapbox sources and layers for the solar map.
 * Called once when data first arrives.
 *
 * @param {object} geojsonData        - Enriched region FeatureCollection
 * @param {object} outlineGeojsonData - Country outline FeatureCollection
 */
export function addMapLayers (geojsonData, outlineGeojsonData) {
  const map = state.mapInstance

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
      'fill-color': '#1e293b',
      'fill-opacity': 0.8,
    },
  })

  // Region internal borders
  map.addLayer({
    id: LAYER_IDS.REGIONS_BORDERS,
    type: 'line',
    source: SOURCE_IDS.REGIONS,
    paint: {
      'line-color': '#94a3b8',
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
      'line-color': '#ffffff',
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

/**
 * Build the Mapbox expression that evaluates to true when a feature
 * belongs to the selected country and that country has micro data.
 */
function buildIsMicroExpression (selCountry) {
  const noMicroCountries = COUNTRY_KEYS.filter(k => !COUNTRIES[k].hasMicroData)
  const conditions = [['==', ['get', 'country'], selCountry]]
  noMicroCountries.forEach(k => {
    conditions.push(['!=', ['get', 'country'], k])
  })
  return ['all', ...conditions]
}

/**
 * Re-apply all dynamic paint properties and update the legend.
 * Called on selection change, normalisation toggle, and data refresh.
 */
export function updateMapStyles () {
  const { mapInstance, selectedCountry, isNormalized } = state
  if (!mapInstance || !mapInstance.getLayer(LAYER_IDS.REGIONS_FILL)) return

  const selCountry = selectedCountry || 'none'
  const isMicro = buildIsMicroExpression(selCountry)

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
    isMicro,
    microColorExp,
    macroColorExp,
  ])

  // Region borders: visible for selected micro regions, soft on hover otherwise
  mapInstance.setPaintProperty(LAYER_IDS.REGIONS_BORDERS, 'line-opacity', [
    'case',
    isMicro,
    1.0,
    ['boolean', ['feature-state', 'hover'], false],
    0.6,
    0.0,
  ])

  // Country outline colour matched to fill via macro expression
  if (mapInstance.getLayer(LAYER_IDS.COUNTRIES_BORDERS)) {
    mapInstance.setPaintProperty(
      LAYER_IDS.COUNTRIES_BORDERS,
      'line-color',
      macroColorExp
    )
  }

  // Opacity: highlight selected, fade others
  mapInstance.setPaintProperty(LAYER_IDS.REGIONS_FILL, 'fill-opacity', [
    'case',
    ['==', selCountry, 'none'],
    ['case', ['boolean', ['feature-state', 'hover'], false], 0.55, 0.45],
    ['==', ['get', 'country'], selCountry],
    ['case', ['boolean', ['feature-state', 'hover'], false], 0.55, 0.45],
    0.1,
  ])
}
