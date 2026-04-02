import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { ProjectForm } from '../components/ProjectForm'
import type { Project } from '../types'

export function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState('')

  async function loadProjects() {
    try {
      setProjects(await api.listProjects())
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects')
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  async function handleCreate(values: { name: string; description: string }) {
    try {
      await api.createProject(values)
      await loadProjects()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    }
  }

  async function handleDelete(projectId: number) {
    await api.deleteProject(projectId)
    await loadProjects()
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
      <ProjectForm onCreate={handleCreate} />
      <section className="theme-panel rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur transition-colors duration-300">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-2xl text-ink">Project Dashboard</h2>
            <p className="text-sm text-slate-600">Each project keeps datasets, rules, and classifications fully isolated.</p>
          </div>
        </div>
        {error && <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {projects.length === 0 && <p className="text-sm text-slate-500">No projects yet. Create one to start the shutdown prioritization flow.</p>}
          {projects.map((project) => (
            <article key={project.id} className="theme-card rounded-[1.5rem] border border-slate-200 bg-gradient-to-br from-white to-mist p-5 transition-colors duration-300">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-display text-xl text-ink">{project.name}</h3>
                  <p className="mt-2 text-sm text-slate-600">{project.description || 'No description yet.'}</p>
                  <p className="mt-3 text-xs uppercase tracking-[0.2em] text-slate-400">Created {new Date(project.created_at).toLocaleString()}</p>
                </div>
                <button onClick={() => handleDelete(project.id)} className="rounded-full bg-red-50 p-2 text-red-500 transition hover:bg-red-100">
                  <Trash2 size={16} />
                </button>
              </div>
              <Link to={`/projects/${project.id}`} className="mt-5 inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white">
                Open workspace
                <ArrowRight size={16} />
              </Link>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
