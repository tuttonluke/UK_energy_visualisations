import { escapeHtml } from '../utils.js'
import { COUNTRIES } from './countryRegistry.js'

/**
 * Build the HTML string for the map hover tooltip.
 *
 * Extracted from the inline template that was embedded inside
 * the mousemove handler, making it independently testable and
 * easier to maintain.
 *
 * @param {object} opts
 * @param {string} opts.country          - Country key (e.g. 'uk')
 * @param {boolean} opts.isMicro         - Whether we are in micro (regional) mode
 * @param {boolean} opts.isSelected      - Whether the country is currently selected
 * @param {string} opts.regionName       - Region display name
 * @param {string} opts.subName          - Sub-label (e.g. DNO name)
 * @param {string} opts.displayId        - Region identifier
 * @param {string} opts.outputLabel      - Label for the output section
 * @param {string} opts.displayRegionData     - Formatted absolute value
 * @param {string} opts.displayNormalizedData - Formatted density value
 * @returns {string} Sanitised HTML
 */
export function buildTooltipHtml ({
  country,
  isMicro,
  isSelected,
  regionName,
  subName,
  displayId,
  outputLabel,
  displayRegionData,
  displayNormalizedData,
  disabledHoverMessage,
  generatedTime,
  isDataUnavailable,
}) {
  const config = COUNTRIES[country]
  const sourceLabel = config?.dataSource || 'Unknown'
  const title = isMicro ? regionName : (config?.displayTitle || country.toUpperCase())
  
  let subtitle = isMicro ? subName : 'National'
  if (isSelected && !config?.hasMicroData) {
    subtitle = 'National: no regional data available'
  }

  return `
    <div style="min-width: 250px;">
        <h3 style="margin:0; color:var(--accent); font-size:1.125rem;">${escapeHtml(title)}</h3>
        <p style="margin:4px 0 0 0; color:var(--text-muted); font-size:0.75rem;">${escapeHtml(subtitle)}</p>
        ${isMicro ? `<p style="margin:0; color:var(--text-muted); font-size:0.75rem; opacity: 0.8;">ID: ${escapeHtml(String(displayId))}</p>` : ''}
        <hr style="border-color:var(--border-color); margin:8px 0;">
        <p style="margin:0; color:var(--text-muted); font-size:0.875rem;">${outputLabel}</p>
        ${disabledHoverMessage 
            ? `<div style="margin-top: 6px; padding: 6px 8px; background: rgba(255,255,255,0.1); border-radius: 4px;">
                 <p style="margin:0; color:var(--text-muted); font-size:0.875rem; font-style: italic;">${escapeHtml(disabledHoverMessage)}</p>
               </div>`
            : `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 6px;">
                <div>
                    <p style="margin:0; color:var(--text-muted); font-size:0.75rem;">Absolute</p>
                    <p style="margin:0; color:var(--text-main); font-size:1.125rem; font-weight:bold; white-space:nowrap;">${escapeHtml(displayRegionData)}</p>
                </div>
                <div>
                    <p style="margin:0; color:var(--text-muted); font-size:0.75rem;">Density</p>
                    <p style="margin:0; color:var(--text-main); font-size:1.125rem; font-weight:bold; white-space:nowrap;">${escapeHtml(displayNormalizedData)}</p>
                </div>
            </div>`
        }
        ${isDataUnavailable || disabledHoverMessage ? '' : `
        <hr style="border-color:var(--border-color); margin:8px 0;">
        <p style="margin:0; color:var(--text-muted); font-size:0.75rem; text-align: left; opacity: 0.8;">Source: ${escapeHtml(sourceLabel)}</p>
        ${generatedTime ? (() => {
            const date = new Date(generatedTime);
            const localStr = date.toLocaleString(undefined, { hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });
            
            let countryStr = '';
            if (config?.timeZone) {
                try {
                    const cStr = date.toLocaleString(undefined, { hour: '2-digit', minute: '2-digit', timeZoneName: 'short', timeZone: config.timeZone });
                    if (cStr !== localStr) {
                        countryStr = ` (${cStr})`;
                    }
                } catch (e) {
                    console.error("Invalid timezone:", config.timeZone, e);
                }
            }
            return `<p style="margin:0; color:var(--text-muted); font-size:0.75rem; text-align: left; opacity: 0.8;">Data generated: ${escapeHtml(localStr)}${escapeHtml(countryStr)}</p>`;
        })() : ''}`}
    </div>
  `
}
