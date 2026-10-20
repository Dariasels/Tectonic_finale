// Page background: white (default) or a soft light green. Cards stay white. Dark mode is not affected.
const KEY = 'graphlas_bg'

export const getBg = () => {
  try { return localStorage.getItem(KEY) === 'green' ? 'green' : 'white' } catch { return 'white' }
}
export const setBg = (v) => {
  document.documentElement.dataset.bg = v
  try { localStorage.setItem(KEY, v) } catch { /* private mode */ }
}
export const applyBg = () => {
  const q = new URLSearchParams(window.location.search).get('bg')      // ?bg=green or ?bg=white also sets it
  if (q === 'green' || q === 'white') setBg(q)
  else document.documentElement.dataset.bg = getBg()
}
