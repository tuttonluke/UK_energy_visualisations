let chartInstance = null;

// Elexon BMRS colors for fuel types (approximate typical colors)
const fuelColors = {
    "CCGT": "#f59e0b", // Amber
    "WIND": "#0ea5e9", // Sky blue
    "NUCLEAR": "#8b5cf6", // Violet
    "BIOMASS": "#22c55e", // Green
    "COAL": "#475569", // Slate
    "NPSHYD": "#0284c7", // Light blue
    "OCGT": "#ea580c", // Orange
    "OIL": "#334155", // Dark slate
    "OTHER": "#a8a29e", // Stone
    "PS": "#0369a1", // Dark blue (Pumped Storage)
    "INTELEC": "#ec4899", // Interconnectors (Pink/Purple shades)
    "INTFR": "#d946ef",
    "INTIFA2": "#c026d3",
    "INTNED": "#a21caf",
    "INTNEM": "#86198f",
    "INTNSL": "#701a75",
    "INTVKL": "#4a044e"
};

export async function initCharts() {
    if (chartInstance) return; // Already initialized

    const ctx = document.getElementById('generationChart').getContext('2d');
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/generation/summary');
        const data = await response.json();
        
        let sortedData;
        if (Array.isArray(data)) {
            sortedData = data;
        } else if (data && data.data && Array.isArray(data.data)) {
            sortedData = data.data;
        } else {
            console.error("No generation data available", data);
            return;
        }

        if (!sortedData || sortedData.length === 0) {
            console.error("No generation data points available");
            return;
        }

        // Parse data for Chart.js
        // The API returns an array of periods, each with a 'startTime' and 'data' array of { fuelType, generation }
        const timeLabels = [];
        const datasets = {};
        
        // Ensure chronological order
        sortedData = sortedData.sort((a, b) => new Date(a.startTime) - new Date(b.startTime));

        sortedData.forEach(period => {
            timeLabels.push(new Date(period.startTime));
            
            period.data.forEach(item => {
                if (!datasets[item.fuelType]) {
                    datasets[item.fuelType] = {
                        label: item.fuelType,
                        data: Array(sortedData.length).fill(0), // Pre-fill with 0s
                        backgroundColor: fuelColors[item.fuelType] || "#cbd5e1",
                        borderColor: fuelColors[item.fuelType] || "#cbd5e1",
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        borderWidth: 1
                    };
                }
            });
        });

        // Now populate the data arrays
        sortedData.forEach((period, index) => {
            period.data.forEach(item => {
                if (datasets[item.fuelType]) {
                    datasets[item.fuelType].data[index] = item.generation;
                }
            });
        });

        // Create chart config
        const config = {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: Object.values(datasets)
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#f8fafc',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y + ' MW';
                                }
                                return label;
                            }
                        }
                    },
                    legend: {
                        position: 'right',
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
        };

        chartInstance = new Chart(ctx, config);

    } catch (error) {
        console.error("Failed to load chart data:", error);
    }
}
