// Page colours: white (default, whatever the computer is set to), soft light green, or dark.
// Colours are set from JavaScript, so the choice works in every browser and ignores the system light/dark setting.
const KEY = 'graphlas_bg'
const GREEN = { '--page': '#e2f2e7', '--soft': '#d3e9da', '--line': '#c2dac9' }
const DARK = {
  '--page': '#0f0e1a', '--surface': '#1a1830', '--main': '#f1eef8', '--muted': '#a9a3c2', '--line': '#2c2850', '--soft': '#221f3d',
  '--accent': '#c79bff', '--ok-text': '#5fd39a', '--ok-bg': '#12301f', '--warn-text': '#f2c94c', '--warn-bg': '#3a3010',
  '--bad-text': '#ff8a8b', '--bad-bg': '#3b1618',
}
const ALL = [...new Set([...Object.keys(GREEN), ...Object.keys(DARK)])]
const MODES = ['white', 'green', 'dark']

const paint = (mode) => {
  const root = document.documentElement
  root.dataset.bg = mode
  root.style.colorScheme = mode === 'dark' ? 'dark' : 'light'
  const palette = mode === 'green' ? GREEN : mode === 'dark' ? DARK : {}
  for (const k of ALL) {
    if (palette[k]) root.style.setProperty(k, palette[k])
    else root.style.removeProperty(k)
  }
}

export const getBg = () => {
  try { const v = localStorage.getItem(KEY); return MODES.includes(v) ? v : 'white' } catch { return 'white' }
}
export const setBg = (v) => {
  paint(v)
  try { localStorage.setItem(KEY, v) } catch { /* private mode */ }
}
export const applyBg = () => {
  const q = new URLSearchParams(window.location.search).get('bg')      // ?bg=green, ?bg=white or ?bg=dark also sets it
  if (MODES.includes(q)) setBg(q)
  else paint(getBg())
}
