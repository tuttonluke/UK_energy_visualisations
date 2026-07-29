import { fetchRiverLevels } from './api.js'
import { MAP_CONFIG } from './mapConfig.js'
import { escapeHtml } from './utils.js'
import * as maplibregl from 'maplibre-gl'
import { ensurePMTilesProtocol } from './mapSetup.js'

let envMapInstance = null

async function loadEnvMapData () {
  try {
    document.getElementById('env-status-text').innerText =
      'Fetching live river data...'

    if (envMapInstance.getLayer('waterway')) {
      envMapInstance.setPaintProperty('waterway', 'line-color', '#3b82f6') // blue-500
      envMapInstance.setPaintProperty('waterway', 'line-width', [
        'interpolate',
        ['linear'],
        ['zoom'],
        4,
        1.5,
        10,
        3.5
      ])
      envMapInstance.setPaintProperty('waterway', 'line-opacity', 1.0)
    }

    // Fetch Environment Agency Data
    const eaData = await fetchRiverLevels()

    if (!eaData || !eaData.data) {
      throw new Error('Failed to fetch river data from API')
    }

    document.getElementById(
      'env-status-text'
    ).innerText = `Live / Connected (${eaData.data.length} stations)`
    document
      .getElementById('env-status-dot')
      .classList.replace('pulse', 'connected')

    const geojsonFeatures = eaData.data.map(station => {
      let status = 1 // 0 = low, 1 = normal, 2 = high
      if (station.value > station.typicalRangeHigh) {
        status = 2
      } else if (station.value < station.typicalRangeLow) {
        status = 0
      }

      return {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [station.long, station.lat]
        },
        properties: {
          id: station.stationReference,
          name: station.label,
          river: station.riverName,
          value: station.value,
          high: station.typicalRangeHigh,
          low: station.typicalRangeLow,
          status: status
        }
      }
    })

    const stationsGeoJSON = {
      type: 'FeatureCollection',
      features: geojsonFeatures
    }

    // Update existing source or add new one
    const existingSource = envMapInstance.getSource('ea-stations')
    if (existingSource) {
      existingSource.setData(stationsGeoJSON)
    } else {
      addEnvMapLayers(stationsGeoJSON)
    }
  } catch (error) {
    console.error('Failed to load env map data:', error)
    document.getElementById('env-status-text').innerText = 'Data Load Failed'
    document.getElementById('env-status-dot').classList.replace('connected', 'error')
    document.getElementById('env-status-dot').classList.replace('pulse', 'error')
  }
}

function addEnvMapLayers (stationsGeoJSON) {
  // Add source
  envMapInstance.addSource('ea-stations', {
    type: 'geojson',
    data: stationsGeoJSON
  })

  // Add circle layer
  envMapInstance.addLayer({
    id: 'ea-stations-layer',
    type: 'circle',
    source: 'ea-stations',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 3, 10, 6],
      'circle-color': [
        'match',
        ['get', 'status'],
        0,
        '#fcd34d', // Low (Amber)
        1,
        '#10b981', // Normal (Emerald)
        2,
        '#ef4444', // High (Red)
        '#94a3b8' // Default (Slate)
      ],
      'circle-opacity': 0.8,
      'circle-stroke-width': 1,
      'circle-stroke-color': '#0f172a'
    }
  })

  const popup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: false,
    className: 'custom-popup env-popup'
  })

  // Hover interactions
  envMapInstance.on('mousemove', 'ea-stations-layer', e => {
    envMapInstance.getCanvas().style.cursor = 'pointer'
    if (e.features.length > 0) {
      const feature = e.features[0]
      const props = feature.properties

      let statusText = 'Normal'
      let statusColor = 'var(--success)'
      if (props.status === 2) {
        statusText = 'High'
        statusColor = 'var(--danger)'
      } else if (props.status === 0) {
        statusText = 'Low'
        statusColor = 'var(--accent)'
      }

      const val = parseFloat(props.value) || 0
      const high = parseFloat(props.high) || 0
      const low = parseFloat(props.low) || 0

      popup
        .setLngLat(feature.geometry.coordinates)
        .setHTML(
          `
                    <div>
                        <h3 style="margin:0; color:var(--text-main); font-size:1rem;">${escapeHtml(
                          props.name
                        )}</h3>
                        <p style="margin:2px 0 8px 0; color:var(--text-muted); font-size:0.75rem;">${escapeHtml(
                          props.river || 'Unknown River'
                        )}</p>
                        
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px; gap: 12px">
                            <span style="color:var(--text-muted); font-size:0.875rem;">Status:</span>
                            <span style="color:${statusColor}; font-weight:bold; font-size:0.875rem;">${statusText}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px; gap: 12px">
                            <span style="color:var(--text-muted); font-size:0.875rem;">Current Level:</span>
                            <span style="color:var(--text-main); font-size:0.875rem;">${val.toFixed(
                              2
                            )} m</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; gap: 12px;">
                            <span style="color:var(--text-muted); font-size:0.875rem;">Typical Range:</span>
                            <span style="color:var(--text-muted); font-size:0.875rem;">${low.toFixed(
                              2
                            )} - ${high.toFixed(2)} m</span>
                        </div>
                    </div>
                `
        )
        .addTo(envMapInstance)
    }
  })

  envMapInstance.on('mouseleave', 'ea-stations-layer', () => {
    envMapInstance.getCanvas().style.cursor = ''
    popup.remove()
  })
}

const ENV_MAX_RETRIES = 3
const ENV_LOAD_TIMEOUT_MS = 10_000
let resetBtnRegistered = false

export async function initEnvMap () {
  if (envMapInstance) {
    setTimeout(() => envMapInstance.resize(), 100)
    return
  }

  ensurePMTilesProtocol()
  createEnvMapWithRetry()
}

function createEnvMapWithRetry (attempt = 1) {
  if (attempt > 1) {
    document.getElementById('env-status-text').innerText =
      `Retrying map load (${attempt}/${ENV_MAX_RETRIES + 1})…`
  }

  const map = new maplibregl.Map({
    container: 'env-map',
    ...MAP_CONFIG,
    pitch: 0
  })

  // Timeout — if the style hasn't loaded in time, tear down and retry
  const loadTimer = setTimeout(() => {
    console.warn(`Env map style load timed out (attempt ${attempt}/${ENV_MAX_RETRIES + 1})`)
    map.remove()

    if (attempt <= ENV_MAX_RETRIES) {
      createEnvMapWithRetry(attempt + 1)
    } else {
      document.getElementById('env-status-text').innerText = 'Map load failed'
      document.getElementById('env-status-dot').classList.replace('pulse', 'error')
    }
  }, ENV_LOAD_TIMEOUT_MS)

  // Log errors but don't surface them — let the timeout handle failures
  map.on('error', (e) => {
    console.error('MapLibre error:', e.error?.message || e)
  })

  map.on('load', () => {
    clearTimeout(loadTimer)
    envMapInstance = map
    loadEnvMapData()
  })

  // Register reset button listener only once
  if (!resetBtnRegistered) {
    resetBtnRegistered = true
    const resetBtn = document.getElementById('env-map-reset')
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (!envMapInstance) return
        envMapInstance.flyTo({
          center: MAP_CONFIG.center,
          zoom: MAP_CONFIG.zoom,
          pitch: 0,
          bearing: 0
        })
      })
    }
  }
}

/**
 * Refresh environment map data without re-creating the map instance.
 * Called by the polling interval in app.js.
 */
export async function updateEnvMapData () {
  if (!envMapInstance) return
  await loadEnvMapData()
}
