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
  ITALY: { center: [12.56, 41.87], zoom: 5.0 },
}

export const MAP_CONFIG = {
  style: {
    version: 8,
    sources: {
      "protomaps": {
        type: "vector",
        url: "pmtiles:///map_data.pmtiles"
      }
    },
    glyphs: "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf",
    layers: [
      {
        id: "background",
        type: "background",
        paint: {
          "background-color": "#0f172a" // Match --bg-main
        }
      },
      {
        id: "earth",
        type: "fill",
        source: "protomaps",
        "source-layer": "earth",
        paint: {
          "fill-color": "#1e293b" // Match --bg-sidebar / slate-800
        }
      },
      {
        id: "water",
        type: "fill",
        source: "protomaps",
        "source-layer": "water",
        paint: {
          "fill-color": "#0f172a" // Same as background
        }
      },
      {
        id: "boundaries",
        type: "line",
        source: "protomaps",
        "source-layer": "boundaries",
        paint: {
          "line-color": "#334155", // Match --border-color
          "line-width": 1
        }
      },
      {
        id: "places",
        type: "symbol",
        source: "protomaps",
        "source-layer": "places",
        layout: {
          "text-field": "{name}",
          "text-size": 12,
          "text-font": ["Noto Sans Regular"],
          "text-transform": "uppercase",
          "text-letter-spacing": 0.1
        },
        paint: {
          "text-color": "#94a3b8", // Match --text-muted
          "text-halo-color": "#0f172a", // Outline text so it's readable
          "text-halo-width": 1
        }
      }
    ]
  },
  center: [-2.5, 54.5], // Centre of UK
  zoom: 5.5,
}
