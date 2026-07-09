import { fetchMapRegions, fetchSolarData, BACKEND_URL } from './api.js'
import { MAP_CONFIG } from './mapConfig.js'
import { escapeHtml } from './utils.js'
import mapboxgl from 'mapbox-gl'
import * as topojson from 'topojson-client'

let mapInstance = null
let currentSolarData = null

async function loadMapData () {
  try {
    document.getElementById('status-text').innerText = 'Fetching live data...'

    const [rawTopoData, solarData] = await Promise.all([
      fetchMapRegions(),
      fetchSolarData()
    ])

    if (!rawTopoData || !solarData) {
      throw new Error('Failed to fetch map or solar data from API')
    }

    currentSolarData = solarData

    const geojsonData = topojson.feature(rawTopoData, rawTopoData.objects.data)

    // Update UI Total
    const totalGen = solarData.totalGen
    document.getElementById('total-gen-display').innerText =
      totalGen !== undefined ? totalGen : '0'
    document.getElementById('status-text').innerText = 'Live / Connected'
    document
      .getElementById('status-dot')
      .classList.replace('pulse', 'connected')

    // Map properties
    geojsonData.features.forEach(feature => {
      feature.id = feature.properties.ID
      const mwValue = solarData[feature.id]
      feature.properties.generation =
        mwValue !== undefined && mwValue !== null ? mwValue : 0
    })

    // Update existing source or add new one
    const existingSource = mapInstance.getSource('pes-regions-source')
    if (existingSource) {
      existingSource.setData(geojsonData)
    } else {
      addMapLayers(geojsonData)
    }
  } catch (error) {
    console.error('Failed to load map data:', error)
    document.getElementById('status-text').innerText = 'Data Load Failed'
    document.getElementById('status-dot').classList.replace('connected', 'error')
    document.getElementById('status-dot').classList.replace('pulse', 'error')
  }
}

function addMapLayers (geojsonData) {
  // Add map source
  mapInstance.addSource('pes-regions-source', {
    type: 'geojson',
    data: geojsonData
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

  // Tooltip object
  const popup = new mapboxgl.Popup({
    closeButton: false,
    closeOnClick: false,
    className: 'custom-popup'
  })

  let hoveredPolygonId = null

  // Mouse events
  mapInstance.on('mousemove', 'pes-regions-fill', e => {
    if (e.features.length > 0) {
      const currentFeature = e.features[0]

      if (hoveredPolygonId != null) {
        mapInstance.setFeatureState(
          { source: 'pes-regions-source', id: hoveredPolygonId },
          { hover: false }
        )
      }
      hoveredPolygonId = currentFeature.id
      mapInstance.setFeatureState(
        { source: 'pes-regions-source', id: hoveredPolygonId },
        { hover: true }
      )

      // Tooltip logic
      const regionName = currentFeature.properties.Area
      const dnoName = currentFeature.properties.DNO_Full
      const generationMw = currentSolarData
        ? currentSolarData[currentFeature.id]
        : null

      const displayRegionData =
        generationMw !== undefined && generationMw !== null
          ? `${generationMw} MW`
          : '0 MW (Offline)'

      popup
        .setLngLat(e.lngLat)
        .setHTML(
          `
                    <div>
                        <h3 style="margin:0; color:var(--accent); font-size:1.125rem;">${escapeHtml(regionName)}</h3>
                        <p style="margin:4px 0 0 0; color:var(--text-muted); font-size:0.75rem;">${escapeHtml(dnoName)}</p>
                        <p style="margin:0; color:var(--text-muted); font-size:0.75rem; opacity: 0.8;">PES ID: ${escapeHtml(currentFeature.id)}</p>
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
}

export async function initMap () {
  if (mapInstance) {
    setTimeout(() => mapInstance.resize(), 100)
    return
  }

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
    document.getElementById('status-text').innerText = 'Map load failed'
    document.getElementById('status-dot').classList.replace('pulse', 'error')
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
