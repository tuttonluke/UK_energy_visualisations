/**
 * Solar map module — public API.
 *
 * This thin orchestrator wires together the sub-modules.
 * All heavy logic lives in dedicated files:
 *   - countryRegistry.js  — data-driven country configuration
 *   - colorScales.js      — palettes and MapLibre expression builders
 *   - dataEnricher.js     — TopoJSON → enriched GeoJSON pipeline
 *   - layers.js           — MapLibre source/layer management and styling
 *   - events.js           — hover, click, toggle event handlers
 *   - tooltip.js          — popup HTML builder
 *   - statsPanel.js       — stats panel DOM updates
 *   - legend.js           — legend DOM updates
 *   - state.js            — centralised mutable state
 */

import * as maplibregl from 'maplibre-gl'
import { ensurePMTilesProtocol } from '../mapSetup.js'
import { fetchMapRegions, fetchSolarData } from '../api.js'
import { MAP_CONFIG, MAP_VIEWS } from '../mapConfig.js'
import { state } from './state.js'
import { enrichMapData } from './dataEnricher.js'
import { addMapLayers, updateMapStyles, SOURCE_IDS } from './layers.js'
import { registerMapEvents } from './events.js'
import { updateStatsPanel } from './statsPanel.js'

// ---------------------------------------------------------------------------
// Status UI helpers
// ---------------------------------------------------------------------------

/** Lazily cached DOM references for status indicators. */
let _statusText = null
let _statusDot = null

function getStatusText () {
  if (!_statusText) _statusText = document.getElementById('status-text')
  return _statusText
}

/**
 * Set the status dot to a single state, removing all other
 * state classes first so it can recover from any previous
 * state (fixes #5).
 */
function setStatusDot (statusClass) {
  if (!_statusDot) _statusDot = document.getElementById('status-dot')
  if (!_statusDot) return
  _statusDot.classList.remove('pulse', 'connected', 'error')
  _statusDot.classList.add(statusClass)
}

// ---------------------------------------------------------------------------
// Core data-loading pipeline
// ---------------------------------------------------------------------------

async function loadMapData () {
  if (state.isLoading) return
  if (!state.mapInstance) return
  state.isLoading = true

  const statusText = getStatusText()

  try {
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
    let geojsonData, outlineGeojsonData, countryFeatureIds
    try {
      ({ geojsonData, outlineGeojsonData, countryFeatureIds } =
        enrichMapData(state.cachedTopoData, solarData))
    } catch (enrichErr) {
      throw new Error(`Data enrichment failed: ${enrichErr.message}`)
    }

    // Overwrite (not append) the feature-ID lookup — fixes the unbounded-growth bug
    state.countryFeatureIds = countryFeatureIds

    if (statusText) statusText.textContent = 'Live / Connected'
    setStatusDot('connected')

    // Update existing source or add new one
    const existingSource = state.mapInstance.getSource(SOURCE_IDS.REGIONS)
    if (existingSource) {
      existingSource.setData(geojsonData)
      const countriesSource = state.mapInstance.getSource(SOURCE_IDS.COUNTRIES)
      if (countriesSource) countriesSource.setData(outlineGeojsonData)
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
    if (statusText) statusText.textContent = 'Data Load Failed'
    setStatusDot('error')
  } finally {
    state.isLoading = false
  }
}

// ---------------------------------------------------------------------------
// Public exports (consumed by app.js)
// ---------------------------------------------------------------------------

const MAX_ATTEMPTS = 4
const LOAD_TIMEOUT_MS = 10_000

/**
 * Initialise the MapLibre map instance and trigger the first data load.
 * Safe to call multiple times — subsequent calls only resize.
 *
 * Uses an automatic retry mechanism: if the map style fails to load
 * within LOAD_TIMEOUT_MS (common with proxy setups due to transient
 * network / timing issues), the map is destroyed and re-created.
 */
export function initMap () {
  if (state.mapInstance) {
    // Brief delay ensures the container has finished its CSS transition
    // before MapLibre measures the new dimensions.
    setTimeout(() => state.mapInstance.resize(), 100)
    return
  }

  ensurePMTilesProtocol()

  createMapWithRetry()
}

function createMapWithRetry (attempt = 1) {
  const statusText = getStatusText()

  if (attempt > 1 && statusText) {
    statusText.textContent = `Retrying map load (attempt ${attempt} of ${MAX_ATTEMPTS})…`
    setStatusDot('pulse')
  }

  const map = new maplibregl.Map({
    container: 'map',
    ...MAP_CONFIG,
    ...MAP_VIEWS.DEFAULT,
  })

  // Timeout — if the style hasn't loaded in time, tear down and retry
  const loadTimer = setTimeout(() => {
    console.warn(`Map style load timed out (attempt ${attempt} of ${MAX_ATTEMPTS})`)
    map.remove()

    if (attempt < MAX_ATTEMPTS) {
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
    console.error('MapLibre error:', e.error?.message || e)
  })

  map.on('load', () => {
    clearTimeout(loadTimer)
    // Guard against a late-firing load event after the timeout already
    // removed this map instance and started a retry.
    if (!map.getContainer()) return
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
