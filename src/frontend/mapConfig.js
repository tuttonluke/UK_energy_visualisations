import { BACKEND_URL } from './api.js'

export const MAP_VIEWS = {
  DEFAULT: { center: [-1, 48.0], zoom: 3 },
  UK: { center: [-2.5, 54.0], zoom: 4.8 },
  FRANCE: { center: [2.2, 46.2], zoom: 4.5 },
  GERMANY: { center: [10.4, 51.1], zoom: 4.5 },
}

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
