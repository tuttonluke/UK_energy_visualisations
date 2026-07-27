import { MAP_VIEWS } from '../mapConfig.js'

/**
 * Data-driven country registry.
 *
 * To add a new country, add a single entry here.  All map logic
 * (enrichment, styling, events, tooltips, stats panel) reads from
 * this registry instead of hard-coding per-country branches.
 */
export const COUNTRIES = {
  uk: {
    key: 'uk',
    idPrefix: 'uk',
    displayTitle: 'GREAT BRITAIN',
    statsLabel: 'Total GB Output',
    featureIdProp: 'ID',
    featureIdFallbackProp: null,
    displayNameProp: 'Area',
    displaySubProp: 'DNO_Full',
    displaySubFallback: null,
    displayIdProp: 'ID',
    displayIdFallback: null,
    dataSource: 'Sheffield Solar (PV_Live)',
    hasMicroData: true,
    mapView: MAP_VIEWS.UK,
  },

  france: {
    key: 'france',
    idPrefix: 'fr',
    displayTitle: 'FRANCE',
    statsLabel: 'Total France Output',
    featureIdProp: 'code',
    featureIdFallbackProp: null,
    displayNameProp: 'nom',
    displaySubProp: null,
    displaySubFallback: 'France Region',
    displayIdProp: 'code',
    displayIdFallback: null,
    dataSource: 'RTE (éCO2mix)',
    hasMicroData: true,
    mapView: MAP_VIEWS.FRANCE,
  },

  germany: {
    key: 'germany',
    idPrefix: 'de',
    displayTitle: 'GERMANY',
    statsLabel: 'Total Germany Output',
    featureIdProp: 'id',
    featureIdFallbackProp: 'name',
    displayNameProp: 'name',
    displaySubProp: null,
    displaySubFallback: 'Germany (State)',
    displayIdProp: 'id',
    displayIdFallback: 'DE',
    dataSource: 'Fraunhofer ISE (Energy-Charts)',
    hasMicroData: false,
    mapView: MAP_VIEWS.GERMANY,
  },
}

/** Ordered array of country keys (stable iteration order). */
export const COUNTRY_KEYS = Object.keys(COUNTRIES)
