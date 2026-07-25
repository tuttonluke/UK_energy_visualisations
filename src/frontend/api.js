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
    const [uk, france, germany] = await Promise.all([
        fetchWithCheck(`${API_BASE_URL}/solar/solar`),
        fetchWithCheck(`${API_BASE_URL}/solar/solar/france`),
        fetchWithCheck(`${API_BASE_URL}/solar/solar/germany`)
    ])
    return { uk, france, germany }
}

export async function fetchRiverLevels() {
    return fetchWithCheck(`${API_BASE_URL}/environment/river_levels`)
}

// Bump this version only when the static TopoJSON boundary files change
const STATIC_VERSION = '2024.1'

export async function fetchMapRegions() {
    const [uk, france, germany] = await Promise.all([
        fetchWithCheck(`${BACKEND_URL}/static/gb-dno-license-areas-2024_wgs84.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/france-regions.topojson?v=${STATIC_VERSION}`),
        fetchWithCheck(`${BACKEND_URL}/static/germany.topojson?v=${STATIC_VERSION}`)
    ])
    return { uk, france, germany }
}
