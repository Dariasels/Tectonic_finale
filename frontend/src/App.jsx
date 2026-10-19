import { useEffect, useState } from 'react'
import axios from 'axios'

export default function App() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    axios.get('/api/health')
      .then((r) => setStatus(r.data.status))
      .catch(() => setStatus('backend unreachable'))
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
      <div className="text-center">
        <h1 className="text-4xl font-bold">Tectonic</h1>
        <p className="mt-2 text-slate-400">Backend: {status}</p>
      </div>
    </div>
  )
}
