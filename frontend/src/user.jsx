import { createContext, useContext, useEffect, useState } from 'react'
import { api } from './api'

const Ctx = createContext(null)
export const useUser = () => useContext(Ctx)

const load = () => {
  try { return JSON.parse(localStorage.getItem('tectonic_user')) } catch { return null }
}
const save = (u) => {
  try { localStorage.setItem('tectonic_user', JSON.stringify(u)) } catch { /* private mode */ }
}

export function UserProvider({ children }) {
  const [users, setUsers] = useState([])
  const [user, setUserState] = useState(load())
  const [error, setError] = useState(null)

  useEffect(() => {
    api.users().then((list) => {
      setUsers(list)
      // ids change when the data is regenerated: drop a stale saved user
      setUserState((cur) => (cur && list.some((u) => u.person_id === cur.person_id)) || (cur && cur.extra) ? cur : list[0] ?? null)
    }).catch(() => setError('Backend not reachable. Start it with ./dev.sh'))
  }, [])

  const setUser = (u) => { setUserState(u); save(u) }
  return <Ctx.Provider value={{ users, user, setUser, error }}>{children}</Ctx.Provider>
}
