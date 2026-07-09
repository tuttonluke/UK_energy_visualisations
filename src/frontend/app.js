import { initCharts } from './charts.js'
import { initMap, updateMapData } from './map.js'
import { initEnvMap, updateEnvMapData } from './envMap.js'

document.addEventListener('DOMContentLoaded', () => {
  const navItems = document.querySelectorAll('.nav-item')
  const tabContents = document.querySelectorAll('.tab-content')

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(nav => nav.classList.remove('active'))
      tabContents.forEach(tab => tab.classList.remove('active'))

      item.classList.add('active')

      const targetId = item.getAttribute('data-target')
      document.getElementById(targetId).classList.add('active')

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

  // Polling every 5 minutes (300,000 ms)
  setInterval(() => {
    initCharts()
    updateMapData()
    updateEnvMapData()
  }, 300_000)
})
