// Automatically route to 8000 if running on a dev server, otherwise use current origin
export const BACKEND_URL = ['5500', '3000', '5173'].includes(window.location.port)
    ? 'http://127.0.0.1:8000' 
    : window.location.origin

const API_BASE_URL = `${BACKEND_URL}/api`

async function fetchWithCheck(url) {
    try {
        const response = await fetch(url)
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`)
            return null
        }
        const data = await response.json()
        if (data && data.error) {
            console.error(`API error: ${data.error}`)
            return null
        }
        return data
    } catch (e) {
        console.error('Network error fetching from backend:', e)
        return null
    }
}


export async function fetchGenerationSummary() {
    return fetchWithCheck(`${API_BASE_URL}/generation/summary`)
}

export async function fetchSolarData() {
    const [uk, france, energy_charts, denmark, belgium] = await Promise.all([
        fetchWithCheck(`${API_BASE_URL}/solar/solar`),
        fetchWithCheck(`${API_BASE_URL}/solar/solar/france`),
        fetchWithCheck(`${API_BASE_URL}/solar/solar/energy_charts`),
        fetchWithCheck(`${API_BASE_URL}/solar/solar/denmark`),
        fetchWithCheck(`${API_BASE_URL}/solar/solar/belgium`)
    ])
    
    // Flatten energy_charts into the returned object, mapping short codes to full names
    const mappedEnergyCharts = energy_charts ? {
        germany: energy_charts.de,
        netherlands: energy_charts.nl,
        austria: energy_charts.at,
        switzerland: energy_charts.ch,
        poland: energy_charts.pl,
        czechia: energy_charts.cz,
        spain: energy_charts.es,
        portugal: energy_charts.pt
    } : {}

    return { 
        uk, 
        france, 
        denmark,
        belgium,
        ...mappedEnergyCharts
    }
}

export async function fetchRiverLevels() {
    return fetchWithCheck(`${API_BASE_URL}/environment/river_levels`)
}

// Cache buster for static TopoJSON files
const STATIC_VERSION = '2024.4'

export async function fetchMapRegions() {
    const [uk, france, spain, netherlands, austria, switzerland, poland, czechia, germany, denmark, belgium, portugal] = await Promise.all([
        fetchWithCheck(`${BACKEND_URL}/static/gb-dno-license-areas-2024_wgs84.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/france-regions.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/spain-regions.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/netherlands.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/austria.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/switzerland.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/poland.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/czechia.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/germany.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/denmark-regions.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/belgium-regions.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/portugal.topojson?v=${STATIC_VERSION}`)
    ])
    return { uk, france, spain, netherlands, austria, switzerland, poland, czechia, germany, denmark, belgium, portugal }
}
