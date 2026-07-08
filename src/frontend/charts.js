let chartInstance = null

// User-requested order from bottom to top:
// Nuclear, Coal, Gas (CCGT), Gas (OCGT), Oil, Imports, Biomass, Wind, Solar, Hydro, Pumped Storage, Other
const FUEL_ORDER = [
  'Nuclear',
  'Coal',
  'Gas (CCGT)',
  'Gas (OCGT)',
  'Oil',
  'Imports',
  'Biomass',
  'Wind',
  'Solar',
  'Hydro',
  'Pumped Storage',
  'Other'
]

const fuelColors = {
  'Nuclear': '#afafaf',
  'Coal': '#1e1e1f',
  'Gas (CCGT)': '#349fdd',
  'Gas (OCGT)': '#0c5f8f',
  'Oil': '#4A545D',
  'Imports': '#a465b4',
  'Biomass': '#55431bb7',
  'Wind': '#61b96f',
  'Solar': '#e6cb54',
  'Hydro': '#658CA8',
  'Pumped Storage': '#4D7591',
  'Other': '#A3A09E'
}

function getStandardizedFuelType(rawType) {
  if (rawType.startsWith('INT') || rawType === 'INTELEC') return 'Imports';
  if (rawType === 'CCGT') return 'Gas (CCGT)';
  if (rawType === 'OCGT') return 'Gas (OCGT)';
  if (rawType === 'NPSHYD') return 'Hydro';
  if (rawType === 'PS') return 'Pumped Storage';
  
  const mapped = {
    'NUCLEAR': 'Nuclear',
    'COAL': 'Coal',
    'OIL': 'Oil',
    'BIOMASS': 'Biomass',
    'WIND': 'Wind',
    'SOLAR': 'Solar',
    'OTHER': 'Other'
  }[rawType];

  return mapped || 'Other';
}

function lightenColor(hex, percent = 0.4) {
  if (!hex || hex[0] !== '#') return hex;
  let r = parseInt(hex.substring(1, 3), 16);
  let g = parseInt(hex.substring(3, 5), 16);
  let b = parseInt(hex.substring(5, 7), 16);

  r = Math.min(255, Math.floor(r * (1 + percent)));
  g = Math.min(255, Math.floor(g * (1 + percent)));
  b = Math.min(255, Math.floor(b * (1 + percent)));

  const toHex = (n) => n.toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function hexToRgba(hex, alpha) {
  if (!hex || hex[0] !== '#') return hex;
  let r = parseInt(hex.substring(1, 3), 16);
  let g = parseInt(hex.substring(3, 5), 16);
  let b = parseInt(hex.substring(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export async function initCharts () {
  if (chartInstance) return // Already initialized

  const ctx = document.getElementById('generationChart').getContext('2d')

  try {
    const response = await fetch('http://127.0.0.1:8000/api/generation/summary')
    const data = await response.json()

    let sortedData
    if (Array.isArray(data)) {
      sortedData = data
    } else if (data && data.data && Array.isArray(data.data)) {
      sortedData = data.data
    } else {
      console.error('No generation data available', data)
      return
    }

    if (!sortedData || sortedData.length === 0) {
      console.error('No generation data points available')
      return
    }

    // Parse data for Chart.js
    const timeLabels = []
    const datasets = {}

    // Ensure chronological order
    sortedData = sortedData.sort(
      (a, b) => new Date(a.startTime) - new Date(b.startTime)
    )

    sortedData.forEach(period => {
      timeLabels.push(new Date(period.startTime))

      period.data.forEach(item => {
        const fuelType = getStandardizedFuelType(item.fuelType)
        if (!datasets[fuelType]) {
          const bgColor = fuelColors[fuelType] || '#cbd5e1';
          const bgColorWithOpacity = hexToRgba(bgColor, 0.7);
          const borderColor = lightenColor(bgColor, 0.2);
          datasets[fuelType] = {
            label: fuelType,
            data: Array(sortedData.length).fill(0),
            backgroundColor: bgColorWithOpacity,
            borderColor: borderColor,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBorderColor: '#ffffff',
            pointHoverBorderWidth: 2,
            borderWidth: 3
          }
        }
      })
    })

    // Now populate the data arrays
    sortedData.forEach((period, index) => {
      period.data.forEach(item => {
        const fuelType = getStandardizedFuelType(item.fuelType)
        if (datasets[fuelType]) {
          datasets[fuelType].data[index] += item.generation
        }
      })
    })

    // If a source has 0 generation across all periods, remove its border so it leaves no trace
    Object.values(datasets).forEach(ds => {
      const isAllZero = ds.data.every(val => val === 0);
      if (isAllZero) {
        ds.borderWidth = 0;
      }
    })

    const orderedDatasets = []
    FUEL_ORDER.forEach(fuelName => {
      if (datasets[fuelName]) {
        orderedDatasets.push(datasets[fuelName])
      }
    })
    
    Object.values(datasets).forEach(ds => {
      if (!orderedDatasets.includes(ds)) {
        orderedDatasets.push(ds)
      }
    })

    // Create chart config
    const config = {
      type: 'line',
      data: {
        labels: timeLabels,
        datasets: orderedDatasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.7)',
            titleColor: '#f8fafc',
            bodyColor: '#cbd5e1',
            borderColor: '#334155',
            borderWidth: 2,
            padding: 10,
            caretPadding: 15,
            bodySpacing: 10,
            titleMarginBottom: 15,
            boxPadding: 8,
            itemSort: function(a, b) {
              return b.datasetIndex - a.datasetIndex;
            },
            callbacks: {
              label: function (context) {
                let label = context.dataset.label || ''
                if (label) {
                  label += ': '
                }
                if (context.parsed.y !== null) {
                  label += context.parsed.y + ' MW'
                }
                return label
              }
            }
          },
          legend: {
            position: 'right',
            reverse: true,
            labels: {
              color: '#94a3b8',
              usePointStyle: true,
              boxWidth: 8
            }
          }
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'hour',
              tooltipFormat: 'D MMM YYYY, HH:mm',
              displayFormats: {
                hour: 'HH:mm'
              }
            },
            title: {
              display: true,
              text: 'Time (UTC)',
              color: '#64748b'
            },
            grid: {
              color: '#1e293b'
            },
            ticks: {
              color: '#94a3b8'
            }
          },
          y: {
            stacked: true,
            title: {
              display: true,
              text: 'Generation (MW)',
              color: '#64748b'
            },
            grid: {
              color: '#1e293b'
            },
            ticks: {
              color: '#94a3b8'
            }
          }
        }
      }
    }

    chartInstance = new Chart(ctx, config)
  } catch (error) {
    console.error('Failed to load chart data:', error)
  }
}
