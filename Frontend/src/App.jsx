import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Auth from './pages/Auth'
import Chat from './pages/Chat'
import { getUser } from './services/api'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [sessionLoading, setSessionLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    const restoreSession = async () => {
      const stored = localStorage.getItem('cortex_user')
      if (!stored) {
        setSessionLoading(false)
        return
      }

      try {
        const savedUser = JSON.parse(stored)
        if (!savedUser?.id) throw new Error('Saved user is invalid')

        if (!localStorage.getItem('cortex_token')) throw new Error('Saved session is missing its token')
        const currentUser = await getUser()
        if (cancelled) return

        setUser(currentUser)
        localStorage.setItem('cortex_user', JSON.stringify(currentUser))
      } catch {
        if (!cancelled) {
          localStorage.removeItem('cortex_user')
          localStorage.removeItem('cortex_token')
          setUser(null)
        }
      } finally {
        if (!cancelled) setSessionLoading(false)
      }
    }

    restoreSession()
    return () => { cancelled = true }
  }, [])

  const handleAuth = (authData) => {
    setUser(authData.user)
    localStorage.setItem('cortex_token', authData.access_token)
    localStorage.setItem('cortex_user', JSON.stringify(authData.user))
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('cortex_user')
    localStorage.removeItem('cortex_token')
  }

  if (sessionLoading) {
    return <div className="app-loading" role="status">Checking your session...</div>
  }

  return (
    <Router>
      <Routes>
        <Route path="/auth" element={user ? <Navigate to="/" /> : <Auth onAuth={handleAuth} />} />
        <Route path="/" element={user ? <Chat user={user} setUser={setUser} onLogout={handleLogout} /> : <Navigate to="/auth" />} />
      </Routes>
    </Router>
  )
}

export default App
