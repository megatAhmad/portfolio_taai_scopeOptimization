import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Play, Sparkles, Trash2 } from 'lucide-react'
import { DatasetUploadForm } from '../components/DatasetUploadForm'
import { ResultsPanel } from '../components/ResultsPanel'
import { RuleBuilder } from '../components/RuleBuilder'
import { api } from '../lib/api'
import type { ClassificationResult, ProjectDetail, RuleSet } from '../types'

const PAGE_LIMIT = 100

export function ProjectPage() {
  const params = useParams()
  const projectId = Number(params.projectId)
  const [detail, setDetail] = useState<ProjectDetail | null>(null)
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)
  const [loadingResult, setLoadingResult] = useState(false)

  async function loadRunPage(runId: number, summary: Record<string, number>, rulesetVersion: number, offset = 0) {
    setLoadingResult(true)
    try {
      const page = await api.getClassificationRunRows(runId, offset, PAGE_LIMIT)
      setResult({
        run_id: runId,
        summary,
        rows: page.rows,
        columns: page.columns,
        ruleset_version: rulesetVersion,
        explanations: page.explanations,
        total_rows: page.total_rows,
        offset: page.offset,
        limit: page.limit,
      })
    } finally {
      setLoadingResult(false)
    }
  }

  async function loadProject() {
    try {
      const next = await api.getProjectDetail(projectId)
      setDetail(next)
      if (next.latest_run) {
        await loadRunPage(next.latest_run.id, next.latest_run.summary, next.latest_run.ruleset_version, 0)
      } else {
        setResult(null)
      }
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project')
    }
  }

  useEffect(() => {
    if (!Number.isNaN(projectId)) {
      setDetail(null)
      setResult(null)
      void loadProject()
    }
  }, [projectId])

  const availableColumns = useMemo(() => {
    const columns = new Set<string>()
    detail?.datasets.forEach((dataset) => dataset.mapping_rules.filter((entry) => entry.include).forEach((entry) => columns.add(entry.target)))
    detail?.datasets.forEach((dataset) => dataset.derived_columns.forEach((derived) => columns.add(derived.name)))
    return Array.from(columns)
  }, [detail])

  async function handleUpload(formData: FormData) {
    await api.uploadDataset(projectId, formData)
    await loadProject()
  }

  async function handleDeleteDataset(datasetId: number) {
    await api.deleteDataset(datasetId)
    await loadProject()
  }

  async function handleSaveRules(payload: { name: string; ast_json: RuleSet['ast_json'] }) {
    await api.saveRuleSet(projectId, payload)
    await loadProject()
  }

  async function handleRunClassification() {
    setRunning(true)
    try {
      setResult(await api.runClassification(projectId))
      await loadProject()
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to classify project')
    } finally {
      setRunning(false)
    }
  }

  async function handlePageChange(offset: number) {
    if (!detail?.latest_run) return
    await loadRunPage(detail.latest_run.id, detail.latest_run.summary, detail.latest_run.ruleset_version, offset)
  }

  if (!detail) {
    return <div className="rounded-[2rem] bg-white/80 p-6 shadow-panel">Loading project workspace...</div>
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.25em] text-ocean">Project workspace</p>
            <h2 className="mt-2 font-display text-3xl text-ink">{detail.project.name}</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">{detail.project.description || 'No description provided for this project yet.'}</p>
          </div>
          <button onClick={handleRunClassification} disabled={running || !detail.latest_ruleset || !detail.datasets.some((dataset) => dataset.role === 'canonical')} className="inline-flex items-center justify-center gap-2 rounded-full bg-pine px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
            <Play size={16} />
            {running ? 'Running classification...' : 'Run classification'}
          </button>
        </div>
        {error && <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}
      </section>

      <div className="grid gap-6 2xl:grid-cols-[1.1fr_0.9fr]">
        <DatasetUploadForm projectId={projectId} datasets={detail.datasets} onUpload={handleUpload} />
        <section className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
          <div className="flex items-center gap-3">
            <Sparkles size={18} className="text-ember" />
            <div>
              <h2 className="font-display text-2xl text-ink">Dataset Registry</h2>
              <p className="text-sm text-slate-600">Each dataset stores its inspected schema, mapping rules, and matching strategy for auditability.</p>
            </div>
          </div>
          <div className="mt-5 space-y-4">
            {detail.datasets.length === 0 && <p className="text-sm text-slate-500">No datasets uploaded yet.</p>}
            {detail.datasets.map((dataset) => (
              <article key={dataset.id} className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-ocean">{dataset.role}</span>
                      {dataset.sheet_name && <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-ember">Sheet: {dataset.sheet_name}</span>}
                      {dataset.role === 'supplementary' && <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-pine">{dataset.matching_config.strategy} match</span>}
                      {dataset.equipment_id_cleaning_config.enabled && <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-ink">ID cleaning on</span>}
                    </div>
                    <h3 className="mt-3 font-display text-xl text-ink">{dataset.name}</h3>
                    <p className="text-sm text-slate-600">{dataset.file_name}</p>
                    <p className="mt-1 text-xs text-slate-500">Source equipment ID: {dataset.equipment_id_column}{dataset.canonical_join_column ? ' • Canonical join: ' + dataset.canonical_join_column : ''}</p>
                  </div>
                  <button onClick={() => handleDeleteDataset(dataset.id)} className="rounded-full bg-red-50 p-2 text-red-500 transition hover:bg-red-100">
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-white p-3">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Mapped fields</div>
                    <div className="flex flex-wrap gap-2">{dataset.mapping_rules.filter((entry) => entry.include).map((entry) => <span key={entry.source} className="rounded-full bg-mist px-3 py-2 text-xs font-semibold text-ink">{entry.source} → {entry.target}</span>)}</div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white p-3">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Column profile</div>
                    <div className="space-y-2 text-sm text-slate-600">{dataset.schema_profile.slice(0, 4).map((profile) => <div key={profile.source}>{profile.source}: {profile.inferred_type} • {Math.round(profile.null_ratio * 100)}% null</div>)}</div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <RuleBuilder columns={availableColumns} existingRuleSet={detail.latest_ruleset} onSave={handleSaveRules} />
      <ResultsPanel result={result} loading={loadingResult} onPageChange={handlePageChange} />
    </div>
  )
}
