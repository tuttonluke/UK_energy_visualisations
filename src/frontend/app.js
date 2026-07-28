import { initCharts } from './charts.js'
import 'maplibre-gl/dist/maplibre-gl.css'
import { initMap, updateMapData } from './map/index.js'
import { initEnvMap, updateEnvMapData } from './envMap.js'

document.addEventListener('DOMContentLoaded', () => {
  let activeTab = 'tab-generation'
  const navItems = document.querySelectorAll('.nav-item')
  const tabContents = document.querySelectorAll('.tab-content')

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(nav => nav.classList.remove('active'))
      tabContents.forEach(tab => tab.classList.remove('active'))

      item.classList.add('active')

      const targetId = item.getAttribute('data-target')
      const tabEl = document.getElementById(targetId)
      if (!tabEl) {
        console.error(`Tab element not found: ${targetId}`)
        return
      }
      tabEl.classList.add('active')
      activeTab = targetId

      if (targetId === 'tab-generation') {
        initCharts()
      } else if (targetId === 'tab-maps') {
        initMap()
      } else if (targetId === 'tab-environment') {
        initEnvMap()
      }
    })
  })

  // Only init the default visible tab — maps defer until their tab is clicked
  initCharts()

  // Polling every 5 minutes — only refresh the active tab
  setInterval(() => {
    if (activeTab === 'tab-generation') {
      initCharts()
    } else if (activeTab === 'tab-maps') {
      updateMapData()
    } else if (activeTab === 'tab-environment') {
      updateEnvMapData()
    }
  }, 300_000)
})
