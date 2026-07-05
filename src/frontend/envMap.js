let envMapInstance = null;

export async function initEnvMap() {
    if (envMapInstance) {
        // Mapbox requires resize if it was initialized while hidden
        setTimeout(() => envMapInstance.resize(), 100);
        return;
    }

    try {
        const config_response = await fetch('http://127.0.0.1:8000/api/config');
        const config = await config_response.json();
        mapboxgl.accessToken = config.mapboxToken;

        // Initialize map
        envMapInstance = new mapboxgl.Map({
            container: 'env-map',
            style: 'mapbox://styles/mapbox/dark-v11', // Dark map looks good with bright data points
            center: [-2.5, 54.5],
            zoom: 5.5,
            pitch: 0
        });

        // Tooltip object
        const popup = new mapboxgl.Popup({
            closeButton: false,
            closeOnClick: false,
            className: 'custom-popup'
        });

        envMapInstance.on('load', async () => {
            document.getElementById('env-status-text').innerText = "Fetching live river data...";

            // Highlight the built-in waterway layer
            if (envMapInstance.getLayer('waterway')) {
                envMapInstance.setPaintProperty('waterway', 'line-color', '#3b82f6'); // blue-500
                envMapInstance.setPaintProperty('waterway', 'line-width', [
                    'interpolate', ['linear'], ['zoom'],
                    4, 1.5,
                    10, 3.5
                ]);
                envMapInstance.setPaintProperty('waterway', 'line-opacity', 1.0);
            } else {
                // Some styles might have different waterway layer names, or we can just add a simple filter if needed
                console.log("Built-in waterway layer not found or named differently.");
            }

            // Fetch Environment Agency Data
            const ea_response = await fetch('http://127.0.0.1:8000/api/environment/river_levels');
            const ea_data = await ea_response.json();

            document.getElementById('env-status-text').innerText = `Live / Connected (${ea_data.data.length} stations)`;
            document.getElementById('env-status-dot').classList.replace('pulse', 'connected');

            // Convert EA data to GeoJSON
            const geojsonFeatures = ea_data.data.map(station => {
                // Calculate status: 'low', 'normal', 'high'
                let status = 1; // 0 = low, 1 = normal, 2 = high
                if (station.value > station.typicalRangeHigh) {
                    status = 2; // High
                } else if (station.value < station.typicalRangeLow) {
                    status = 0; // Low
                }

                return {
                    type: "Feature",
                    geometry: {
                        type: "Point",
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
                };
            });

            const stationsGeoJSON = {
                type: "FeatureCollection",
                features: geojsonFeatures
            };

            // Add source
            envMapInstance.addSource('ea-stations', {
                type: 'geojson',
                data: stationsGeoJSON
            });

            // Add circle layer
            envMapInstance.addLayer({
                id: 'ea-stations-layer',
                type: 'circle',
                source: 'ea-stations',
                paint: {
                    'circle-radius': [
                        'interpolate', ['linear'], ['zoom'],
                        5, 3,
                        10, 6
                    ],
                    'circle-color': [
                        'match',
                        ['get', 'status'],
                        0, '#fcd34d', // Low (Amber)
                        1, '#10b981', // Normal (Emerald)
                        2, '#ef4444', // High (Red)
                        '#94a3b8'     // Default (Slate)
                    ],
                    'circle-opacity': 0.8,
                    'circle-stroke-width': 1,
                    'circle-stroke-color': '#0f172a'
                }
            });

            // Hover interactions
            envMapInstance.on('mousemove', 'ea-stations-layer', (e) => {
                envMapInstance.getCanvas().style.cursor = 'pointer';
                if (e.features.length > 0) {
                    const feature = e.features[0];
                    const props = feature.properties;
                    
                    let statusText = "Normal";
                    let statusColor = "var(--success)";
                    if (props.status === 2) {
                        statusText = "High";
                        statusColor = "var(--danger)";
                    } else if (props.status === 0) {
                        statusText = "Low";
                        statusColor = "var(--accent)";
                    }

                    popup.setLngLat(feature.geometry.coordinates)
                        .setHTML(`
                        <div>
                            <h3 style="margin:0; color:var(--text-main); font-size:1rem;">${props.name}</h3>
                            <p style="margin:2px 0 8px 0; color:var(--text-muted); font-size:0.75rem;">${props.river || 'Unknown River'}</p>
                            
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span style="color:var(--text-muted); font-size:0.875rem;">Status:</span>
                                <span style="color:${statusColor}; font-weight:bold; font-size:0.875rem;">${statusText}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span style="color:var(--text-muted); font-size:0.875rem;">Current Level:</span>
                                <span style="color:var(--text-main); font-size:0.875rem;">${props.value.toFixed(2)} m</span>
                            </div>
                            <div style="display:flex; justify-content:space-between;">
                                <span style="color:var(--text-muted); font-size:0.875rem;">Typical Range:</span>
                                <span style="color:var(--text-muted); font-size:0.875rem;">${props.low.toFixed(2)} - ${props.high.toFixed(2)} m</span>
                            </div>
                        </div>
                    `)
                        .addTo(envMapInstance);
                }
            });

            envMapInstance.on('mouseleave', 'ea-stations-layer', () => {
                envMapInstance.getCanvas().style.cursor = '';
                popup.remove();
            });
        });

    } catch (error) {
        console.error("Initialisation failed:", error);
        document.getElementById('env-status-text').innerText = "Connection Failed";
        document.getElementById('env-status-dot').classList.replace('pulse', 'error');
    }
}
