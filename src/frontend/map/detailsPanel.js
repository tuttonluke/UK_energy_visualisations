import Chart from 'chart.js/auto'
import { COUNTRIES } from './countryRegistry.js'

let detailChartInstance = null

export function initDetailsPanel (closeCallback) {
  const closeBtn = document.getElementById('close-details-btn')
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      closeDetailsPanel()
      if (closeCallback) closeCallback()
    })
  }
}

export function openDetailsPanel (countryKey) {
  const panel = document.getElementById('country-details-panel')
  const titleEl = document.getElementById('details-country-title')
  const capTotalEl = document.getElementById('details-cap-total')
  const capDensityEl = document.getElementById('details-cap-density')
  const canvas = document.getElementById('country-detail-chart')

  if (!panel || !titleEl || !canvas) return

  const config = COUNTRIES[countryKey]
  if (!config) return

  titleEl.textContent = config.displayTitle || countryKey.toUpperCase()
  
  // Clear data until hooked up to backend
  capTotalEl.textContent = '--'
  capDensityEl.textContent = '--'

  panel.classList.add('active')

  // Render dummy chart
  if (detailChartInstance) {
    detailChartInstance.destroy()
  }

  const ctx = canvas.getContext('2d')
  
  // Empty data until hooked up to backend
  const labels = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`)
  const data = []

  detailChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Solar Output (MW)',
        data,
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(51, 65, 85, 0.5)' },
          ticks: { color: '#94a3b8', maxTicksLimit: 6 }
        },
        y: {
          grid: { color: 'rgba(51, 65, 85, 0.5)' },
          ticks: { color: '#94a3b8' },
          beginAtZero: true
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  })
}

export function closeDetailsPanel () {
  const panel = document.getElementById('country-details-panel')
  if (panel) {
    panel.classList.remove('active')
  }
}
