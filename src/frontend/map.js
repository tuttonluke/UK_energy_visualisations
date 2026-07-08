let mapInstance = null

export async function initMap () {
  if (mapInstance) return

  try {
    const config_response = await fetch('http://127.0.0.1:8000/api/config')
    const config = await config_response.json()
    mapboxgl.accessToken = config.mapboxToken

    // Map configuration
    mapInstance = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [-2.5, 54.5],
      zoom: 5.5,
      pitch: 20
    })

    // Tooltip object
    const popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: 'custom-popup'
    })

    let hovered_polygon_id = null

    mapInstance.on('load', async () => {
      document.getElementById('status-text').innerText = 'Fetching live data...'

      const regions_response = await fetch('http://127.0.0.1:8000/api/regions')
      const geojsonData = await regions_response.json()

      const solar_response = await fetch(
        'http://127.0.0.1:8000/api/solar/solar'
      )
      const solar_data = await solar_response.json()

      // Update UI Total
      const totalGen = solar_data['total_gen']
      document.getElementById('total-gen-display').innerText =
        totalGen !== undefined ? totalGen : '0'
      document.getElementById('status-text').innerText = 'Live / Connected'
      document
        .getElementById('status-dot')
        .classList.replace('pulse', 'connected')

      // Map properties
      geojsonData.features.forEach(feature => {
        feature.id = feature.properties.ID
        const mw_value = solar_data[feature.id]
        feature.properties.generation =
          mw_value !== undefined && mw_value !== null ? mw_value : 0
      })

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

      // Mouse events
      mapInstance.on('mousemove', 'pes-regions-fill', e => {
        if (e.features.length > 0) {
          const current_feature = e.features[0]

          if (hovered_polygon_id != null) {
            mapInstance.setFeatureState(
              { source: 'pes-regions-source', id: hovered_polygon_id },
              { hover: false }
            )
          }
          hovered_polygon_id = current_feature.id
          mapInstance.setFeatureState(
            { source: 'pes-regions-source', id: hovered_polygon_id },
            { hover: true }
          )

          // Tooltip logic
          const region_name = current_feature.properties.Area
          const dnoName = current_feature.properties.DNO_Full
          const generation_mw = solar_data[current_feature.id]

          const display_region_data =
            generation_mw !== undefined && generation_mw !== null
              ? `${generation_mw} MW`
              : '0 MW (Offline)'

          popup
            .setLngLat(e.lngLat)
            .setHTML(
              `
                        <div>
                            <h3 style="margin:0; color:var(--accent); font-size:1.125rem;">${region_name}</h3>
                            <p style="margin:4px 0 0 0; color:var(--text-muted); font-size:0.75rem;">${dnoName}</p>
                            <p style="margin:0; color:var(--text-muted); font-size:0.75rem; opacity: 0.8;">PES ID: ${current_feature.id}</p>
                            <hr style="border-color:var(--border-color); margin:8px 0;">
                            <p style="margin:0; color:var(--text-muted); font-size:0.875rem;">Region Output:</p>
                            <p style="margin:0; color:var(--text-main); font-size:1.25rem; font-weight:bold;">${display_region_data}</p>
                        </div>
                    `
            )
            .addTo(mapInstance)
        }
      })

      // When mouse leaves regions entirely
      mapInstance.on('mouseleave', 'pes-regions-fill', () => {
        if (hovered_polygon_id !== null) {
          mapInstance.setFeatureState(
            { source: 'pes-regions-source', id: hovered_polygon_id },
            { hover: false }
          )
        }
        hovered_polygon_id = null
        mapInstance.getCanvas().style.cursor = ''
        popup.remove()
      })

      // Change cursor on hover
      mapInstance.on('mouseenter', 'pes-regions-fill', () => {
        mapInstance.getCanvas().style.cursor = 'pointer'
      })
    })
  } catch (error) {
    console.error('Initialisation failed:', error)
    document.getElementById('status-text').innerText = 'Connection Failed'
    document.getElementById('status-dot').classList.replace('pulse', 'error')
  }
}
