// Page background: white (default) or a soft light green. Cards stay white. Dark mode keeps its own colours.
// The colours are set from JavaScript as well as CSS, so it works in every browser.
const KEY = 'graphlas_bg'
const GREEN = { '--page': '#e2f2e7', '--soft': '#d3e9da', '--line': '#c2dac9' }

const isDark = () => window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches

const paint = (v) => {
  const root = document.documentElement
  root.dataset.bg = v
  for (const [k, c] of Object.entries(GREEN)) {
    if (v === 'green' && !isDark()) root.style.setProperty(k, c)
    else root.style.removeProperty(k)
  }
}

export const getBg = () => {
  try { return localStorage.getItem(KEY) === 'green' ? 'green' : 'white' } catch { return 'white' }
}
export const setBg = (v) => {
  paint(v)
  try { localStorage.setItem(KEY, v) } catch { /* private mode */ }
}
export const applyBg = () => {
  const q = new URLSearchParams(window.location.search).get('bg')      // ?bg=green or ?bg=white also sets it
  if (q === 'green' || q === 'white') setBg(q)
  else paint(getBg())
}
