import { useEffect, useMemo, useState } from 'react'
import { ChevronRight, FileSpreadsheet, LoaderCircle, TableProperties, WandSparkles, X } from 'lucide-react'
import { api } from '../lib/api'
import type { Dataset, DatasetInspection, DerivedColumn, MappingEntry, MatchingConfig } from '../types'

const textOperators = ['=', '!=', 'CONTAINS', 'CONTAINS ANY', 'CONTAINS ALL', 'IN']
const rangeOperators = ['<', '>', '<=', '>=', 'BETWEEN']

function defaultMatchingConfig(): MatchingConfig {
  return { strategy: 'normalized', fuzzy_threshold: 0.82 }
}

function cloneSuggestions(suggestions: MappingEntry[]) {
  return suggestions.map((entry) => ({ ...entry }))
}

function getIncludedTargets(entries: MappingEntry[]) {
  return entries.filter((entry) => entry.include).map((entry) => entry.target.trim())
}

export function DatasetUploadForm({
  projectId,
  datasets,
  onUpload,
}: {
  projectId: number
  datasets: Dataset[]
  onUpload: (payload: FormData) => Promise<void>
}) {
  const canonicalDataset = datasets.find((dataset) => dataset.role === 'canonical')
  const canonicalTargets = useMemo(
    () => canonicalDataset?.mapping_rules.filter((entry) => entry.include).map((entry) => entry.target) ?? [],
    [canonicalDataset],
  )

  const [fileKey, setFileKey] = useState(0)
  const [file, setFile] = useState<File | null>(null)
  const [inspection, setInspection] = useState<DatasetInspection | null>(null)
  const [selectedSheet, setSelectedSheet] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState<'canonical' | 'supplementary'>('canonical')
  const [equipmentIdColumn, setEquipmentIdColumn] = useState('')
  const [joinColumn, setJoinColumn] = useState('')
  const [mappingEntries, setMappingEntries] = useState<MappingEntry[]>([])
  const [derivedColumns, setDerivedColumns] = useState<DerivedColumn[]>([])
  const [matchingConfig, setMatchingConfig] = useState<MatchingConfig>(defaultMatchingConfig())
  const [inspecting, setInspecting] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [sheetModalOpen, setSheetModalOpen] = useState(false)

  useEffect(() => {
    if (canonicalDataset) {
      setRole('supplementary')
    }
  }, [canonicalDataset])

  useEffect(() => {
    if (inspection?.columns.length) {
      setEquipmentIdColumn((current) => (current && inspection.columns.includes(current) ? current : inspection.columns[0]))
      if (role === 'supplementary') {
        setJoinColumn((current) => current || canonicalTargets[0] || canonicalDataset?.equipment_id_column || '')
      }
    }
  }, [inspection, role, canonicalTargets, canonicalDataset])

  async function inspectFile(nextFile: File, nextRole: 'canonical' | 'supplementary', sheetName?: string) {
    const formData = new FormData()
    formData.append('file', nextFile)
    formData.append('project_id', String(projectId))
    formData.append('role', nextRole)
    if (sheetName) {
      formData.append('sheet_name', sheetName)
    }

    setInspecting(true)
    setError('')
    try {
      const result = await api.inspectDataset(formData)
      setInspection(result)
      setMappingEntries(cloneSuggestions(result.mapping_suggestions))
      setEquipmentIdColumn('')
      if (sheetName) {
        setSelectedSheet(sheetName)
        setSheetModalOpen(false)
      } else if (result.file_type === 'excel') {
        setSelectedSheet('')
        setSheetModalOpen(true)
      }
    } catch (err) {
      setInspection(null)
      setMappingEntries([])
      setError(err instanceof Error ? err.message : 'Failed to inspect file')
    } finally {
      setInspecting(false)
    }
  }

  function resetStateAfterUpload() {
    setFile(null)
    setInspection(null)
    setSelectedSheet('')
    setName('')
    setEquipmentIdColumn('')
    setJoinColumn('')
    setMappingEntries([])
    setDerivedColumns([])
    setMatchingConfig(defaultMatchingConfig())
    setSheetModalOpen(false)
    setFileKey((current) => current + 1)
  }

  function resetPendingExcelSelection(message: string) {
    setFile(null)
    setInspection(null)
    setSelectedSheet('')
    setMappingEntries([])
    setEquipmentIdColumn('')
    setSheetModalOpen(false)
    setFileKey((current) => current + 1)
    setError(message)
  }

  function addDerivedColumn() {
    const defaultColumn = inspection?.columns[0] ?? equipmentIdColumn
    setDerivedColumns((current) => [
      ...current,
      {
        name: 'derived_' + (current.length + 1),
        true_value: 'Match',
        false_value: 'No Match',
        null_value: 'Unknown',
        conditions: [
          {
            column: defaultColumn,
            data_type: 'text',
            operator: 'CONTAINS',
            value: '',
          },
        ],
      },
    ])
  }

  function updateMapping(index: number, next: Partial<MappingEntry>) {
    setMappingEntries((current) => current.map((entry, entryIndex) => (entryIndex === index ? { ...entry, ...next } : entry)))
  }

  const validationErrors = useMemo(() => {
    if (!inspection || !inspection.columns.length) {
      return []
    }

    const errors: string[] = []
    const includedTargets = getIncludedTargets(mappingEntries)
    const targetCounts = includedTargets.reduce<Record<string, number>>((accumulator, target) => {
      accumulator[target] = (accumulator[target] || 0) + 1
      return accumulator
    }, {})

    if (!equipmentIdColumn) {
      errors.push('Select a source equipment ID column.')
    }

    const equipmentEntry = mappingEntries.find((entry) => entry.source === equipmentIdColumn)
    if (equipmentIdColumn && equipmentEntry && !equipmentEntry.include) {
      errors.push('The equipment ID column cannot be excluded from mapping.')
    }

    mappingEntries.forEach((entry) => {
      if (entry.include && !entry.target.trim()) {
        errors.push('Included columns need a mapped target name.')
      }
    })

    Object.entries(targetCounts).forEach(([target, count]) => {
      if (count > 1) {
        errors.push('Duplicate mapped target name: ' + target)
      }
    })

    if (role === 'supplementary' && !joinColumn) {
      errors.push('Select a canonical join column for supplementary uploads.')
    }

    if (inspection.file_type === 'excel' && !selectedSheet) {
      errors.push('Choose an Excel sheet before preview and upload.')
    }

    return Array.from(new Set(errors))
  }, [equipmentIdColumn, inspection, joinColumn, mappingEntries, role, selectedSheet])

  const canSubmit = Boolean(file && inspection && inspection.columns.length && validationErrors.length === 0 && !submitting)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!file || !inspection || !canSubmit) return

    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', name)
    formData.append('role', role)
    formData.append('equipment_id_column', equipmentIdColumn)
    formData.append('mapping_rules', JSON.stringify(mappingEntries))
    formData.append('derived_columns', JSON.stringify(derivedColumns))
    formData.append('matching_config', JSON.stringify(matchingConfig))
    if (inspection.file_type === 'excel') {
      formData.append('sheet_name', selectedSheet)
    }
    if (role === 'supplementary') {
      formData.append('canonical_join_column', joinColumn)
    }

    setSubmitting(true)
    setError('')
    try {
      await onUpload(formData)
      resetStateAfterUpload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload dataset')
    } finally {
      setSubmitting(false)
    }
  }

  const readyForPreview = Boolean(inspection && inspection.columns.length > 0)
  const workbookOnly = Boolean(inspection && inspection.file_type === 'excel' && inspection.columns.length === 0)

  return (
    <>
      <form onSubmit={handleSubmit} className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="font-display text-2xl text-ink">Guided Dataset Intake</h2>
            <p className="text-sm text-slate-600">Inspect files, choose Excel sheets, map columns visually, and configure derived evidence before upload.</p>
          </div>
          <div className="rounded-full bg-mist px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-ocean">Project #{projectId}</div>
        </div>

        {error && <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">
            Dataset label
            <input required value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Role
            <select
              value={role}
              onChange={async (event) => {
                const nextRole = event.target.value as 'canonical' | 'supplementary'
                setRole(nextRole)
                if (file) {
                  await inspectFile(file, nextRole, selectedSheet || undefined)
                }
              }}
              className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3"
            >
              <option value="canonical" disabled={Boolean(canonicalDataset)}>Canonical</option>
              <option value="supplementary">Supplementary</option>
            </select>
          </label>
          <label className="text-sm font-medium text-slate-700 md:col-span-2">
            File
            <input
              key={fileKey}
              required
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={async (event) => {
                const nextFile = event.target.files?.[0] ?? null
                setFile(nextFile)
                setInspection(null)
                setSelectedSheet('')
                setMappingEntries([])
                setEquipmentIdColumn('')
                setJoinColumn('')
                if (nextFile) {
                  await inspectFile(nextFile, role)
                }
              }}
              className="mt-2 w-full rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3"
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Source equipment ID column
            <select value={equipmentIdColumn} onChange={(event) => setEquipmentIdColumn(event.target.value)} disabled={!readyForPreview} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 disabled:bg-slate-100">
              <option value="">Select a column</option>
              {inspection?.columns.map((column) => (
                <option key={column} value={column}>{column}</option>
              ))}
            </select>
          </label>
          {role === 'supplementary' && (
            <label className="text-sm font-medium text-slate-700">
              Canonical join column
              <select value={joinColumn} onChange={(event) => setJoinColumn(event.target.value)} disabled={!canonicalTargets.length} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 disabled:bg-slate-100">
                <option value="">Select canonical join</option>
                {canonicalTargets.map((column) => (
                  <option key={column} value={column}>{column}</option>
                ))}
              </select>
            </label>
          )}
        </div>

        {inspecting && (
          <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-mist px-4 py-2 text-sm text-ocean">
            <LoaderCircle size={16} className="animate-spin" />
            Inspecting dataset schema...
          </div>
        )}

        {workbookOnly && (
          <section className="mt-6 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
            <h3 className="font-display text-lg text-ink">Workbook Detected</h3>
            <p className="mt-2 text-sm text-slate-600">Preview, mapping, and upload stay blocked until you explicitly choose one sheet.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {inspection?.sheet_names.map((sheet) => (
                <span key={sheet} className="rounded-full bg-white px-3 py-2 text-xs font-semibold text-slate-600">{sheet}</span>
              ))}
            </div>
          </section>
        )}

        {validationErrors.length > 0 && readyForPreview && (
          <div className="mt-4 rounded-[1.5rem] border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <div className="font-semibold">Fix before upload</div>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {validationErrors.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        )}

        {readyForPreview && inspection && (
          <div className="mt-6 space-y-6">
            <section className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h3 className="font-display text-lg text-ink">Inspection Summary</h3>
                  <p className="text-sm text-slate-600">{inspection.file_name}{selectedSheet ? ' • Sheet ' + selectedSheet : ''}</p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  <span className="rounded-full bg-white px-3 py-2">{inspection.file_type}</span>
                  <span className="rounded-full bg-white px-3 py-2">{inspection.columns.length} columns</span>
                </div>
              </div>
              <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-100 text-left text-slate-600">
                    <tr>
                      {inspection.columns.map((column) => <th key={column} className="px-3 py-2 font-semibold">{column}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {inspection.preview_rows.map((row, rowIndex) => (
                      <tr key={rowIndex} className="border-t border-slate-100">
                        {inspection.columns.map((column) => <td key={column} className="px-3 py-2">{String(row[column] ?? '')}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {inspection.file_type === 'excel' && (
                <button type="button" onClick={() => setSheetModalOpen(true)} className="mt-4 rounded-full bg-white px-4 py-2 text-sm font-semibold text-ocean">Change sheet</button>
              )}
            </section>

            <section className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-3">
                <TableProperties size={18} className="text-ocean" />
                <div>
                  <h3 className="font-display text-lg text-ink">Schema Mapping Grid</h3>
                  <p className="text-sm text-slate-600">Map source columns to canonical-friendly names without writing JSON.</p>
                </div>
              </div>
              <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-100 text-left text-slate-600">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Include</th>
                      <th className="px-3 py-2 font-semibold">Source</th>
                      <th className="px-3 py-2 font-semibold">Target</th>
                      <th className="px-3 py-2 font-semibold">Type</th>
                      <th className="px-3 py-2 font-semibold">Suggested</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mappingEntries.map((entry, index) => (
                      <tr key={entry.source} className="border-t border-slate-100">
                        <td className="px-3 py-2"><input type="checkbox" checked={entry.include} onChange={(event) => updateMapping(index, { include: event.target.checked })} /></td>
                        <td className="px-3 py-2 font-medium text-slate-700">{entry.source}</td>
                        <td className="px-3 py-2"><input value={entry.target} onChange={(event) => updateMapping(index, { target: event.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2" /></td>
                        <td className="px-3 py-2 text-slate-600">{inspection.schema_profile.find((profile) => profile.source === entry.source)?.inferred_type ?? entry.inferred_type}</td>
                        <td className="px-3 py-2 text-slate-500">{entry.suggested_target ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-3">
                <WandSparkles size={18} className="text-ember" />
                <div>
                  <h3 className="font-display text-lg text-ink">Derived Columns</h3>
                  <p className="text-sm text-slate-600">Create typed fallback labels before the classification rules run.</p>
                </div>
              </div>
              <button type="button" onClick={addDerivedColumn} className="mt-4 rounded-full bg-white px-4 py-2 text-sm font-semibold text-ocean">Add derived column</button>
              <div className="mt-4 space-y-4">
                {derivedColumns.length === 0 && <p className="text-sm text-slate-500">No derived columns configured yet.</p>}
                {derivedColumns.map((derived, derivedIndex) => (
                  <div key={derivedIndex} className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="grid gap-3 md:grid-cols-2">
                      <input value={derived.name} onChange={(event) => {
                        const next = [...derivedColumns]
                        next[derivedIndex].name = event.target.value
                        setDerivedColumns(next)
                      }} placeholder="Derived column name" className="rounded-2xl border border-slate-200 px-4 py-3" />
                      <input value={derived.true_value} onChange={(event) => {
                        const next = [...derivedColumns]
                        next[derivedIndex].true_value = event.target.value
                        setDerivedColumns(next)
                      }} placeholder="True value" className="rounded-2xl border border-slate-200 px-4 py-3" />
                      <input value={derived.false_value ?? ''} onChange={(event) => {
                        const next = [...derivedColumns]
                        next[derivedIndex].false_value = event.target.value
                        setDerivedColumns(next)
                      }} placeholder="False value" className="rounded-2xl border border-slate-200 px-4 py-3" />
                      <input value={derived.null_value ?? ''} onChange={(event) => {
                        const next = [...derivedColumns]
                        next[derivedIndex].null_value = event.target.value
                        setDerivedColumns(next)
                      }} placeholder="Null value" className="rounded-2xl border border-slate-200 px-4 py-3" />
                    </div>
                    {derived.conditions.map((condition, conditionIndex) => {
                      const operators = condition.data_type === 'text' ? textOperators : rangeOperators
                      return (
                        <div key={conditionIndex} className="mt-3 grid gap-3 md:grid-cols-5">
                          <select value={condition.column} onChange={(event) => {
                            const next = [...derivedColumns]
                            next[derivedIndex].conditions[conditionIndex].column = event.target.value
                            setDerivedColumns(next)
                          }} className="rounded-2xl border border-slate-200 px-4 py-3">
                            {inspection.columns.map((column) => <option key={column} value={column}>{column}</option>)}
                          </select>
                          <select value={condition.data_type} onChange={(event) => {
                            const next = [...derivedColumns]
                            next[derivedIndex].conditions[conditionIndex].data_type = event.target.value as 'text' | 'numeric' | 'date'
                            next[derivedIndex].conditions[conditionIndex].operator = event.target.value === 'text' ? 'CONTAINS' : '>'
                            setDerivedColumns(next)
                          }} className="rounded-2xl border border-slate-200 px-4 py-3">
                            <option value="text">Text</option>
                            <option value="numeric">Numeric</option>
                            <option value="date">Date</option>
                          </select>
                          <select value={condition.operator} onChange={(event) => {
                            const next = [...derivedColumns]
                            next[derivedIndex].conditions[conditionIndex].operator = event.target.value
                            setDerivedColumns(next)
                          }} className="rounded-2xl border border-slate-200 px-4 py-3">
                            {operators.map((operator) => <option key={operator} value={operator}>{operator}</option>)}
                          </select>
                          <input value={condition.value ?? ''} onChange={(event) => {
                            const next = [...derivedColumns]
                            next[derivedIndex].conditions[conditionIndex].value = event.target.value
                            setDerivedColumns(next)
                          }} placeholder="Value" className="rounded-2xl border border-slate-200 px-4 py-3" />
                          <input value={condition.secondary_value ?? ''} onChange={(event) => {
                            const next = [...derivedColumns]
                            next[derivedIndex].conditions[conditionIndex].secondary_value = event.target.value
                            setDerivedColumns(next)
                          }} placeholder="Second value" className="rounded-2xl border border-slate-200 px-4 py-3" />
                        </div>
                      )
                    })}
                  </div>
                ))}
              </div>
            </section>

            {role === 'supplementary' && (
              <section className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center gap-3">
                  <FileSpreadsheet size={18} className="text-pine" />
                  <div>
                    <h3 className="font-display text-lg text-ink">Matching Strategy</h3>
                    <p className="text-sm text-slate-600">Choose how messy equipment IDs should be matched to canonical rows.</p>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="text-sm font-medium text-slate-700">
                    Strategy
                    <select value={matchingConfig.strategy} onChange={(event) => setMatchingConfig((current) => ({ ...current, strategy: event.target.value as MatchingConfig['strategy'] }))} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3">
                      <option value="exact">Exact</option>
                      <option value="normalized">Normalized</option>
                      <option value="fuzzy">Fuzzy</option>
                    </select>
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Fuzzy threshold
                    <input type="number" min="0.5" max="1" step="0.01" value={matchingConfig.fuzzy_threshold} onChange={(event) => setMatchingConfig((current) => ({ ...current, fuzzy_threshold: Number(event.target.value) }))} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
                  </label>
                </div>
              </section>
            )}
          </div>
        )}

        <button type="submit" disabled={!canSubmit} className="mt-6 inline-flex items-center gap-2 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
          <ChevronRight size={16} />
          {submitting ? 'Uploading...' : 'Upload dataset'}
        </button>
      </form>

      {sheetModalOpen && file && inspection?.file_type === 'excel' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <div className="w-full max-w-2xl rounded-[2rem] bg-white p-6 shadow-panel">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.25em] text-ocean">Excel sheet required</p>
                <h3 className="mt-2 font-display text-2xl text-ink">Select the sheet to ingest</h3>
                <p className="mt-2 text-sm text-slate-600">No schema preview is shown until a sheet is explicitly selected.</p>
              </div>
              <button type="button" onClick={() => resetPendingExcelSelection('Excel selection canceled. Choose the file again to continue.')} className="rounded-full bg-slate-100 p-2 text-slate-500">
                <X size={16} />
              </button>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {inspection.sheet_names.map((sheet) => (
                <button
                  key={sheet}
                  type="button"
                  onClick={async () => {
                    await inspectFile(file, role, sheet)
                  }}
                  className={'rounded-2xl border px-4 py-4 text-left transition ' + (selectedSheet === sheet ? 'border-ocean bg-mist' : 'border-slate-200 bg-white hover:border-slate-300')}
                >
                  <div className="font-semibold text-ink">{sheet}</div>
                  <div className="mt-1 text-sm text-slate-500">Use this sheet for preview, mapping, and ingestion.</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
