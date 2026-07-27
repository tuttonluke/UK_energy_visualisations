import { BACKEND_URL } from './api.js'

export const MAP_VIEWS = {
  DEFAULT: { center: [-1, 48.0], zoom: 3 },
  UK: { center: [-2.5, 54.0], zoom: 4.8 },
  FRANCE: { center: [2.2, 46.2], zoom: 4.5 },
  GERMANY: { center: [10.4, 51.1], zoom: 4.5 },
  SPAIN: { center: [-3.7, 40.4], zoom: 5.0 },
  NETHERLANDS: { center: [5.29, 52.13], zoom: 6.0 },
  AUSTRIA: { center: [14.55, 47.51], zoom: 6.0 },
  SWITZERLAND: { center: [8.22, 46.81], zoom: 6.5 },
  POLAND: { center: [19.14, 51.91], zoom: 5.0 },
  CZECHIA: { center: [15.47, 49.81], zoom: 6.0 },
  DENMARK: { center: [9.50, 56.26], zoom: 6.0 },
  BELGIUM: { center: [4.46, 50.50], zoom: 6.5 },
  PORTUGAL: { center: [-8.2, 39.4], zoom: 6.0 },
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
