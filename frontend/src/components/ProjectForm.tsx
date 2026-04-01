import { useState } from 'react'

export function ProjectForm({ onCreate }: { onCreate: (values: { name: string; description: string }) => Promise<void> }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    try {
      await onCreate({ name, description })
      setName('')
      setDescription('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="font-display text-2xl text-ink">Start a Project</h2>
          <p className="text-sm text-slate-600">Create an isolated workspace for uploads, rules, and classification runs.</p>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">
          Project name
          <input value={name} onChange={(e) => setName(e.target.value)} required className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none ring-ocean/20 focus:ring" />
        </label>
        <label className="text-sm font-medium text-slate-700 md:row-span-2">
          Description
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none ring-ocean/20 focus:ring" />
        </label>
      </div>
      <button type="submit" disabled={submitting} className="mt-5 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60">
        {submitting ? 'Creating...' : 'Create project'}
      </button>
    </form>
  )
}
