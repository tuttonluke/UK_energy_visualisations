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
let hoveredState = null // { type: 'macro' | 'micro', id: string, country: string }
let eventsRegistered = false
let isNormalized = true
const countryFeatureIds = { uk: [], france: [], germany: [] }

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
      if (!cachedTopoData || !cachedTopoData.uk || !cachedTopoData.france || !cachedTopoData.germany) {
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
    const deUnavailable = !solarData.germany
    if (ukUnavailable) console.warn('UK solar data unavailable — regions will show as unavailable')
    if (frUnavailable) console.warn('France solar data unavailable — regions will show as unavailable')
    if (deUnavailable) console.warn('Germany solar data unavailable — regions will show as unavailable')

    currentSolarData = solarData

    // 1. Calculate Areas using Turf.js
    const countryAreas = { uk: 0, france: 0, germany: 0 }
    const ukGeojson = topojson.feature(cachedTopoData.uk, cachedTopoData.uk.objects.data)
    const frGeojson = topojson.feature(cachedTopoData.france, cachedTopoData.france.objects.data)
    const deGeojson = topojson.feature(cachedTopoData.germany, cachedTopoData.germany.objects.data)

    ukGeojson.features.forEach(f => {
      f.properties.areaSqKm = turf.area(f) / 1000000
      countryAreas.uk += f.properties.areaSqKm
    })
    frGeojson.features.forEach(f => {
      f.properties.areaSqKm = turf.area(f) / 1000000
      countryAreas.france += f.properties.areaSqKm
    })
    deGeojson.features.forEach(f => {
      f.properties.areaSqKm = turf.area(f) / 1000000
      countryAreas.germany += f.properties.areaSqKm
    })

    // Tag and enrich UK features
    ukGeojson.features.forEach(feature => {
      const customId = `uk-${feature.properties.ID}`
      feature.id = customId
      countryFeatureIds.uk.push(customId)
      feature.properties.customId = customId
      feature.properties.country = 'uk'
      feature.properties.unavailable = ukUnavailable
      
      const macroGen = solarData.uk ? solarData.uk.totalGen : 0
      const microGen = solarData.uk && solarData.uk[feature.properties.ID] !== undefined ? solarData.uk[feature.properties.ID] : 0
      
      feature.properties.macroGeneration = macroGen
      feature.properties.microGeneration = microGen
      feature.properties.macroNormalized = countryAreas.uk > 0 ? (macroGen / countryAreas.uk) : 0
      feature.properties.microNormalized = feature.properties.areaSqKm > 0 ? (microGen / feature.properties.areaSqKm) : 0
      
      feature.properties.displayName = feature.properties.Area
      feature.properties.displaySub = feature.properties.DNO_Full
      feature.properties.displayId = feature.properties.ID
    })

    // Tag and enrich FR features
    frGeojson.features.forEach(feature => {
      const customId = `fr-${feature.properties.code}`
      feature.id = customId
      countryFeatureIds.france.push(customId)
      feature.properties.customId = customId
      feature.properties.country = 'france'
      feature.properties.unavailable = frUnavailable
      
      const macroGen = solarData.france ? solarData.france.totalGen : 0
      const microGen = solarData.france && solarData.france[feature.properties.code] !== undefined ? solarData.france[feature.properties.code] : 0
      
      feature.properties.macroGeneration = macroGen
      feature.properties.microGeneration = microGen
      feature.properties.macroNormalized = countryAreas.france > 0 ? (macroGen / countryAreas.france) : 0
      feature.properties.microNormalized = feature.properties.areaSqKm > 0 ? (microGen / feature.properties.areaSqKm) : 0
      
      feature.properties.displayName = feature.properties.nom
      feature.properties.displaySub = 'France Region'
      feature.properties.displayId = feature.properties.code
    })

    // Tag and enrich DE features
    deGeojson.features.forEach(feature => {
      const customId = `de-${feature.properties.id || feature.properties.name}`
      feature.id = customId
      countryFeatureIds.germany.push(customId)
      feature.properties.customId = customId
      feature.properties.country = 'germany'
      feature.properties.unavailable = deUnavailable
      
      const macroGen = solarData.germany ? solarData.germany.totalGen : 0
      
      feature.properties.macroGeneration = macroGen
      feature.properties.microGeneration = 0 // Regional unavailable
      feature.properties.macroNormalized = countryAreas.germany > 0 ? (macroGen / countryAreas.germany) : 0
      feature.properties.microNormalized = 0
      
      feature.properties.displayName = feature.properties.name
      feature.properties.displaySub = 'Germany (State)'
      feature.properties.displayId = feature.properties.id || 'DE'
    })

    const geojsonData = {
      type: 'FeatureCollection',
      features: [...ukGeojson.features, ...frGeojson.features, ...deGeojson.features]
    }

    // 4. Generate Country Outlines using TopoJSON merge + hole removal
    // This perfectly removes "rogue" internal lines caused by unshared arcs.
    function getSolidOutline(topology, object) {
      const merged = topojson.merge(topology, object.geometries)
      if (merged.type === 'Polygon') {
        merged.coordinates = [merged.coordinates[0]] // keep only exterior ring
      } else if (merged.type === 'MultiPolygon') {
        merged.coordinates = merged.coordinates.map(poly => [poly[0]]) // keep only exterior rings
      }
      return merged
    }

    const ukOutline = getSolidOutline(cachedTopoData.uk, cachedTopoData.uk.objects.data)
    const frOutline = getSolidOutline(cachedTopoData.france, cachedTopoData.france.objects.data)
    const deOutline = getSolidOutline(cachedTopoData.germany, cachedTopoData.germany.objects.data)

    const getMacroGen = (countryKey) => solarData[countryKey] ? solarData[countryKey].totalGen : 0
    const getMacroNorm = (countryKey) => countryAreas[countryKey] > 0 ? (getMacroGen(countryKey) / countryAreas[countryKey]) : 0

    const outlineGeojsonData = {
      type: 'FeatureCollection',
      features: [
        { type: 'Feature', id: 'uk', properties: { country: 'uk', macroGeneration: getMacroGen('uk'), macroNormalized: getMacroNorm('uk') }, geometry: ukOutline },
        { type: 'Feature', id: 'france', properties: { country: 'france', macroGeneration: getMacroGen('france'), macroNormalized: getMacroNorm('france') }, geometry: frOutline },
        { type: 'Feature', id: 'germany', properties: { country: 'germany', macroGeneration: getMacroGen('germany'), macroNormalized: getMacroNorm('germany') }, geometry: deOutline }
      ]
    }

    document.getElementById('status-text').textContent = 'Live / Connected'
    setStatusDot('connected')

    // Update existing source or add new one
    const existingSource = mapInstance.getSource('pes-regions-source')
    if (existingSource) {
      existingSource.setData(geojsonData)
      mapInstance.getSource('pes-countries-source').setData(outlineGeojsonData)
    } else {
      addMapLayers(geojsonData, outlineGeojsonData)
    }

    // Register event listeners exactly once, after layers exist
    if (!eventsRegistered) {
      registerMapEvents()
      eventsRegistered = true
    }

    updateStatsPanel()
    // Re-apply highlight if a country was already selected
    updateMapStyles()

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
  } else if (selectedCountry === 'germany') {
    titleEl.textContent = 'Total Germany Output'
    if (!currentSolarData.germany) {
      valEl.textContent = 'Unavailable'
    } else {
      valEl.textContent = currentSolarData.germany.totalGen !== undefined ? currentSolarData.germany.totalGen : '0'
    }
  }
}



function addMapLayers (geojsonData, outlineGeojsonData) {
  // Add map source for regions
  mapInstance.addSource('pes-regions-source', {
    type: 'geojson',
    data: geojsonData,
    promoteId: 'customId'
  })

  // Add map source for country outlines
  mapInstance.addSource('pes-countries-source', {
    type: 'geojson',
    data: outlineGeojsonData,
    promoteId: 'country' // Explicitly promote country to ID for feature-state
  })

  // Map background colour
  mapInstance.addLayer({
    id: 'pes-regions-fill',
    type: 'fill',
    source: 'pes-regions-source',
    paint: {
      'fill-color': '#1e293b', // fallback
      'fill-opacity': 0.8
    }
  })

  // Add region borders
  mapInstance.addLayer({
    id: 'pes-regions-borders',
    type: 'line',
    source: 'pes-regions-source',
    paint: {
      'line-color': '#94a3b8',
      'line-width': 0.5,
      'line-opacity': 0 // default hidden
    }
  })

  // Add country outline borders
  mapInstance.addLayer({
    id: 'pes-countries-borders',
    type: 'line',
    source: 'pes-countries-source',
    paint: {
      'line-color': '#ffffff', // Placeholder, updated dynamically
      'line-width': 2.5,
      'line-opacity': [
        'case',
        ['boolean', ['feature-state', 'hover'], false], 1.0,
        0.0 // hidden by default
      ]
    }
  })

  updateMapStyles()
}

function updateMapStyles () {
  if (!mapInstance || !mapInstance.getLayer('pes-regions-fill')) return

  const selCountry = selectedCountry || 'none'
  const isMicro = ['all', ['==', ['get', 'country'], selCountry], ['!=', ['get', 'country'], 'germany']]

  // Shared matte solar colors (9-step scale)
  const c0 = '#1e293b' // Zero (Base Slate)
  const c1 = '#7a6021' // Very Low (Dark Amber)
  const c2 = '#9e7924' // Low (Amber)
  const c3 = '#c49323' // Med-Low (Light Amber)
  const c4 = '#d18b24' // Medium (Orange-Amber)
  const c5 = '#d16a24' // Med-High (Orange)
  const c6 = '#c24b1d' // High (Burnt Orange)
  const c7 = '#a62d17' // Very High (Red)
  const c8 = '#7a1811' // Max (Dark Red)

  let macroColorExp, microColorExp
  
  const isMicroMode = (selCountry !== 'none' && selCountry !== 'germany')

  if (isNormalized) {
    // Normalized (MW/km²)
    const normStops = [0, c0, 0.005, c1, 0.015, c2, 0.03, c3, 0.06, c4, 0.1, c5, 0.2, c6, 0.35, c7, 0.5, c8]
    macroColorExp = ['interpolate', ['linear'], ['get', 'macroNormalized'], ...normStops]
    microColorExp = ['interpolate', ['linear'], ['get', 'microNormalized'], ...normStops]
    
    // Update Legend UI
    document.getElementById('solar-legend-title').textContent = 'Solar Density (MW/km²)'
    document.getElementById('solar-legend-scale').innerHTML = `
        <div class="legend-item"><div class="legend-color" style="background-color: ${c8};"></div><span>> 0.50</span></div>
        <div class="legend-item"><div class="legend-color" style="background-color: ${c6};"></div><span>~ 0.20</span></div>
        <div class="legend-item"><div class="legend-color" style="background-color: ${c4};"></div><span>~ 0.06</span></div>
        <div class="legend-item"><div class="legend-color" style="background-color: ${c2};"></div><span>~ 0.01</span></div>
        <div class="legend-item"><div class="legend-color" style="background-color: ${c0};"></div><span>0 / Offline</span></div>
    `
  } else {
    // Absolute MW
    const macroStops = [0, c0, 250, c1, 1000, c2, 2500, c3, 5000, c4, 10000, c5, 20000, c6, 40000, c7, 60000, c8]
    const microStops = [0, c0, 25, c1, 100, c2, 250, c3, 500, c4, 1000, c5, 2000, c6, 3500, c7, 5000, c8]
    macroColorExp = ['interpolate', ['linear'], ['get', 'macroGeneration'], ...macroStops]
    microColorExp = ['interpolate', ['linear'], ['get', 'microGeneration'], ...microStops]
    
    document.getElementById('solar-legend-title').textContent = isMicroMode ? 'Regional Output (MW)' : 'National Output (MW)'
    
    if (isMicroMode) {
      document.getElementById('solar-legend-scale').innerHTML = `
          <div class="legend-item"><div class="legend-color" style="background-color: ${c8};"></div><span>> 5,000</span></div>
          <div class="legend-item"><div class="legend-color" style="background-color: ${c6};"></div><span>~ 2,000</span></div>
          <div class="legend-item"><div class="legend-color" style="background-color: ${c4};"></div><span>~ 500</span></div>
          <div class="legend-item"><div class="legend-color" style="background-color: ${c2};"></div><span>~ 100</span></div>
          <div class="legend-item"><div class="legend-color" style="background-color: ${c0};"></div><span>0 / Offline</span></div>
      `
    } else {
      document.getElementById('solar-legend-scale').innerHTML = `
          <div class="legend-item"><div class="legend-color" style="background-color: ${c8};"></div><span>> 60,000</span></div>
          <div class="legend-item"><div class="legend-color" style="background-color: ${c6};"></div><span>~ 20,000</span></div>
          <div class="legend-item"><div class="legend-color" style="background-color: ${c4};"></div><span>~ 5,000</span></div>
          <div class="legend-item"><div class="legend-color" style="background-color: ${c2};"></div><span>~ 1,000</span></div>
          <div class="legend-item"><div class="legend-color" style="background-color: ${c0};"></div><span>0 / Offline</span></div>
      `
    }
  }

  mapInstance.setPaintProperty('pes-regions-fill', 'fill-color', [
    'case',
    isMicro, microColorExp,
    macroColorExp
  ])

  // Borders: Show for selected micro regions (not Germany), OR when hovering in macro mode
  mapInstance.setPaintProperty('pes-regions-borders', 'line-opacity', [
    'case',
    isMicro, 1.0,
    ['boolean', ['feature-state', 'hover'], false], 0.6, // Soft borders on hover
    0.0
  ])

  // Outline Borders: Color matched to the fill color via macroColorExp
  if (mapInstance.getLayer('pes-countries-borders')) {
    mapInstance.setPaintProperty('pes-countries-borders', 'line-color', macroColorExp)
  }
  
  // Opacity: Highlight selected country, or show all if none selected
  mapInstance.setPaintProperty('pes-regions-fill', 'fill-opacity', [
    'case',
    ['==', selCountry, 'none'],
    ['case', ['boolean', ['feature-state', 'hover'], false], 0.55, 0.45], // Subtle fill highlight
    ['==', ['get', 'country'], selCountry],
    ['case', ['boolean', ['feature-state', 'hover'], false], 0.55, 0.45],
    0.1 // Fade out others heavily
  ])
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

      // Tooltip logic
      const regionName = currentFeature.properties.displayName
      const subName = currentFeature.properties.displaySub
      const displayId = currentFeature.properties.displayId
      const isUnavailable = currentFeature.properties.unavailable
      const country = currentFeature.properties.country
      
      const isMicro = (selectedCountry === country && country !== 'germany')
      
      // Clear previous hover
      if (hoveredState) {
        if (hoveredState.type === 'macro') {
          // Clear regions
          countryFeatureIds[hoveredState.country].forEach(id => {
            mapInstance.setFeatureState({ source: 'pes-regions-source', id }, { hover: false })
          })
          // Clear country outline
          mapInstance.setFeatureState({ source: 'pes-countries-source', id: hoveredState.country }, { hover: false })
        } else {
          mapInstance.setFeatureState({ source: 'pes-regions-source', id: hoveredState.id }, { hover: false })
        }
      }

      const currentRegionId = currentFeature.properties.customId || currentFeature.id

      // Set new hover
      if (!isMicro) {
        // Macro hover: Highlight the whole country fill
        countryFeatureIds[country].forEach(id => {
          mapInstance.setFeatureState({ source: 'pes-regions-source', id }, { hover: true })
        })
        // Highlight the country outline
        mapInstance.setFeatureState({ source: 'pes-countries-source', id: country }, { hover: true })
        hoveredState = { type: 'macro', country }
      } else {
        // Micro hover: Highlight just the region fill
        mapInstance.setFeatureState({ source: 'pes-regions-source', id: currentRegionId }, { hover: true })
        hoveredState = { type: 'micro', id: currentRegionId }
      }
      
      const generationMw = isMicro ? currentFeature.properties.microGeneration : currentFeature.properties.macroGeneration
      const normalizedValue = isMicro ? currentFeature.properties.microNormalized : currentFeature.properties.macroNormalized
      
      let displayRegionData, displayNormalizedData
      if (isUnavailable) {
        displayRegionData = 'Data Unavailable'
        displayNormalizedData = '--'
      } else if (generationMw !== undefined && generationMw !== null) {
        displayRegionData = `${Number(generationMw).toFixed(1)} MW`
        displayNormalizedData = `${Number(normalizedValue).toFixed(4)} MW/km²`
      } else {
        displayRegionData = '0 MW (Offline)'
        displayNormalizedData = '0 MW/km²'
      }

      let outputLabel = ''
      if (country === 'germany') {
          outputLabel = 'National Output (Regional N/A):'
      } else if (isMicro) {
          outputLabel = 'Regional Output:'
      } else {
          outputLabel = 'National Output:'
      }

      const DATA_SOURCES = {
        'uk': 'Sheffield Solar (PV_Live)',
        'france': 'RTE (éCO2mix)',
        'germany': 'Fraunhofer ISE (Energy-Charts)'
      }
      const sourceLabel = DATA_SOURCES[country] || 'Unknown'

      let displayTitle = country.toUpperCase()
      if (country === 'uk') displayTitle = 'GREAT BRITAIN'
      else if (country === 'france') displayTitle = 'FRANCE'
      else if (country === 'germany') displayTitle = 'GERMANY'

      popup
        .setLngLat(e.lngLat)
        .setHTML(
          `
                    <div style="min-width: 250px;">
                        <h3 style="margin:0; color:var(--accent); font-size:1.125rem;">${escapeHtml(isMicro ? regionName : displayTitle)}</h3>
                        <p style="margin:4px 0 0 0; color:var(--text-muted); font-size:0.75rem;">${escapeHtml(isMicro ? subName : 'National')}</p>
                        ${isMicro ? `<p style="margin:0; color:var(--text-muted); font-size:0.75rem; opacity: 0.8;">ID: ${escapeHtml(String(displayId))}</p>` : ''}
                        <hr style="border-color:var(--border-color); margin:8px 0;">
                        <p style="margin:0; color:var(--text-muted); font-size:0.875rem;">${outputLabel}</p>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 6px;">
                            <div>
                                <p style="margin:0; color:var(--text-muted); font-size:0.75rem;">Absolute</p>
                                <p style="margin:0; color:var(--text-main); font-size:1.125rem; font-weight:bold; white-space:nowrap;">${escapeHtml(displayRegionData)}</p>
                            </div>
                            <div>
                                <p style="margin:0; color:var(--text-muted); font-size:0.75rem;">Density</p>
                                <p style="margin:0; color:var(--text-main); font-size:1.125rem; font-weight:bold; white-space:nowrap;">${escapeHtml(displayNormalizedData)}</p>
                            </div>
                        </div>
                        <hr style="border-color:var(--border-color); margin:8px 0;">
                        <p style="margin:0; color:var(--text-muted); font-size:0.75rem; text-align: left; opacity: 0.8;">Source: ${escapeHtml(sourceLabel)}</p>
                    </div>
                `
        )
        .addTo(mapInstance)
    }
  })

  // When mouse leaves regions entirely
  mapInstance.on('mouseleave', 'pes-regions-fill', () => {
    if (hoveredState) {
      if (hoveredState.type === 'macro') {
        countryFeatureIds[hoveredState.country].forEach(id => {
          mapInstance.setFeatureState({ source: 'pes-regions-source', id }, { hover: false })
        })
        mapInstance.setFeatureState({ source: 'pes-countries-source', id: hoveredState.country }, { hover: false })
      } else {
        mapInstance.setFeatureState({ source: 'pes-regions-source', id: hoveredState.id }, { hover: false })
      }
    }
    hoveredState = null
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
      updateMapStyles()

      if (selectedCountry === 'uk') {
        mapInstance.flyTo(MAP_VIEWS.UK)
      } else if (selectedCountry === 'france') {
        mapInstance.flyTo(MAP_VIEWS.FRANCE)
      } else if (selectedCountry === 'germany') {
        mapInstance.flyTo(MAP_VIEWS.GERMANY)
      }
    }
  })

  // Click outside to deselect
  mapInstance.on('click', e => {
    const features = mapInstance.queryRenderedFeatures(e.point, { layers: ['pes-regions-fill'] })
    if (features.length === 0) {
      selectedCountry = null
      updateStatsPanel()
      updateMapStyles()
    }
  })

  // Hook up stats panel click to deselect too
  document.getElementById('solar-stats').addEventListener('click', (e) => {
    e.stopPropagation()
    selectedCountry = null
    updateStatsPanel()
    updateMapStyles()
    mapInstance.flyTo(MAP_VIEWS.DEFAULT)
  })

  // Toggle listener
  const toggle = document.getElementById('normalize-toggle')
  if (toggle) {
    toggle.addEventListener('change', (e) => {
      isNormalized = e.target.checked
      updateMapStyles()
    })
  }
  // Reset button listener
  const resetBtn = document.getElementById('solar-map-reset')
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      selectedCountry = null
      updateStatsPanel()
      updateMapStyles()
      mapInstance.flyTo({
        center: MAP_VIEWS.DEFAULT.center,
        zoom: MAP_VIEWS.DEFAULT.zoom,
        pitch: 20,
        bearing: 0
      })
    })
  }
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
    center: MAP_VIEWS.DEFAULT.center,
    zoom: MAP_VIEWS.DEFAULT.zoom,
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
