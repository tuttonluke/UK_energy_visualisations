import * as topojson from 'topojson-client'
import { area } from '@turf/area'
import { COUNTRIES, COUNTRY_KEYS } from './countryRegistry.js'

// ---------------------------------------------------------------------------
// Internal area cache — geographic boundaries are static so areas
// only need to be computed once (or when boundary data changes).
// ---------------------------------------------------------------------------
let cachedAreaData = null

/**
 * Merge topology geometries into a solid country outline,
 * removing internal region boundaries and holes.
 *
 * @param {object} topology - TopoJSON topology
 * @param {object} object   - The objects entry (e.g. topology.objects.data)
 * @returns {object} GeoJSON geometry
 */
function getSolidOutline (topology, object) {
  const merged = topojson.merge(topology, object.geometries)
  if (merged.type === 'Polygon') {
    merged.coordinates = [merged.coordinates[0]]
  } else if (merged.type === 'MultiPolygon') {
    merged.coordinates = merged.coordinates.map(poly => [poly[0]])
  }
  return merged
}

/**
 * Resolve the feature ID value from properties, using the
 * primary property and an optional fallback.
 */
function getFeatureIdValue (properties, config) {
  return (
    properties[config.featureIdProp] ||
    (config.featureIdFallbackProp ? properties[config.featureIdFallbackProp] : null)
  )
}

/**
 * Process raw TopoJSON + solar data into enriched GeoJSON
 * ready for Mapbox GL, plus country outlines.
 *
 * @param {object} topoData  - Raw TopoJSON keyed by country
 * @param {object} solarData - Solar generation data keyed by country
 * @returns {{ geojsonData: object, outlineGeojsonData: object, countryFeatureIds: Record<string, string[]> }}
 */
export function enrichMapData (topoData, solarData) {
  const countryFeatureIds = {}
  const allFeatures = []
  const outlineFeatures = []

  // -----------------------------------------------------------------------
  // 1. Convert TopoJSON → GeoJSON per country
  // -----------------------------------------------------------------------
  const geojsonByCountry = {}
  COUNTRY_KEYS.forEach(key => {
    geojsonByCountry[key] = topojson.feature(
      topoData[key],
      topoData[key].objects.data
    )
  })

  // -----------------------------------------------------------------------
  // 2. Compute areas (only on first load — boundaries are static)
  // -----------------------------------------------------------------------
  if (!cachedAreaData) {
    cachedAreaData = {}
    COUNTRY_KEYS.forEach(key => {
      const config = COUNTRIES[key]
      let totalArea = 0
      const featureAreas = new Map()

      geojsonByCountry[key].features.forEach(f => {
        const areaSqKm = area(f) / 1_000_000
        const featureId = getFeatureIdValue(f.properties, config)
        featureAreas.set(featureId, areaSqKm)
        totalArea += areaSqKm
      })

      cachedAreaData[key] = { totalArea, featureAreas }
    })
  }

  // -----------------------------------------------------------------------
  // 3. Enrich features in a single pass per country
  // -----------------------------------------------------------------------
  COUNTRY_KEYS.forEach(key => {
    const config = COUNTRIES[key]
    const countryData = solarData[key]
    const isUnavailable = !countryData
    const { totalArea, featureAreas } = cachedAreaData[key]

    if (isUnavailable) {
      console.warn(`${config.displayTitle} solar data unavailable — regions will show as unavailable`)
    }

    countryFeatureIds[key] = []
    const macroGen = countryData ? countryData.totalGen : 0

    geojsonByCountry[key].features.forEach(feature => {
      const featureIdValue = getFeatureIdValue(feature.properties, config)
      const customId = `${config.idPrefix}-${featureIdValue}`
      const featureArea = featureAreas.get(featureIdValue) || 0

      feature.id = customId
      countryFeatureIds[key].push(customId)

      feature.properties.areaSqKm = featureArea
      feature.properties.customId = customId
      feature.properties.country = key
      feature.properties.unavailable = isUnavailable

      // Micro generation: only for countries that publish regional data
      const microGen =
        config.hasMicroData && countryData && countryData[featureIdValue] !== undefined
          ? countryData[featureIdValue]
          : 0

      feature.properties.macroGeneration = macroGen
      feature.properties.microGeneration = microGen
      feature.properties.macroNormalized = totalArea > 0 ? macroGen / totalArea : 0
      feature.properties.microNormalized = featureArea > 0 ? microGen / featureArea : 0

      // Display properties (read from the registry's property mappings)
      feature.properties.displayName = feature.properties[config.displayNameProp]
      feature.properties.displaySub = config.displaySubProp
        ? feature.properties[config.displaySubProp]
        : config.displaySubFallback
      feature.properties.displayId =
        feature.properties[config.displayIdProp] || config.displayIdFallback || key.toUpperCase()
    })

    allFeatures.push(...geojsonByCountry[key].features)

    // Build country outline
    const outline = getSolidOutline(topoData[key], topoData[key].objects.data)
    const macroNormalized = totalArea > 0 ? macroGen / totalArea : 0
    outlineFeatures.push({
      type: 'Feature',
      id: key,
      properties: { country: key, macroGeneration: macroGen, macroNormalized },
      geometry: outline,
    })
  })

  return {
    geojsonData: { type: 'FeatureCollection', features: allFeatures },
    outlineGeojsonData: { type: 'FeatureCollection', features: outlineFeatures },
    countryFeatureIds,
  }
}

/** Clear the area cache (e.g. if boundary files are updated). */
export function clearAreaCache () {
  cachedAreaData = null
}
