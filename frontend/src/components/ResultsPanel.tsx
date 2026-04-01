import { useEffect, useMemo, useState } from 'react'
import { Download, Eye, GaugeCircle } from 'lucide-react'
import { api } from '../lib/api'
import type { ClassificationResult, GroupTrace, TraceNode } from '../types'

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value) || (typeof value === 'object' && value !== null)) {
    return JSON.stringify(value)
  }
  return String(value)
}

function renderTrace(node: TraceNode): JSX.Element {
  if ('children' in node) {
    const group = node as GroupTrace
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
        <div className="text-sm font-semibold text-ink">Group {group.node_id} • {group.combinator} • {group.result ? 'Passed' : 'Failed'}</div>
        <div className="mt-3 space-y-2">{group.children.map((child) => <div key={child.node_id}>{renderTrace(child)}</div>)}</div>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 text-sm">
      <div className="font-semibold text-ink">{node.field} {node.operator}</div>
      <div className="mt-1 text-slate-600">Actual: {formatValue(node.actual_value)}</div>
      <div className="text-slate-600">Expected: {formatValue(node.expected_value)}{node.secondary_value ? ' / ' + formatValue(node.secondary_value) : ''}</div>
      <div className={'mt-2 inline-flex rounded-full px-3 py-1 text-xs font-semibold ' + (node.result ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700')}>
        {node.result === null ? 'Null' : node.result ? 'Matched' : 'Not matched'}
      </div>
    </div>
  )
}

export function ResultsPanel({ result, loading, onPageChange }: { result: ClassificationResult | null; loading?: boolean; onPageChange?: (offset: number) => Promise<void> | void }) {
  const [selectedExplanationIndex, setSelectedExplanationIndex] = useState(0)
  const [visibleColumns, setVisibleColumns] = useState<string[]>([])

  useEffect(() => {
    setSelectedExplanationIndex(0)
  }, [result?.run_id, result?.offset])

  useEffect(() => {
    setVisibleColumns(result?.columns ?? [])
  }, [result?.run_id, result?.columns])

  const explanation = result?.explanations[selectedExplanationIndex] ?? null
  const confidenceColumns = useMemo(() => result?.columns.filter((column) => column.endsWith('__match_confidence')) ?? [], [result])
  const selectedRow = result?.rows[selectedExplanationIndex] ?? null
  const evidenceKeys = useMemo(() => Object.keys(selectedRow ?? {}).filter((key) => key.endsWith('__evidence_rows')), [selectedRow])
  const pageStart = result ? result.offset + 1 : 0
  const pageEnd = result ? Math.min(result.offset + result.rows.length, result.total_rows) : 0
  const displayedColumns = useMemo(
    () => result?.columns.filter((column) => visibleColumns.includes(column)) ?? [],
    [result?.columns, visibleColumns],
  )

  if (!result) {
    return (
      <section className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
        <h2 className="font-display text-2xl text-ink">Classification Output</h2>
        <p className="mt-2 text-sm text-slate-600">Run a classification to generate the decision matrix, evidence trace, and exportable results.</p>
      </section>
    )
  }

  return (
    <section className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h2 className="font-display text-2xl text-ink">Classification Output</h2>
          <p className="text-sm text-slate-600">Run #{result.run_id} used ruleset version {result.ruleset_version}.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {Object.entries(result.summary).map(([label, count]) => (
            <div key={label} className="rounded-full bg-mist px-4 py-2 text-sm font-semibold text-ink">{label}: {count}</div>
          ))}
          <a href={api.exportClassificationRunUrl(result.run_id)} className="inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white">
            <Download size={16} /> Export CSV
          </a>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
        <div>{loading ? 'Loading run page...' : 'Showing ' + pageStart + ' to ' + pageEnd + ' of ' + result.total_rows + ' rows'}</div>
        <div className="flex gap-2">
          <button type="button" onClick={() => onPageChange?.(Math.max(result.offset - result.limit, 0))} disabled={loading || result.offset === 0} className="rounded-full border border-slate-200 px-3 py-2 font-semibold text-slate-700 disabled:opacity-50">Previous</button>
          <button type="button" onClick={() => onPageChange?.(result.offset + result.limit)} disabled={loading || result.offset + result.limit >= result.total_rows} className="rounded-full border border-slate-200 px-3 py-2 font-semibold text-slate-700 disabled:opacity-50">Next</button>
        </div>
      </div>

      <div className="mt-4 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-semibold text-ink">Visible columns</p>
            <p className="text-sm text-slate-600">Tick the columns you want to keep in the classification table.</p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setVisibleColumns(result.columns)}
              className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
            >
              Show all
            </button>
            <button
              type="button"
              onClick={() => setVisibleColumns([])}
              className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
            >
              Hide all
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {result.columns.map((column) => {
            const checked = visibleColumns.includes(column)
            return (
              <label key={column} className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm ${checked ? 'border-ocean bg-mist text-ink' : 'border-slate-200 bg-white text-slate-600'}`}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => {
                    setVisibleColumns((current) => (
                      event.target.checked
                        ? [...current, column]
                        : current.filter((item) => item !== column)
                    ))
                  }}
                />
                {column}
              </label>
            )
          })}
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="overflow-x-auto rounded-[1.5rem] border border-slate-200">
          <table className="min-w-full border-collapse text-sm">
            <thead className="bg-slate-100 text-left text-slate-600">
              <tr>
                <th className="px-4 py-3 font-semibold">Explain</th>
                {displayedColumns.map((column) => <th key={column} className="px-4 py-3 font-semibold">{column}</th>)}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row, index) => (
                <tr key={result.offset + index} className="border-t border-slate-100 align-top odd:bg-white even:bg-slate-50/50">
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => setSelectedExplanationIndex(index)} className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">
                      <Eye size={14} /> Trace
                    </button>
                  </td>
                  {displayedColumns.map((column) => (
                    <td key={column} className="max-w-[20rem] px-4 py-3 text-slate-700">{formatValue(row[column])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
          {explanation ? (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-ocean"><GaugeCircle size={16} /> Evidence Trace</div>
              <h3 className="mt-3 font-display text-xl text-ink">{explanation.equipment_id || 'Selected row'}</h3>
              <div className="mt-3 space-y-2 text-sm text-slate-600">
                <div>Classification: <span className="font-semibold text-ink">{explanation.classification}</span></div>
                <div>Matched rule: <span className="font-semibold text-ink">{explanation.matched_rule}</span></div>
                <div>Rule path: <span className="font-semibold text-ink">{explanation.rule_path.join(' > ') || 'Fallback'}</span></div>
                <div>Source fields: <span className="font-semibold text-ink">{explanation.source_fields.join(', ') || 'None recorded'}</span></div>
                {confidenceColumns.length > 0 && (
                  <div>Confidence: <span className="font-semibold text-ink">{confidenceColumns.map((column) => formatValue(result.rows[selectedExplanationIndex]?.[column])).filter(Boolean).join(', ') || 'N/A'}</span></div>
                )}
              </div>
              {evidenceKeys.length > 0 && selectedRow && (
                <div className="mt-4 space-y-3">
                  {evidenceKeys.map((key) => (
                    <div key={key} className="rounded-2xl border border-slate-200 bg-white p-3">
                      <div className="text-sm font-semibold text-ink">{key.replace('__evidence_rows', '')} evidence</div>
                      <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-slate-600">{formatValue(selectedRow[key])}</pre>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-4 space-y-3">{renderTrace(explanation.condition_trace)}</div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Select a row to inspect its rule lineage and evidence.</p>
          )}
        </div>
      </div>
    </section>
  )
}
