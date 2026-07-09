import { BACKEND_URL } from './api.js'

export const MAP_CONFIG = {
  style: 'mapbox://styles/mapbox/dark-v11',
  center: [-2.5, 54.5], // Centre of UK
  zoom: 5.5,
  transformRequest: (url, resourceType) => {
    if (url.startsWith('https://api.mapbox.com/')) {
      return {
        url: `${BACKEND_URL}/api/proxy/mapbox?url=${encodeURIComponent(url)}`
      }
    }
  }
}
