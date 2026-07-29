import * as pmtiles from 'pmtiles'
import * as maplibregl from 'maplibre-gl'

let registered = false

/**
 * Ensures the PMTiles protocol is registered with MapLibre exactly once.
 * Must be called before creating any map instance that uses a PMTiles source.
 *
 * Safe to call multiple times — subsequent calls are no-ops.
 */
export function ensurePMTilesProtocol () {
  if (registered) return
  const protocol = new pmtiles.Protocol()
  maplibregl.addProtocol('pmtiles', protocol.tile)
  registered = true
}
