// Automatically route to 8000 if running on a dev server, otherwise use current origin.
// Override with VITE_BACKEND_URL env var for custom deployments.
export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL
  || (['5500', '3000', '5173'].includes(window.location.port)
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

const API_BASE_URL = `${BACKEND_URL}/api`

// ---------------------------------------------------------------------------
// Fetch with timeout, retry, and error handling
// ---------------------------------------------------------------------------

const FETCH_TIMEOUT_MS = 15_000
const MAX_RETRIES = 2
const RETRY_BASE_DELAY_MS = 1_000

function delay (ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Fetch JSON from the given URL with automatic timeout, retry, and
 * error handling.
 *
 * - Times out after FETCH_TIMEOUT_MS (15 s) per attempt.
 * - Retries up to MAX_RETRIES times on network errors, timeouts,
 *   and 5xx server errors.  4xx client errors are not retried.
 * - Uses exponential backoff (1 s, 2 s) between retries.
 * - Returns the parsed JSON on success, or null on failure.
 */
async function fetchWithCheck (url) {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

    try {
      const response = await fetch(url, { signal: controller.signal })
      clearTimeout(timeout)

      if (!response.ok) {
        // Retry on server errors (5xx), give up immediately on client errors (4xx)
        if (response.status >= 500 && attempt < MAX_RETRIES) {
          console.warn(`HTTP ${response.status} from ${url}, retrying (${attempt + 1}/${MAX_RETRIES})…`)
          await delay(RETRY_BASE_DELAY_MS * 2 ** attempt)
          continue
        }
        console.error(`HTTP ${response.status} fetching ${url}`)
        return null
      }

      const data = await response.json()
      if (data && data.error) {
        console.error(`API error from ${url}: ${data.error}`)
        return null
      }
      return data
    } catch (e) {
      clearTimeout(timeout)

      if (attempt < MAX_RETRIES) {
        const reason = e.name === 'AbortError' ? 'timeout' : 'network error'
        console.warn(`Fetch ${reason} for ${url}, retrying (${attempt + 1}/${MAX_RETRIES})…`)
        await delay(RETRY_BASE_DELAY_MS * 2 ** attempt)
        continue
      }

      if (e.name === 'AbortError') {
        console.error(`Request timed out after ${MAX_RETRIES + 1} attempts: ${url}`)
      } else {
        console.error(`Fetch failed after ${MAX_RETRIES + 1} attempts for ${url}:`, e)
      }
      return null
    }
  }
  return null
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

export async function fetchGenerationSummary () {
  return fetchWithCheck(`${API_BASE_URL}/generation/summary`)
}

export async function fetchSolarData () {
  const [uk, france, energy_charts, denmark, belgium, italy, sweden, norway] = await Promise.all([
    fetchWithCheck(`${API_BASE_URL}/solar/solar`),
    fetchWithCheck(`${API_BASE_URL}/solar/solar/france`),
    fetchWithCheck(`${API_BASE_URL}/solar/solar/energy_charts`),
    fetchWithCheck(`${API_BASE_URL}/solar/solar/denmark`),
    fetchWithCheck(`${API_BASE_URL}/solar/solar/belgium`),
    fetchWithCheck(`${API_BASE_URL}/solar/solar/italy`),
    fetchWithCheck(`${API_BASE_URL}/solar/solar/sweden`),
    fetchWithCheck(`${API_BASE_URL}/solar/solar/norway`)
  ])
  
  const ireland = null;
  const northern_ireland = null;

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

  const result = { uk, france, denmark, belgium, italy, ireland, northern_ireland, sweden, norway, ...mappedEnergyCharts }

  // Return null only when every single endpoint failed — lets callers
  // distinguish "no data at all" from "some countries unavailable".
  const hasAnyData = Object.values(result).some(v => v != null)
  return hasAnyData ? result : null
}

export async function fetchRiverLevels () {
  return fetchWithCheck(`${API_BASE_URL}/environment/river_levels`)
}

// Cache buster for static TopoJSON files.
// Bump this value whenever boundary files are updated to invalidate browser caches.
const STATIC_VERSION = '2024.5'

/** Country key → TopoJSON filename mapping. */
const REGION_FILES = [
  ['uk', 'gb-dno-license-areas-2024_wgs84.topojson'],
  ['france', 'france-regions.topojson'],
  ['spain', 'spain-regions.topojson'],
  ['netherlands', 'netherlands.topojson'],
  ['austria', 'austria.topojson'],
  ['switzerland', 'switzerland.topojson'],
  ['poland', 'poland.topojson'],
  ['czechia', 'czechia.topojson'],
  ['germany', 'germany.topojson'],
  ['denmark', 'denmark-regions.topojson'],
  ['belgium', 'belgium-regions.topojson'],
  ['portugal', 'portugal.topojson'],
  ['italy', 'italy.topojson'],
  ['ireland', 'ireland.topojson'],
  ['northern_ireland', 'northern_ireland.topojson'],
  ['sweden', 'sweden.topojson'],
  ['norway', 'norway.topojson'],
]

/**
 * Fetch boundary TopoJSON for all countries.
 *
 * Returns an object keyed by country with successfully loaded data.
 * Countries whose fetches failed (after retries) are omitted — the map
 * will render without them rather than crashing entirely.
 * Returns null only when every single fetch failed.
 */
export async function fetchMapRegions () {
  const results = await Promise.all(
    REGION_FILES.map(async ([key, file]) => [
      key,
      await fetchWithCheck(`${BACKEND_URL}/static/${file}?v=${STATIC_VERSION}`)
    ])
  )

  const regions = {}
  const failed = []
  for (const [key, data] of results) {
    if (data) {
      regions[key] = data
    } else {
      failed.push(key)
    }
  }

  if (failed.length > 0) {
    console.warn(`Failed to load boundary data for: ${failed.join(', ')}`)
  }

  return Object.keys(regions).length > 0 ? regions : null
}
