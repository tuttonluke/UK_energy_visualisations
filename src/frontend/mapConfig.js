import { BACKEND_URL } from './api.js'

export const MAP_CONFIG = {
  style: 'mapbox://styles/mapbox/dark-v11',
  center: [-2.5, 54.5], // Centre of UK
  zoom: 5.5,
  transformRequest: (url, resourceType) => {
    if (url.startsWith('https://api.mapbox.com/')) {
      const urlObj = new URL(url);
      const proxyUrl = new URL(`${BACKEND_URL}/api/proxy/mapbox`);
      proxyUrl.searchParams.set('path', urlObj.pathname);
      urlObj.searchParams.forEach((value, key) => {
        proxyUrl.searchParams.append(key, value);
      });
      return {
        url: proxyUrl.toString()
      }
    }
  }
}
