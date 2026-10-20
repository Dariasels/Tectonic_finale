// Accounts the visitor linked on the first page. Kept in the browser until sign-in completes, then saved to the profile.
const KEY = 'graphlas_connections'

export const getConnections = () => {
  try { return JSON.parse(localStorage.getItem(KEY)) ?? [] } catch { return [] }
}
export const setConnections = (list) => {
  try { localStorage.setItem(KEY, JSON.stringify(list)) } catch { /* private mode */ }
}
