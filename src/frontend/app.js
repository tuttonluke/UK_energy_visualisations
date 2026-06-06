async function initialise_app() {
    try {
        const config_response = await fetch('http://127.0.0.1:8000/api/config');
        const config = await config_response.json();
        
        mapboxgl.accessToken = config.mapboxToken;

        const map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/dark-v11',
            center: [-2.5, 54.5],
            zoom: 5
        });

        map.on('load', async () => {
            const regionsResponse = await fetch('http://127.0.0.1:8000/api/regions');
            const geojsonData = await regionsResponse.json();

            map.addSource('pes-regions-source', { type: 'geojson', data: geojsonData });
            map.addLayer({
                id: 'pes-regions-layer',
                type: 'fill',
                source: 'pes-regions-source',
                paint: {
                    'fill-color': '#3498db',
                    'fill-opacity': 0.5,
                    'fill-outline-color': '#ffffff'
                }
            });
        });

    } catch (error) {
        console.error("Initialisation failed:", error);
    }
}

initialise_app();