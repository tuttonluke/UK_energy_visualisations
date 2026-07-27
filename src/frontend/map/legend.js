import { 
  SOLAR_COLORS, 
  NORMALIZED_STOPS, 
  MACRO_ABSOLUTE_STOPS, 
  MICRO_ABSOLUTE_STOPS 
} from './colorScales.js'

const { c0, c1, c2, c3, c4, c5, c6, c7, c8 } = SOLAR_COLORS
const GRADIENT_CSS = `linear-gradient(to right, ${c0}, ${c1}, ${c2}, ${c3}, ${c4}, ${c5}, ${c6}, ${c7}, ${c8})`

/**
 * Render the continuous scale legend as HTML.
 */
function renderContinuousLegend (min, mid, max) {
  return `
    <div class="continuous-scale-bar" style="background: ${GRADIENT_CSS};"></div>
    <div class="legend-labels">
        <span>${min}</span>
        <span>${mid}</span>
        <span>${max}+</span>
    </div>
  `
}

/**
 * Format large numbers for legend labels.
 */
function formatLabel (num) {
  if (num >= 1000) {
    return (num / 1000).toString() + 'k'
  }
  return num.toString()
}

/**
 * Update the legend panel in the DOM.
 *
 * @param {boolean} isNormalized - Whether the normalise toggle is on
 * @param {boolean} isMicroMode  - Whether a country with micro data is selected
 */
export function updateLegend (isNormalized, isMicroMode) {
  let title = ''
  let stops = []

  if (isNormalized) {
    title = 'Solar Density (MW/km²)'
    stops = NORMALIZED_STOPS
  } else if (isMicroMode) {
    title = 'Regional Output (MW)'
    stops = MICRO_ABSOLUTE_STOPS
  } else {
    title = 'National Output (MW)'
    stops = MACRO_ABSOLUTE_STOPS
  }

  const titleEl = document.getElementById('solar-legend-title')
  const scaleEl = document.getElementById('solar-legend-scale')
  
  if (titleEl) titleEl.textContent = title
  if (scaleEl) {
    const min = formatLabel(stops[0])
    const mid = formatLabel(stops[4])
    const max = formatLabel(stops[8])
    scaleEl.innerHTML = renderContinuousLegend(min, mid, max)
  }
}
