import { COUNTRIES } from './countryRegistry.js'

/**
 * Update the stats panel to show summary data for the selected country.
 *
 * Replaces the if/else-if chain that was duplicated per country.
 *
 * @param {string | null} selectedCountry  - Country key or null
 * @param {object | null} currentSolarData - Solar data keyed by country
 */
export function updateStatsPanel (selectedCountry, currentSolarData) {
  const titleEl = document.getElementById('stats-title')
  const valContainer = document.getElementById('stats-value-container')
  const valEl = document.getElementById('total-gen-display')

  if (!titleEl || !valContainer || !valEl) return

  if (!selectedCountry || !currentSolarData) {
    titleEl.textContent = 'Select a country'
    valContainer.style.display = 'none'
    return
  }

  const config = COUNTRIES[selectedCountry]
  if (!config) return

  valContainer.style.display = 'block'
  titleEl.textContent = config.statsLabel

  const countryData = currentSolarData[selectedCountry]
  if (!countryData) {
    valEl.textContent = 'Unavailable'
  } else {
    valEl.textContent = countryData.totalGen && countryData.totalGen.solar !== undefined ? countryData.totalGen.solar : '0'
  }
}
