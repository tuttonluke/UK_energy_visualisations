import { initCharts } from './charts.js'
import 'maplibre-gl/dist/maplibre-gl.css'
import { initMap, updateMapData } from './map/index.js'
import { initEnvMap, updateEnvMapData } from './envMap.js'

document.addEventListener('DOMContentLoaded', () => {
  let activeTab = 'tab-generation'
  let pollTimer = null
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

  // -------------------------------------------------------------------------
  // Polling — refresh data for the active tab every 30 seconds.
  //
  // Uses setTimeout chaining (not setInterval) so the next poll only starts
  // after the previous one completes, preventing request pileup on slow
  // connections.  Polling pauses when the browser tab is hidden and resumes
  // with an immediate refresh when it becomes visible again.
  // -------------------------------------------------------------------------

  /** Refresh data for whichever tab is currently visible. */
  async function pollActiveTab () {
    try {
      if (activeTab === 'tab-generation') {
        await initCharts()
      } else if (activeTab === 'tab-maps') {
        await updateMapData()
      } else if (activeTab === 'tab-environment') {
        await updateEnvMapData()
      }
    } catch (e) {
      console.error('Poll error:', e)
    }
  }

  /** Schedule the next poll — only called after the previous one completes. */
  function scheduleNextPoll () {
    clearTimeout(pollTimer)
    pollTimer = setTimeout(async () => {
      await pollActiveTab()
      // Only continue the chain if the tab is still visible
      if (!document.hidden) {
        scheduleNextPoll()
      }
    }, 30_000)
  }

  // Pause polling when the browser tab is hidden to avoid wasting
  // bandwidth and server resources.  Resume with an immediate refresh
  // when the tab becomes visible again.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      clearTimeout(pollTimer)
      pollTimer = null
    } else {
      pollActiveTab()
      scheduleNextPoll()
    }
  })

  // Only init the default visible tab — maps defer until their tab is clicked.
  // Catch startup errors so polling always begins even if the initial load fails.
  initCharts().catch(e => console.error('Initial chart load failed:', e))
  scheduleNextPoll()
})
