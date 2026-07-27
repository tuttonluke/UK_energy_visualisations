/**
 * Solar map module — public API.
 *
 * This thin orchestrator wires together the sub-modules.
 * All heavy logic lives in dedicated files:
 *   - countryRegistry.js  — data-driven country configuration
 *   - colorScales.js      — palettes and Mapbox expression builders
 *   - dataEnricher.js     — TopoJSON → enriched GeoJSON pipeline
 *   - layers.js           — Mapbox source/layer management and styling
 *   - events.js           — hover, click, toggle event handlers
 *   - tooltip.js          — popup HTML builder
 *   - statsPanel.js       — stats panel DOM updates
 *   - legend.js           — legend DOM updates
 *   - state.js            — centralised mutable state
 */

import mapboxgl from 'mapbox-gl'
import { fetchMapRegions, fetchSolarData } from '../api.js'
import { MAP_CONFIG, MAP_VIEWS } from '../mapConfig.js'
import { state } from './state.js'
import { enrichMapData } from './dataEnricher.js'
import { addMapLayers, updateMapStyles, SOURCE_IDS } from './layers.js'
import { registerMapEvents } from './events.js'
import { updateStatsPanel } from './statsPanel.js'

// ---------------------------------------------------------------------------
// Status-dot helper
// ---------------------------------------------------------------------------

/**
 * Set the status dot to a single state, removing all other
 * state classes first so it can recover from any previous
 * state (fixes #5).
 */
function setStatusDot (statusClass) {
  const dot = document.getElementById('status-dot')
  if (!dot) return
  dot.classList.remove('pulse', 'connected', 'error')
  dot.classList.add(statusClass)
}

// ---------------------------------------------------------------------------
// Core data-loading pipeline
// ---------------------------------------------------------------------------

async function loadMapData () {
  if (state.isLoading) return
  state.isLoading = true

  try {
    const statusText = document.getElementById('status-text')
    if (statusText) statusText.textContent = 'Fetching live data...'

    // Use cached TopoJSON if available — it's static boundary data
    if (!state.cachedTopoData) {
      state.cachedTopoData = await fetchMapRegions()
      if (!state.cachedTopoData) {
        throw new Error('Failed to fetch map boundary data from API')
      }
    }

    const solarData = await fetchSolarData()
    if (!solarData) {
      throw new Error('Failed to fetch solar data from API')
    }
    state.currentSolarData = solarData

    // Enrich geographic data with generation values
    const { geojsonData, outlineGeojsonData, countryFeatureIds } =
      enrichMapData(state.cachedTopoData, solarData)

    // Overwrite (not append) the feature-ID lookup — fixes the unbounded-growth bug
    state.countryFeatureIds = countryFeatureIds

    if (statusText) statusText.textContent = 'Live / Connected'
    setStatusDot('connected')

    // Update existing source or add new one
    const existingSource = state.mapInstance.getSource(SOURCE_IDS.REGIONS)
    if (existingSource) {
      existingSource.setData(geojsonData)
      state.mapInstance.getSource(SOURCE_IDS.COUNTRIES).setData(outlineGeojsonData)
    } else {
      addMapLayers(geojsonData, outlineGeojsonData)
    }

    // Register event listeners exactly once, after layers exist
    if (!state.eventsRegistered) {
      registerMapEvents()
      state.eventsRegistered = true
    }

    updateStatsPanel(state.selectedCountry, state.currentSolarData)
    updateMapStyles()
  } catch (error) {
    console.error('Failed to load map data:', error)
    const statusText = document.getElementById('status-text')
    if (statusText) statusText.textContent = 'Data Load Failed'
    setStatusDot('error')
  } finally {
    state.isLoading = false
  }
}

// ---------------------------------------------------------------------------
// Public exports (consumed by app.js)
// ---------------------------------------------------------------------------

/**
 * Initialise the Mapbox map instance and trigger the first data load.
 * Safe to call multiple times — subsequent calls only resize.
 *
 * Uses an automatic retry mechanism: if the map style fails to load
 * within LOAD_TIMEOUT_MS (common with proxy setups due to transient
 * network / timing issues), the map is destroyed and re-created.
 */
export async function initMap () {
  if (state.mapInstance) {
    setTimeout(() => state.mapInstance.resize(), 100)
    return
  }

  // Dummy token — all Mapbox API requests are proxied through the backend
  // which injects the real token. Do not replace this with a real key.
  mapboxgl.accessToken = 'pk.dummy'

  createMapWithRetry()
}

const MAX_RETRIES = 3
const LOAD_TIMEOUT_MS = 10_000

function createMapWithRetry (attempt = 1) {
  const statusText = document.getElementById('status-text')

  if (attempt > 1 && statusText) {
    statusText.textContent = `Retrying map load (${attempt}/${MAX_RETRIES + 1})…`
    setStatusDot('pulse')
  }

  const map = new mapboxgl.Map({
    container: 'map',
    ...MAP_CONFIG,
    center: MAP_VIEWS.DEFAULT.center,
    zoom: MAP_VIEWS.DEFAULT.zoom,
    pitch: 20,
  })

  // Timeout — if the style hasn't loaded in time, tear down and retry
  const loadTimer = setTimeout(() => {
    console.warn(`Map style load timed out (attempt ${attempt}/${MAX_RETRIES + 1})`)
    map.remove()

    if (attempt <= MAX_RETRIES) {
      createMapWithRetry(attempt + 1)
    } else {
      if (statusText) statusText.textContent = 'Map load failed'
      setStatusDot('error')
    }
  }, LOAD_TIMEOUT_MS)

  // Log errors but don't surface them to the UI — let the timeout
  // handle genuine failures so transient tile/telemetry errors
  // don't prematurely mark the map as broken.
  map.on('error', e => {
    console.error('Mapbox error:', e.error?.message || e)
  })

  map.on('load', () => {
    clearTimeout(loadTimer)
    state.mapInstance = map
    loadMapData()
  })
}

/**
 * Refresh map data without re-creating the map instance.
 * Called by the polling interval in app.js.
 */
export async function updateMapData () {
  if (!state.mapInstance) return
  await loadMapData()
}
