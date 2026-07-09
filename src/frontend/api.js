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
        return await response.json()
    } catch (e) {
        console.error('Network error fetching from backend:', e)
        return null
    }
}


export async function fetchGenerationSummary() {
    return fetchWithCheck(`${API_BASE_URL}/generation/summary`)
}

export async function fetchSolarData() {
    return fetchWithCheck(`${API_BASE_URL}/solar/solar`)
}

export async function fetchRiverLevels() {
    return fetchWithCheck(`${API_BASE_URL}/environment/river_levels`)
}

export async function fetchMapRegions() {
    return fetchWithCheck(`${BACKEND_URL}/static/gb-dno-license-areas-2024_wgs84.topojson`)
}
