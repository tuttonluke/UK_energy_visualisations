import { fetchMapRegions, fetchSolarData } from './api.js'
import { MAP_CONFIG, MAP_VIEWS } from './mapConfig.js'
import { escapeHtml } from './utils.js'
import mapboxgl from 'mapbox-gl'
import * as topojson from 'topojson-client'

let mapInstance = null
let currentSolarData = null
let selectedCountry = null
let cachedTopoData = null
let isLoading = false
let hoveredPolygonId = null
let eventsRegistered = false

const popup = new mapboxgl.Popup({
  closeButton: false,
  closeOnClick: false,
  className: 'custom-popup'
})

/**
 * Helper to set the status dot to a single state,
 * removing all other state classes first so it can
 * recover from any previous state (fixes #5).
 */
function setStatusDot (state) {
  const dot = document.getElementById('status-dot')
  dot.classList.remove('pulse', 'connected', 'error')
  dot.classList.add(state)
}

async function loadMapData () {
  if (isLoading) return
  isLoading = true

  try {
    document.getElementById('status-text').textContent = 'Fetching live data...'

    // Use cached TopoJSON if available — it's static geographic boundary
    // data that only changes when the underlying files are updated.
    if (!cachedTopoData) {
      cachedTopoData = await fetchMapRegions()
      if (!cachedTopoData || !cachedTopoData.uk || !cachedTopoData.france) {
        cachedTopoData = null
        throw new Error('Failed to fetch map boundary data from API')
      }
    }

    const solarData = await fetchSolarData()
    if (!solarData) {
      throw new Error('Failed to fetch solar data from API')
    }

    // Detect partial failures — one country's data may be unavailable
    const ukUnavailable = !solarData.uk
    const frUnavailable = !solarData.france
    if (ukUnavailable) console.warn('UK solar data unavailable — regions will show as unavailable')
    if (frUnavailable) console.warn('France solar data unavailable — regions will show as unavailable')

    currentSolarData = solarData

    const ukGeojson = topojson.feature(cachedTopoData.uk, cachedTopoData.uk.objects.data)
    const frGeojson = topojson.feature(cachedTopoData.france, cachedTopoData.france.objects.data)

    // Tag and enrich UK features
    ukGeojson.features.forEach(feature => {
      const customId = `uk-${feature.properties.ID}`
      feature.id = customId
      feature.properties.customId = customId
      feature.properties.country = 'uk'
      feature.properties.unavailable = ukUnavailable
      const mwValue = solarData.uk ? solarData.uk[feature.properties.ID] : null
      feature.properties.generation = mwValue !== undefined && mwValue !== null ? mwValue : 0
      feature.properties.displayName = feature.properties.Area
      feature.properties.displaySub = feature.properties.DNO_Full
      feature.properties.displayId = feature.properties.ID
    })

    // Tag and enrich FR features
    frGeojson.features.forEach(feature => {
      const customId = `fr-${feature.properties.code}`
      feature.id = customId
      feature.properties.customId = customId
      feature.properties.country = 'france'
      feature.properties.unavailable = frUnavailable
      const mwValue = solarData.france ? solarData.france[feature.properties.code] : null
      feature.properties.generation = mwValue !== undefined && mwValue !== null ? mwValue : 0
      feature.properties.displayName = feature.properties.nom
      feature.properties.displaySub = 'France Region'
      feature.properties.displayId = feature.properties.code
    })

    const geojsonData = {
      type: 'FeatureCollection',
      features: [...ukGeojson.features, ...frGeojson.features]
    }

    document.getElementById('status-text').textContent = 'Live / Connected'
    setStatusDot('connected')

    // Update existing source or add new one
    const existingSource = mapInstance.getSource('pes-regions-source')
    if (existingSource) {
      existingSource.setData(geojsonData)
    } else {
      addMapLayers(geojsonData)
    }

    // Register event listeners exactly once, after layers exist
    if (!eventsRegistered) {
      registerMapEvents()
      eventsRegistered = true
    }

    updateStatsPanel()
    // Re-apply highlight if a country was already selected
    highlightCountry(selectedCountry)

  } catch (error) {
    console.error('Failed to load map data:', error)
    document.getElementById('status-text').textContent = 'Data Load Failed'
    setStatusDot('error')
  } finally {
    isLoading = false
  }
}

function updateStatsPanel () {
  const titleEl = document.getElementById('stats-title')
  const valContainer = document.getElementById('stats-value-container')
  const valEl = document.getElementById('total-gen-display')

  if (!selectedCountry || !currentSolarData) {
    titleEl.textContent = 'Select a country'
    valContainer.style.display = 'none'
    return
  }

  valContainer.style.display = 'block'
  if (selectedCountry === 'uk') {
    titleEl.textContent = 'Total GB Output'
    if (!currentSolarData.uk) {
      valEl.textContent = 'Unavailable'
    } else {
      valEl.textContent = currentSolarData.uk.totalGen !== undefined ? currentSolarData.uk.totalGen : '0'
    }
  } else if (selectedCountry === 'france') {
    titleEl.textContent = 'Total France Output'
    if (!currentSolarData.france) {
      valEl.textContent = 'Unavailable'
    } else {
      valEl.textContent = currentSolarData.france.totalGen !== undefined ? currentSolarData.france.totalGen : '0'
    }
  }
}

function highlightCountry (country) {
  if (!mapInstance) return

  if (!country) {
    // Reset to normal opacity
    mapInstance.setPaintProperty('pes-regions-fill', 'fill-opacity', [
      'case',
      ['boolean', ['feature-state', 'hover'], false],
      0.8,
      0.4
    ])
    return
  }

  mapInstance.setPaintProperty('pes-regions-fill', 'fill-opacity', [
    'case',
    ['==', ['get', 'country'], country],
    [
      'case',
      ['boolean', ['feature-state', 'hover'], false],
      0.8,
      0.4
    ],
    0.1 // other countries fade
  ])
}

function addMapLayers (geojsonData) {
  // Add map source
  mapInstance.addSource('pes-regions-source', {
    type: 'geojson',
    data: geojsonData,
    promoteId: 'customId'
  })

  // Map background colour
  mapInstance.addLayer({
    id: 'pes-regions-fill',
    type: 'fill',
    source: 'pes-regions-source',
    paint: {
      'fill-color': [
        'interpolate',
        ['linear'],
        ['get', 'generation'],
        0,
        '#1e293b', // Slate 800 (Night/Zero)
        50,
        '#fcd34d', // Amber 300
        200,
        '#fbbf24', // Amber 400
        500,
        '#f59e0b', // Amber 500
        1000,
        '#ea580c', // Orange 600
        2000,
        '#dc2626', // Red 600
        3000,
        '#991b1b' // Red 800
      ],
      'fill-opacity': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        0.8, // opacity when hovered
        0.4 // opacity when not hovered
      ]
    }
  })

  // Add region borders
  mapInstance.addLayer({
    id: 'pes-regions-borders',
    type: 'line',
    source: 'pes-regions-source',
    paint: {
      'line-color': '#94a3b8', // Slate 400
      'line-width': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        2.5, // Thick border on hover
        0.5 // Thin border otherwise
      ]
    }
  })
}

/**
 * Registers all interactive event listeners for the map.
 * Called exactly once after layers have been added (guarded by eventsRegistered).
 */
function registerMapEvents () {
  // Mouse events
  mapInstance.on('mousemove', 'pes-regions-fill', e => {
    if (e.features.length > 0) {
      const currentFeature = e.features[0]

      if (hoveredPolygonId !== null) {
        mapInstance.setFeatureState(
          { source: 'pes-regions-source', id: hoveredPolygonId },
          { hover: false }
        )
      }
      hoveredPolygonId = currentFeature.properties.customId || currentFeature.id
      mapInstance.setFeatureState(
        { source: 'pes-regions-source', id: hoveredPolygonId },
        { hover: true }
      )

      // Tooltip logic
      const regionName = currentFeature.properties.displayName
      const subName = currentFeature.properties.displaySub
      const displayId = currentFeature.properties.displayId
      const generationMw = currentFeature.properties.generation
      const isUnavailable = currentFeature.properties.unavailable

      let displayRegionData
      if (isUnavailable) {
        displayRegionData = 'Data Unavailable'
      } else if (generationMw !== undefined && generationMw !== null) {
        displayRegionData = `${generationMw} MW`
      } else {
        displayRegionData = '0 MW (Offline)'
      }

      popup
        .setLngLat(e.lngLat)
        .setHTML(
          `
                    <div>
                        <h3 style="margin:0; color:var(--accent); font-size:1.125rem;">${escapeHtml(regionName)}</h3>
                        <p style="margin:4px 0 0 0; color:var(--text-muted); font-size:0.75rem;">${escapeHtml(subName)}</p>
                        <p style="margin:0; color:var(--text-muted); font-size:0.75rem; opacity: 0.8;">ID: ${escapeHtml(String(displayId))}</p>
                        <hr style="border-color:var(--border-color); margin:8px 0;">
                        <p style="margin:0; color:var(--text-muted); font-size:0.875rem;">Region Output:</p>
                        <p style="margin:0; color:var(--text-main); font-size:1.25rem; font-weight:bold;">${escapeHtml(displayRegionData)}</p>
                    </div>
                `
        )
        .addTo(mapInstance)
    }
  })

  // When mouse leaves regions entirely
  mapInstance.on('mouseleave', 'pes-regions-fill', () => {
    if (hoveredPolygonId !== null) {
      mapInstance.setFeatureState(
        { source: 'pes-regions-source', id: hoveredPolygonId },
        { hover: false }
      )
    }
    hoveredPolygonId = null
    mapInstance.getCanvas().style.cursor = ''
    popup.remove()
  })

  // Change cursor on hover
  mapInstance.on('mouseenter', 'pes-regions-fill', () => {
    mapInstance.getCanvas().style.cursor = 'pointer'
  })

  // Click on a country feature
  mapInstance.on('click', 'pes-regions-fill', e => {
    if (e.features.length > 0) {
      const clickedCountry = e.features[0].properties.country
      selectedCountry = clickedCountry
      updateStatsPanel()
      highlightCountry(selectedCountry)

      if (selectedCountry === 'uk') {
        mapInstance.flyTo(MAP_VIEWS.UK)
      } else if (selectedCountry === 'france') {
        mapInstance.flyTo(MAP_VIEWS.FRANCE)
      }
    }
  })

  // Click outside to deselect
  mapInstance.on('click', e => {
    const features = mapInstance.queryRenderedFeatures(e.point, { layers: ['pes-regions-fill'] })
    if (features.length === 0) {
      selectedCountry = null
      updateStatsPanel()
      highlightCountry(null)
    }
  })

  // Hook up stats panel click to deselect too
  document.getElementById('solar-stats').addEventListener('click', (e) => {
    e.stopPropagation()
    selectedCountry = null
    updateStatsPanel()
    highlightCountry(null)
    mapInstance.flyTo(MAP_VIEWS.DEFAULT)
  })
}

export async function initMap () {
  if (mapInstance) {
    setTimeout(() => mapInstance.resize(), 100)
    return
  }

  // Dummy token — all Mapbox API requests are proxied through the backend
  // which injects the real token. Do not replace this with a real key.
  mapboxgl.accessToken = 'pk.dummy'

  // Map configuration
  mapInstance = new mapboxgl.Map({
    container: 'map',
    ...MAP_CONFIG,
    pitch: 20
  })

  // Handle map style/tile load errors
  mapInstance.on('error', (e) => {
    console.error('Mapbox error:', e.error?.message || e)
    document.getElementById('status-text').textContent = 'Map load failed'
    setStatusDot('error')
  })

  mapInstance.on('load', () => {
    loadMapData()
  })
}

/**
 * Refresh map data without re-creating the map instance.
 * Called by the polling interval in app.js.
 */
export async function updateMapData () {
  if (!mapInstance) return
  await loadMapData()
}
