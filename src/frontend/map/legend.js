import { SOLAR_COLORS } from './colorScales.js'

const { c0, c2, c4, c6, c8 } = SOLAR_COLORS

/**
 * Pre-defined legend configurations.
 * Each has a title and an ordered array of [color, label] items.
 */
const LEGEND_CONFIGS = {
  normalized: {
    title: 'Solar Density (MW/km²)',
    items: [
      [c8, '> 0.50'],
      [c6, '~ 0.20'],
      [c4, '~ 0.06'],
      [c2, '~ 0.01'],
      [c0, '0 / Offline'],
    ],
  },
  absoluteMicro: {
    title: 'Regional Output (MW)',
    items: [
      [c8, '> 5,000'],
      [c6, '~ 2,000'],
      [c4, '~ 500'],
      [c2, '~ 100'],
      [c0, '0 / Offline'],
    ],
  },
  absoluteMacro: {
    title: 'National Output (MW)',
    items: [
      [c8, '> 60,000'],
      [c6, '~ 20,000'],
      [c4, '~ 5,000'],
      [c2, '~ 1,000'],
      [c0, '0 / Offline'],
    ],
  },
}

/**
 * Render legend items as HTML.  Uses only hardcoded palette
 * constants so there is no XSS risk from dynamic values.
 */
function renderLegendItems (items) {
  return items
    .map(
      ([color, label]) =>
        `<div class="legend-item"><div class="legend-color" style="background-color: ${color};"></div><span>${label}</span></div>`
    )
    .join('\n')
}

/**
 * Update the legend panel in the DOM.
 *
 * @param {boolean} isNormalized - Whether the normalise toggle is on
 * @param {boolean} isMicroMode  - Whether a country with micro data is selected
 */
export function updateLegend (isNormalized, isMicroMode) {
  let config
  if (isNormalized) {
    config = LEGEND_CONFIGS.normalized
  } else if (isMicroMode) {
    config = LEGEND_CONFIGS.absoluteMicro
  } else {
    config = LEGEND_CONFIGS.absoluteMacro
  }

  const titleEl = document.getElementById('solar-legend-title')
  const scaleEl = document.getElementById('solar-legend-scale')
  if (titleEl) titleEl.textContent = config.title
  if (scaleEl) scaleEl.innerHTML = renderLegendItems(config.items)
}
