async function initialise_app() {
    try {
        const config_response = await fetch('http://127.0.0.1:8000/api/config');
        const config = await config_response.json();
        mapboxgl.accessToken = config.mapboxToken;

        // Map configuration
        const map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/dark-v11',
            center: [-2.5, 54.5],
            zoom: 5
        });

        // Tooltip object
        const popup = new mapboxgl.Popup({
            closeButton: false,
            closeOnClick: false,
            className: 'custom-popup'
        });

        let hovered_polygon_id = null;

        map.on('load', async () => {
            const regions_response = await fetch('http://127.0.0.1:8000/api/regions');
            const geojsonData = await regions_response.json();

            const solar_response = await fetch('http://127.0.0.1:8000/api/solar');
            const solar_data = await solar_response.json();

            geojsonData.features.forEach(feature => {
                feature.id = feature.properties.ID;
                const mw_value = solar_data[feature.id];
                feature.properties.generation = (mw_value !== undefined && mw_value !== null) ? mw_value : 0;
            });

            // Add map source
            map.addSource('pes-regions-source', { 
                type: 'geojson', 
                data: geojsonData 
            });

            // Map background colour
            map.addLayer({
                id: 'pes-regions-fill',
                type: 'fill',
                source: 'pes-regions-source',
                paint: {
                    'fill-color': [
                        'interpolate',
                        ['linear'],
                        ['get', 'generation'],
                        0,   '#1e272c',
                        50,
                            '#f1c40f',
                        200,
                            '#e67e22',
                        500,
                            '#e74c3c'
                    ],
                    'fill-opacity': [
                        'case',
                        ['boolean', ['feature-state', 'hover'], false],
                        0.7, // opacity when hovered
                        0.3  // opacity when not hovered
                    ]
                }
            });

            // Add region borders
            map.addLayer({
                id: 'pes-regions-borders',
                type: 'line',
                source: 'pes-regions-source',
                paint: {
                    'line-color': '#ffffff',
                    'line-width': [
                        'case',
                        ['boolean', ['feature-state', 'hover'], false],
                        3,  // Thick border on hover
                        0.5 // Thin border otherwise
                    ]
                }
            });

            // Mouse events
            map.on('mousemove', 'pes-regions-fill', (e) => {
                if (e.features.length > 0) {
                    const current_feature = e.features[0];

                    if (hovered_polygon_id != null) {
                        map.setFeatureState(
                            { source: 'pes-regions-source', id: hovered_polygon_id },
                            { hover: false }
                        );
                    }
                hovered_polygon_id = current_feature.id;
                map.setFeatureState(
                    { source: 'pes-regions-source', id: hovered_polygon_id },
                    { hover: true }
                );

                // Tooltip logic
                const region_name = current_feature.properties.Area;
                const dnoName = current_feature.properties.DNO_Full;

                const generation_mw = solar_data[current_feature.id];
                const total_generation_mw = solar_data["total_gen"]
                const display_total_data = (total_generation_mw !== undefined && total_generation_mw !== null)
                                           ? `${total_generation_mw} MW` 
                                           : "0 MW (Night/Offline)";
                const display_region_data = (generation_mw !== undefined && generation_mw !== null)
                                             ? `${generation_mw} MW` 
                                             : "0 MW (Night/Offline)";

                popup.setLngLat(e.lngLat)
                    .setHTML(`
                        <div style="font-family: sans-serif; padding: 5px;">
                            <h3 style="margin: 0 0 5px 0;">${region_name}</h3>
                            <p style="margin: 0; font-size: 12px; color: #666;">${dnoName}</p>
                            <p style="margin: 0; font-size: 12px; color: #666;">PES ID: <span style="color: #666;">${current_feature.id}</span></p>
                            <hr style="border: 0; border-top: 1px solid #ccc; margin: 8px 0;">
                            <p style="margin: 0;">Total GB Solar Output: <span style="color: #e67e22;">${display_total_data}</span></p>
                            <p style="margin: 0; font-weight: bold;">Region Solar Output: <span style="color: #e67e22;">${display_region_data}</span></p>
                        </div>
                    `)
                    .addTo(map);
                }
            });

            // When mouse leaves regions entirely
            map.on('mouseleave', 'pes-regions-fill', () => {
                if (hovered_polygon_id !== null) {
                    map.setFeatureState(
                        { source: 'pes-regions-source', id: hovered_polygon_id },
                        { hover: false }
                    );
                }
                hovered_polygon_id = null;
            
                popup.remove();
            });
        });

    } catch (error) {
        console.error("Initialisation failed:", error);
    }
}

initialise_app();