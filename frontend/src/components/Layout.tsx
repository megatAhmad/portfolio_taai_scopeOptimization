import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Database, FolderKanban, Moon, Sun } from 'lucide-react'

export function Layout() {
  const location = useLocation()
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window === 'undefined') return false
    const stored = window.localStorage.getItem('scope-optimization-theme')
    if (stored === 'dark') return true
    if (stored === 'light') return false
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    window.localStorage.setItem('scope-optimization-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  return (
    <div className="theme-app-shell min-h-screen bg-grid bg-[size:32px_32px] transition-colors duration-300">
      <div className="mx-auto flex min-h-screen max-w-[1800px] flex-col px-4 py-6 sm:px-6 lg:px-8 xl:px-10">
        <header className="theme-panel mb-8 rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur transition-colors duration-300">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-display text-sm uppercase tracking-[0.35em] text-ocean">Shutdown Planning Platform</p>
              <h1 className="mt-2 font-display text-3xl text-ink md:text-4xl">Scope Optimization Workspace</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-600 md:text-base">
                Consolidate source data, generate derived evidence, and classify shutdown equipment with auditable rule trees.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setDarkMode((current) => !current)}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200"
              >
                {darkMode ? <Sun size={16} /> : <Moon size={16} />}
                {darkMode ? 'Light mode' : 'Dark mode'}
              </button>
              <Link
                to="/"
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${location.pathname === '/' ? 'bg-ink text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
              >
                <FolderKanban size={16} />
                Projects
              </Link>
              <a
                href="http://127.0.0.1:8000/api/health"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-full bg-sand px-4 py-2 text-sm font-semibold text-ember transition hover:bg-orange-100"
              >
                <Database size={16} />
                API Health
              </a>
            </div>
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  )
}
