import { useEffect, useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, FolderTree, Plus, Trash2 } from 'lucide-react'
import type { RuleAst, RuleConditionNode, RuleGroupNode, RuleNode, RuleSet } from '../types'

const textOperators = ['=', '!=', 'CONTAINS', 'CONTAINS ANY', 'CONTAINS ALL', 'IN']
const rangeOperators = ['<', '>', '<=', '>=', 'BETWEEN']

function createId() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `node_${Math.random().toString(36).slice(2, 10)}`
}

function createCondition(field: string): RuleConditionNode {
  return {
    id: createId(),
    type: 'condition',
    field,
    data_type: 'text',
    operator: 'CONTAINS',
    value: '',
    secondary_value: '',
  }
}

function createGroup(): RuleGroupNode {
  return { id: createId(), type: 'group', combinator: 'AND', children: [] }
}

function mutateTree(root: RuleGroupNode, targetId: string, updater: (node: RuleGroupNode) => RuleGroupNode): RuleGroupNode {
  if (root.id === targetId) {
    return updater(root)
  }
  return {
    ...root,
    children: root.children.map((child) => {
      if (child.type === 'group') {
        return mutateTree(child, targetId, updater)
      }
      return child
    }),
  }
}

function mutateNode(root: RuleGroupNode, targetId: string, updater: (node: RuleNode) => RuleNode): RuleGroupNode {
  return {
    ...root,
    children: root.children.map((child) => {
      if (child.id === targetId) {
        return updater(child)
      }
      if (child.type === 'group') {
        return mutateNode(child, targetId, updater)
      }
      return child
    }),
  }
}

function removeNode(root: RuleGroupNode, targetId: string): RuleGroupNode {
  return {
    ...root,
    children: root.children
      .filter((child) => child.id !== targetId)
      .map((child) => (child.type === 'group' ? removeNode(child, targetId) : child)),
  }
}

function moveNode(root: RuleGroupNode, parentId: string, index: number, direction: -1 | 1): RuleGroupNode {
  return mutateTree(root, parentId, (node) => {
    const next = [...node.children]
    const swapIndex = index + direction
    if (swapIndex < 0 || swapIndex >= next.length) {
      return node
    }
    ;[next[index], next[swapIndex]] = [next[swapIndex], next[index]]
    return { ...node, children: next }
  })
}

function RuleNodeEditor({
  node,
  parentId,
  index,
  columns,
  onTreeChange,
  tree,
}: {
  node: RuleNode
  parentId: string
  index: number
  columns: string[]
  onTreeChange: (next: RuleGroupNode) => void
  tree: RuleGroupNode
}) {
  if (node.type === 'condition') {
    const operators = node.data_type === 'text' ? textOperators : rangeOperators
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="mb-3 flex justify-end gap-2">
          <button type="button" onClick={() => onTreeChange(moveNode(tree, parentId, index, -1))} className="rounded-full bg-slate-100 p-2 text-slate-500"><ArrowUp size={14} /></button>
          <button type="button" onClick={() => onTreeChange(moveNode(tree, parentId, index, 1))} className="rounded-full bg-slate-100 p-2 text-slate-500"><ArrowDown size={14} /></button>
          <button type="button" onClick={() => onTreeChange(removeNode(tree, node.id))} className="rounded-full bg-red-50 p-2 text-red-500"><Trash2 size={14} /></button>
        </div>
        <div className="grid gap-3 md:grid-cols-5">
          <select value={node.field} onChange={(event) => onTreeChange(mutateNode(tree, node.id, (current) => ({ ...current, field: event.target.value } as RuleConditionNode)))} className="rounded-2xl border border-slate-200 px-4 py-3">
            {columns.map((column) => <option key={column} value={column}>{column}</option>)}
          </select>
          <select value={node.data_type} onChange={(event) => {
            const dataType = event.target.value as 'text' | 'numeric' | 'date'
            onTreeChange(mutateNode(tree, node.id, (current) => ({
              ...(current as RuleConditionNode),
              data_type: dataType,
              operator: dataType === 'text' ? 'CONTAINS' : '>',
            })))
          }} className="rounded-2xl border border-slate-200 px-4 py-3">
            <option value="text">Text</option>
            <option value="numeric">Numeric</option>
            <option value="date">Date</option>
          </select>
          <select value={node.operator} onChange={(event) => onTreeChange(mutateNode(tree, node.id, (current) => ({ ...(current as RuleConditionNode), operator: event.target.value })))} className="rounded-2xl border border-slate-200 px-4 py-3">
            {operators.map((operator) => <option key={operator} value={operator}>{operator}</option>)}
          </select>
          <input value={node.value ?? ''} onChange={(event) => onTreeChange(mutateNode(tree, node.id, (current) => ({ ...(current as RuleConditionNode), value: event.target.value })))} placeholder="Value" className="rounded-2xl border border-slate-200 px-4 py-3" />
          <input value={node.secondary_value ?? ''} onChange={(event) => onTreeChange(mutateNode(tree, node.id, (current) => ({ ...(current as RuleConditionNode), secondary_value: event.target.value })))} placeholder="Second value" className="rounded-2xl border border-slate-200 px-4 py-3" />
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 p-4">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="rounded-full bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-ocean">Group</div>
        <select value={node.combinator} onChange={(event) => onTreeChange(mutateTree(tree, node.id, (current) => ({ ...current, combinator: event.target.value as 'AND' | 'OR' })))} className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
        <button type="button" onClick={() => onTreeChange(mutateTree(tree, node.id, (current) => ({ ...current, children: [...current.children, createCondition(columns[0] ?? '')] })))} className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-ocean">
          <Plus size={14} className="inline-block" /> Condition
        </button>
        <button type="button" onClick={() => onTreeChange(mutateTree(tree, node.id, (current) => ({ ...current, children: [...current.children, createGroup()] })))} className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-ember">
          <Plus size={14} className="inline-block" /> Group
        </button>
        {parentId && (
          <>
            <button type="button" onClick={() => onTreeChange(moveNode(tree, parentId, index, -1))} className="rounded-full bg-slate-100 p-2 text-slate-500"><ArrowUp size={14} /></button>
            <button type="button" onClick={() => onTreeChange(moveNode(tree, parentId, index, 1))} className="rounded-full bg-slate-100 p-2 text-slate-500"><ArrowDown size={14} /></button>
            <button type="button" onClick={() => onTreeChange(removeNode(tree, node.id))} className="rounded-full bg-red-50 p-2 text-red-500"><Trash2 size={14} /></button>
          </>
        )}
      </div>
      <div className="space-y-3">
        {node.children.length === 0 && <p className="text-sm text-slate-500">Add nested groups or conditions to build the AST.</p>}
        {node.children.map((child, childIndex) => (
          <RuleNodeEditor key={child.id} node={child} parentId={node.id} index={childIndex} columns={columns} onTreeChange={onTreeChange} tree={tree} />
        ))}
      </div>
    </div>
  )
}

export function RuleBuilder({
  columns,
  existingRuleSet,
  onSave,
}: {
  columns: string[]
  existingRuleSet: RuleSet | null
  onSave: (payload: { name: string; ast_json: RuleAst }) => Promise<void>
}) {
  const defaultRules = useMemo<RuleAst>(() => ({ must_have: createGroup(), good_to_have: createGroup(), fallback_label: 'Not Needed' }), [])
  const [name, setName] = useState(existingRuleSet?.name ?? 'Default Rule Set')
  const [rules, setRules] = useState<RuleAst>(existingRuleSet?.ast_json ?? defaultRules)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (existingRuleSet) {
      setName(existingRuleSet.name)
      setRules(existingRuleSet.ast_json)
    }
  }, [existingRuleSet])

  async function handleSave() {
    setSaving(true)
    try {
      await onSave({ name, ast_json: rules })
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-mist px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-ocean">
            <FolderTree size={14} />
            Nested AST Rule Builder
          </div>
          <h2 className="mt-3 font-display text-2xl text-ink">Visual Classification Logic</h2>
          <p className="text-sm text-slate-600">Compose nested groups with AND/OR combinators and keep the AST synchronized with the backend.</p>
        </div>
        <div className="flex flex-col gap-3 md:items-end">
          <input value={name} onChange={(event) => setName(event.target.value)} className="rounded-full border border-slate-200 px-4 py-3" />
          <input value={rules.fallback_label} onChange={(event) => setRules((current) => ({ ...current, fallback_label: event.target.value }))} className="rounded-full border border-slate-200 px-4 py-3" placeholder="Fallback label" />
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <div>
          <h3 className="mb-3 font-display text-lg text-ink">Must Have</h3>
          <RuleNodeEditor node={rules.must_have} parentId="" index={0} columns={columns.length ? columns : ['classification']} onTreeChange={(next) => setRules((current) => ({ ...current, must_have: next }))} tree={rules.must_have} />
        </div>
        <div>
          <h3 className="mb-3 font-display text-lg text-ink">Good to Have</h3>
          <RuleNodeEditor node={rules.good_to_have} parentId="" index={0} columns={columns.length ? columns : ['classification']} onTreeChange={(next) => setRules((current) => ({ ...current, good_to_have: next }))} tree={rules.good_to_have} />
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_320px]">
        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-950 p-4 text-xs text-cyan-200">
          <div className="mb-2 font-display text-sm uppercase tracking-[0.2em] text-cyan-100">AST Preview</div>
          <pre className="overflow-x-auto whitespace-pre-wrap">{JSON.stringify(rules, null, 2)}</pre>
        </div>
        <div className="rounded-[1.5rem] border border-slate-200 bg-sand p-4">
          <p className="text-sm font-semibold text-ember">Versioned persistence</p>
          <p className="mt-2 text-sm text-slate-700">Every save creates a new ruleset version, preserving the exact nested structure and stable node identifiers for explanations.</p>
          <button type="button" onClick={handleSave} disabled={saving || !columns.length} className="mt-4 w-full rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
            {saving ? 'Saving...' : 'Save rule set'}
          </button>
        </div>
      </div>
    </section>
  )
}
