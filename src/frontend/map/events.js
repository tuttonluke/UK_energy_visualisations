import mapboxgl from 'mapbox-gl'
import { MAP_VIEWS } from '../mapConfig.js'
import { COUNTRIES } from './countryRegistry.js'
import { state } from './state.js'
import { SOURCE_IDS, LAYER_IDS, updateMapStyles } from './layers.js'
import { updateStatsPanel } from './statsPanel.js'
import { buildTooltipHtml } from './tooltip.js'

const popup = new mapboxgl.Popup({
  closeButton: false,
  closeOnClick: false,
  className: 'custom-popup',
})

// ---------------------------------------------------------------------------
// Hover helpers
// ---------------------------------------------------------------------------

/** Clear the current hover state from the map. */
function clearHover () {
  const { mapInstance, hoveredState, countryFeatureIds } = state
  if (!hoveredState) return

  if (hoveredState.type === 'macro') {
    countryFeatureIds[hoveredState.country].forEach(id => {
      mapInstance.setFeatureState(
        { source: SOURCE_IDS.REGIONS, id },
        { hover: false }
      )
    })
    mapInstance.setFeatureState(
      { source: SOURCE_IDS.COUNTRIES, id: hoveredState.country },
      { hover: false }
    )
  } else {
    mapInstance.setFeatureState(
      { source: SOURCE_IDS.REGIONS, id: hoveredState.id },
      { hover: false }
    )
  }

  state.hoveredState = null
}

/**
 * Format the generation value for tooltip display.
 *
 * @returns {{ displayRegionData: string, displayNormalizedData: string }}
 */
function formatGenerationDisplay (isUnavailable, generationMw, normalizedValue) {
  if (isUnavailable) {
    return { displayRegionData: 'Data Unavailable', displayNormalizedData: '--' }
  }
  if (generationMw !== undefined && generationMw !== null) {
    return {
      displayRegionData: `${Number(generationMw).toFixed(1)} MW`,
      displayNormalizedData: `${Number(normalizedValue).toFixed(4)} MW/km²`,
    }
  }
  return { displayRegionData: '0 MW (Offline)', displayNormalizedData: '0 MW/km²' }
}

/**
 * Determine the output label for the tooltip.
 */
function getOutputLabel (country, isMicro) {
  const config = COUNTRIES[country]
  if (!config?.hasMicroData) return 'National Output (Regional N/A):'
  return isMicro ? 'Regional Output:' : 'National Output:'
}

// ---------------------------------------------------------------------------
// Public
// ---------------------------------------------------------------------------

/**
 * Register all interactive event listeners for the map.
 * Called exactly once after layers have been added (guarded by state.eventsRegistered).
 */
export function registerMapEvents () {
  const { mapInstance } = state

  // -----------------------------------------------------------------------
  // Mousemove — hover highlight + tooltip
  // -----------------------------------------------------------------------
  mapInstance.on('mousemove', LAYER_IDS.REGIONS_FILL, e => {
    if (e.features.length === 0) return

    const feature = e.features[0]
    const country = feature.properties.country
    const config = COUNTRIES[country]
    const isMicro = state.selectedCountry === country && config?.hasMicroData

    // Clear previous hover
    clearHover()

    const currentRegionId = feature.properties.customId || feature.id

    // Set new hover
    if (!isMicro) {
      // Macro: highlight all regions in the country + outline
      state.countryFeatureIds[country].forEach(id => {
        mapInstance.setFeatureState(
          { source: SOURCE_IDS.REGIONS, id },
          { hover: true }
        )
      })
      mapInstance.setFeatureState(
        { source: SOURCE_IDS.COUNTRIES, id: country },
        { hover: true }
      )
      state.hoveredState = { type: 'macro', country }
    } else {
      // Micro: highlight just the hovered region
      mapInstance.setFeatureState(
        { source: SOURCE_IDS.REGIONS, id: currentRegionId },
        { hover: true }
      )
      state.hoveredState = { type: 'micro', id: currentRegionId }
    }

    // Build tooltip data
    const generationMw = isMicro
      ? feature.properties.microGeneration
      : feature.properties.macroGeneration
    const normalizedValue = isMicro
      ? feature.properties.microNormalized
      : feature.properties.macroNormalized

    const { displayRegionData, displayNormalizedData } = formatGenerationDisplay(
      feature.properties.unavailable,
      generationMw,
      normalizedValue
    )

    popup
      .setLngLat(e.lngLat)
      .setHTML(
        buildTooltipHtml({
          country,
          isMicro,
          regionName: feature.properties.displayName,
          subName: feature.properties.displaySub,
          displayId: feature.properties.displayId,
          outputLabel: getOutputLabel(country, isMicro),
          displayRegionData,
          displayNormalizedData,
        })
      )
      .addTo(mapInstance)
  })

  // -----------------------------------------------------------------------
  // Mouseleave — clear hover + tooltip
  // -----------------------------------------------------------------------
  mapInstance.on('mouseleave', LAYER_IDS.REGIONS_FILL, () => {
    clearHover()
    mapInstance.getCanvas().style.cursor = ''
    popup.remove()
  })

  // -----------------------------------------------------------------------
  // Mouseenter — pointer cursor
  // -----------------------------------------------------------------------
  mapInstance.on('mouseenter', LAYER_IDS.REGIONS_FILL, () => {
    mapInstance.getCanvas().style.cursor = 'pointer'
  })

  // -----------------------------------------------------------------------
  // Click on a region — select/zoom into country
  // -----------------------------------------------------------------------
  mapInstance.on('click', LAYER_IDS.REGIONS_FILL, e => {
    if (e.features.length === 0) return

    const clickedCountry = e.features[0].properties.country
    state.selectedCountry = clickedCountry
    updateStatsPanel(state.selectedCountry, state.currentSolarData)
    updateMapStyles()

    const config = COUNTRIES[clickedCountry]
    if (config?.mapView) {
      mapInstance.flyTo(config.mapView)
    }
  })

  // -----------------------------------------------------------------------
  // Click outside regions — deselect
  // -----------------------------------------------------------------------
  mapInstance.on('click', e => {
    const features = mapInstance.queryRenderedFeatures(e.point, {
      layers: [LAYER_IDS.REGIONS_FILL],
    })
    if (features.length === 0) {
      state.selectedCountry = null
      updateStatsPanel(state.selectedCountry, state.currentSolarData)
      updateMapStyles()
    }
  })

  // -----------------------------------------------------------------------
  // Stats panel click — deselect + reset view
  // -----------------------------------------------------------------------
  const statsPanel = document.getElementById('solar-stats')
  if (statsPanel) {
    statsPanel.addEventListener('click', e => {
      e.stopPropagation()
      state.selectedCountry = null
      updateStatsPanel(state.selectedCountry, state.currentSolarData)
      updateMapStyles()
      mapInstance.flyTo(MAP_VIEWS.DEFAULT)
    })
  }

  // -----------------------------------------------------------------------
  // Normalise toggle
  // -----------------------------------------------------------------------
  const toggle = document.getElementById('normalize-toggle')
  if (toggle) {
    toggle.addEventListener('click', e => {
      state.isNormalized = e.target.checked
      updateMapStyles()
    })
  }

  // -----------------------------------------------------------------------
  // Reset button
  // -----------------------------------------------------------------------
  const resetBtn = document.getElementById('solar-map-reset')
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      state.selectedCountry = null
      updateStatsPanel(state.selectedCountry, state.currentSolarData)
      updateMapStyles()
      mapInstance.flyTo({
        center: MAP_VIEWS.DEFAULT.center,
        zoom: MAP_VIEWS.DEFAULT.zoom,
        pitch: 20,
        bearing: 0,
      })
    })
  }
}
