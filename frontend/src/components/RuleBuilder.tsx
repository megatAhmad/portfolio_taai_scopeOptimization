import { useEffect, useMemo, useState } from 'react'
import type { Dispatch, DragEvent, SetStateAction } from 'react'
import { ArrowDown, ArrowUp, Braces, FolderTree, GitBranch, Plus, Trash2 } from 'lucide-react'
import type { RuleAst, RuleConditionNode, RuleGroupNode, RuleNode, RuleSet } from '../types'

const textOperators = ['=', '!=', 'CONTAINS', 'CONTAINS ANY', 'CONTAINS ALL', 'IN']
const rangeOperators = ['<', '>', '<=', '>=', 'BETWEEN']

type EditorMode = 'graph' | 'syntax' | 'split'
type RootKey = 'must_have' | 'good_to_have'

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

function defaultRuleAst(): RuleAst {
  return {
    must_have: createGroup(),
    good_to_have: createGroup(),
    fallback_label: 'Not Needed',
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isConditionNode(value: unknown): value is RuleConditionNode {
  return isRecord(value) && value.type === 'condition' && typeof value.field === 'string'
}

function isGroupNode(value: unknown): value is RuleGroupNode {
  return isRecord(value) && value.type === 'group' && Array.isArray(value.children)
}

function normalizeConditionNode(value: unknown, columns: string[]): RuleConditionNode {
  const fallbackField = columns[0] ?? 'classification'
  if (!isConditionNode(value)) {
    return createCondition(fallbackField)
  }

  const dataType = value.data_type === 'numeric' || value.data_type === 'date' ? value.data_type : 'text'
  const operatorPool = dataType === 'text' ? textOperators : rangeOperators
  return {
    id: typeof value.id === 'string' && value.id ? value.id : createId(),
    type: 'condition',
    field: value.field || fallbackField,
    data_type: dataType,
    operator: typeof value.operator === 'string' && operatorPool.includes(value.operator) ? value.operator : operatorPool[0],
    value: typeof value.value === 'string' ? value.value : '',
    secondary_value: typeof value.secondary_value === 'string' ? value.secondary_value : '',
  }
}

function normalizeRuleNode(value: unknown, columns: string[]): RuleNode {
  if (isGroupNode(value)) {
    return {
      id: typeof value.id === 'string' && value.id ? value.id : createId(),
      type: 'group',
      combinator: value.combinator === 'OR' ? 'OR' : 'AND',
      children: value.children.map((child) => normalizeRuleNode(child, columns)),
    }
  }
  return normalizeConditionNode(value, columns)
}

function normalizeGroupNode(value: unknown, columns: string[]): RuleGroupNode {
  const normalized = normalizeRuleNode(value, columns)
  return normalized.type === 'group' ? normalized : createGroup()
}

function normalizeRuleAst(value: unknown, columns: string[]): RuleAst {
  if (!isRecord(value)) {
    return defaultRuleAst()
  }

  return {
    must_have: normalizeGroupNode(value.must_have, columns),
    good_to_have: normalizeGroupNode(value.good_to_have, columns),
    fallback_label: typeof value.fallback_label === 'string' && value.fallback_label ? value.fallback_label : 'Not Needed',
  }
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

function detachNode(root: RuleGroupNode, targetId: string): { tree: RuleGroupNode; removed: RuleNode | null } {
  let removed: RuleNode | null = null

  function walk(node: RuleGroupNode): RuleGroupNode {
    const nextChildren: RuleNode[] = []
    for (const child of node.children) {
      if (child.id === targetId) {
        removed = child
        continue
      }
      nextChildren.push(child.type === 'group' ? walk(child) : child)
    }
    return { ...node, children: nextChildren }
  }

  return { tree: walk(root), removed }
}

function insertNode(root: RuleGroupNode, parentId: string, index: number, node: RuleNode): RuleGroupNode {
  return mutateTree(root, parentId, (group) => {
    const next = [...group.children]
    const safeIndex = Math.max(0, Math.min(index, next.length))
    next.splice(safeIndex, 0, node)
    return { ...group, children: next }
  })
}

function groupContainsId(group: RuleGroupNode, targetId: string): boolean {
  for (const child of group.children) {
    if (child.id === targetId) {
      return true
    }
    if (child.type === 'group' && groupContainsId(child, targetId)) {
      return true
    }
  }
  return false
}

function moveAstNode(ast: RuleAst, dragId: string, targetRoot: RootKey, targetParentId: string, targetIndex: number): RuleAst {
  let removed: RuleNode | null = null
  let nextAst = ast

  for (const rootKey of ['must_have', 'good_to_have'] as RootKey[]) {
    const result = detachNode(nextAst[rootKey], dragId)
    if (result.removed) {
      removed = result.removed
    }
    nextAst = {
      ...nextAst,
      [rootKey]: result.tree,
    }
  }

  if (!removed || removed.id === targetParentId) {
    return ast
  }

  if (removed.type === 'group' && groupContainsId(removed, targetParentId)) {
    return ast
  }

  return {
    ...nextAst,
    [targetRoot]: insertNode(nextAst[targetRoot], targetParentId, targetIndex, removed),
  }
}

function summarizeNode(node: RuleNode): string {
  if (node.type === 'condition') {
    const second = node.operator === 'BETWEEN' && node.secondary_value ? ` and ${node.secondary_value}` : ''
    const value = node.value ? ` ${node.value}` : ''
    return `${node.field} ${node.operator}${value}${second}`
  }
  return `${node.combinator} group with ${node.children.length} item${node.children.length === 1 ? '' : 's'}`
}

function DropLane({
  active,
  onDragOver,
  onDragLeave,
  onDrop,
}: {
  active: boolean
  onDragOver: (event: DragEvent<HTMLDivElement>) => void
  onDragLeave: () => void
  onDrop: (event: DragEvent<HTMLDivElement>) => void
}) {
  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={`h-4 rounded-full border border-dashed transition ${active ? 'border-ember bg-ember/10' : 'border-slate-200 bg-transparent'}`}
    />
  )
}

function RuleNodeEditor({
  node,
  parentId,
  index,
  columns,
  onTreeChange,
  tree,
  rootKey,
  draggingNodeId,
  activeDropKey,
  onDragStart,
  onDragEnd,
  onDropTarget,
  setActiveDropKey,
}: {
  node: RuleNode
  parentId: string
  index: number
  columns: string[]
  onTreeChange: (next: RuleGroupNode) => void
  tree: RuleGroupNode
  rootKey: RootKey
  draggingNodeId: string | null
  activeDropKey: string | null
  onDragStart: (nodeId: string) => void
  onDragEnd: () => void
  onDropTarget: (targetRoot: RootKey, targetParentId: string, targetIndex: number) => void
  setActiveDropKey: Dispatch<SetStateAction<string | null>>
}) {
  const dropKey = `${rootKey}:${parentId}:${index}`

  if (node.type === 'condition') {
    const operators = node.data_type === 'text' ? textOperators : rangeOperators
    return (
      <div
        draggable
        onDragStart={(event) => {
          event.dataTransfer.effectAllowed = 'move'
          event.dataTransfer.setData('text/plain', node.id)
          onDragStart(node.id)
        }}
        onDragEnd={onDragEnd}
        className={`rounded-2xl border bg-white p-4 shadow-sm transition ${draggingNodeId === node.id ? 'border-ember/60 opacity-60' : 'border-slate-200'}`}
      >
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Condition</div>
          <div className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">{summarizeNode(node)}</div>
        </div>
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
        <div className="mt-3">
          <DropLane
            active={activeDropKey === dropKey}
            onDragOver={(event) => {
              event.preventDefault()
              setActiveDropKey(dropKey)
            }}
            onDragLeave={() => setActiveDropKey(activeDropKey === dropKey ? null : activeDropKey)}
            onDrop={(event) => {
              event.preventDefault()
              onDropTarget(rootKey, parentId, index)
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div
      draggable={Boolean(parentId)}
      onDragStart={(event) => {
        if (!parentId) return
        event.dataTransfer.effectAllowed = 'move'
        event.dataTransfer.setData('text/plain', node.id)
        onDragStart(node.id)
      }}
      onDragEnd={onDragEnd}
      className={`rounded-[1.5rem] border border-dashed bg-slate-50 p-4 transition ${draggingNodeId === node.id ? 'border-ember bg-ember/5 opacity-70' : 'border-slate-300'}`}
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="rounded-full bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-ocean">Group</div>
        <div className="rounded-full bg-white px-3 py-1 text-xs text-slate-600">{summarizeNode(node)}</div>
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
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
      <div className="space-y-3 border-l-2 border-slate-200 pl-4">
        <DropLane
          active={activeDropKey === dropKey}
          onDragOver={(event) => {
            event.preventDefault()
            setActiveDropKey(dropKey)
          }}
          onDragLeave={() => setActiveDropKey(activeDropKey === dropKey ? null : activeDropKey)}
          onDrop={(event) => {
            event.preventDefault()
            onDropTarget(rootKey, parentId, index)
          }}
        />
        {node.children.length === 0 && <p className="text-sm text-slate-500">Drop nodes here or add nested groups and conditions.</p>}
        {node.children.map((child, childIndex) => (
          <div key={child.id} className="space-y-3">
            <DropLane
              active={activeDropKey === `${rootKey}:${node.id}:${childIndex}`}
              onDragOver={(event) => {
                event.preventDefault()
                setActiveDropKey(`${rootKey}:${node.id}:${childIndex}`)
              }}
              onDragLeave={() => setActiveDropKey(activeDropKey === `${rootKey}:${node.id}:${childIndex}` ? null : activeDropKey)}
              onDrop={(event) => {
                event.preventDefault()
                onDropTarget(rootKey, node.id, childIndex)
              }}
            />
            <RuleNodeEditor
              node={child}
              parentId={node.id}
              index={childIndex}
              columns={columns}
              onTreeChange={onTreeChange}
              tree={tree}
              rootKey={rootKey}
              draggingNodeId={draggingNodeId}
              activeDropKey={activeDropKey}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              onDropTarget={onDropTarget}
              setActiveDropKey={setActiveDropKey}
            />
          </div>
        ))}
        <DropLane
          active={activeDropKey === `${rootKey}:${node.id}:${node.children.length}`}
          onDragOver={(event) => {
            event.preventDefault()
            setActiveDropKey(`${rootKey}:${node.id}:${node.children.length}`)
          }}
          onDragLeave={() => setActiveDropKey(activeDropKey === `${rootKey}:${node.id}:${node.children.length}` ? null : activeDropKey)}
          onDrop={(event) => {
            event.preventDefault()
            onDropTarget(rootKey, node.id, node.children.length)
          }}
        />
      </div>
    </div>
  )
}

function GraphRoot({
  title,
  accentClass,
  rootKey,
  node,
  columns,
  setRoot,
  draggingNodeId,
  activeDropKey,
  onDragStart,
  onDragEnd,
  onDropTarget,
  setActiveDropKey,
}: {
  title: string
  accentClass: string
  rootKey: RootKey
  node: RuleGroupNode
  columns: string[]
  setRoot: (next: RuleGroupNode) => void
  draggingNodeId: string | null
  activeDropKey: string | null
  onDragStart: (nodeId: string) => void
  onDragEnd: () => void
  onDropTarget: (targetRoot: RootKey, targetParentId: string, targetIndex: number) => void
  setActiveDropKey: Dispatch<SetStateAction<string | null>>
}) {
  return (
    <div className="rounded-[1.75rem] border border-slate-200 bg-white p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-lg text-ink">{title}</h3>
          <p className="text-sm text-slate-600">Drag cards between groups and across trees. Drop lanes define exact placement.</p>
        </div>
        <div className={`rounded-full px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] ${accentClass}`}>Root group</div>
      </div>
      <div className="space-y-3">
        <div className="flex flex-wrap gap-3">
          <select value={node.combinator} onChange={(event) => setRoot({ ...node, combinator: event.target.value as 'AND' | 'OR' })} className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold">
            <option value="AND">AND</option>
            <option value="OR">OR</option>
          </select>
          <button type="button" onClick={() => setRoot({ ...node, children: [...node.children, createCondition(columns[0] ?? '')] })} className="rounded-full bg-mist px-4 py-2 text-sm font-semibold text-ocean">
            <Plus size={14} className="inline-block" /> Condition
          </button>
          <button type="button" onClick={() => setRoot({ ...node, children: [...node.children, createGroup()] })} className="rounded-full bg-sand px-4 py-2 text-sm font-semibold text-ember">
            <Plus size={14} className="inline-block" /> Group
          </button>
        </div>
        <div className="space-y-3">
          <DropLane
            active={activeDropKey === `${rootKey}:${node.id}:0`}
            onDragOver={(event) => {
              event.preventDefault()
              setActiveDropKey(`${rootKey}:${node.id}:0`)
            }}
            onDragLeave={() => setActiveDropKey(activeDropKey === `${rootKey}:${node.id}:0` ? null : activeDropKey)}
            onDrop={(event) => {
              event.preventDefault()
              onDropTarget(rootKey, node.id, 0)
            }}
          />
          {node.children.length === 0 && <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">This root is empty. Add a node or drag one in from the other tree.</p>}
          {node.children.map((child, index) => (
            <div key={child.id} className="space-y-3">
              <RuleNodeEditor
                node={child}
                parentId={node.id}
                index={index}
                columns={columns}
                onTreeChange={setRoot}
                tree={node}
                rootKey={rootKey}
                draggingNodeId={draggingNodeId}
                activeDropKey={activeDropKey}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                onDropTarget={onDropTarget}
                setActiveDropKey={setActiveDropKey}
              />
              <DropLane
                active={activeDropKey === `${rootKey}:${node.id}:${index + 1}`}
                onDragOver={(event) => {
                  event.preventDefault()
                  setActiveDropKey(`${rootKey}:${node.id}:${index + 1}`)
                }}
                onDragLeave={() => setActiveDropKey(activeDropKey === `${rootKey}:${node.id}:${index + 1}` ? null : activeDropKey)}
                onDrop={(event) => {
                  event.preventDefault()
                  onDropTarget(rootKey, node.id, index + 1)
                }}
              />
            </div>
          ))}
        </div>
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
  const defaultRules = useMemo(() => defaultRuleAst(), [])
  const [name, setName] = useState(existingRuleSet?.name ?? 'Default Rule Set')
  const [rules, setRules] = useState<RuleAst>(existingRuleSet?.ast_json ?? defaultRules)
  const [saving, setSaving] = useState(false)
  const [mode, setMode] = useState<EditorMode>('graph')
  const [syntaxText, setSyntaxText] = useState(JSON.stringify(existingRuleSet?.ast_json ?? defaultRules, null, 2))
  const [syntaxError, setSyntaxError] = useState('')
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null)
  const [activeDropKey, setActiveDropKey] = useState<string | null>(null)

  useEffect(() => {
    if (existingRuleSet) {
      setName(existingRuleSet.name)
      setRules(existingRuleSet.ast_json)
      setSyntaxText(JSON.stringify(existingRuleSet.ast_json, null, 2))
      setSyntaxError('')
    }
  }, [existingRuleSet])

  useEffect(() => {
    setSyntaxText(JSON.stringify(rules, null, 2))
    setSyntaxError('')
  }, [rules])

  const usableColumns = columns.length ? columns : ['classification']

  function updateRules(next: RuleAst) {
    setRules(normalizeRuleAst(next, usableColumns))
  }

  function handleSyntaxChange(value: string) {
    setSyntaxText(value)
    try {
      const parsed = JSON.parse(value) as unknown
      const normalized = normalizeRuleAst(parsed, usableColumns)
      setRules(normalized)
      setSyntaxError('')
    } catch (error) {
      setSyntaxError(error instanceof Error ? error.message : 'Invalid JSON')
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      await onSave({ name, ast_json: rules })
    } finally {
      setSaving(false)
    }
  }

  function handleDropTarget(targetRoot: RootKey, targetParentId: string, targetIndex: number) {
    if (!draggingNodeId) return
    setRules((current) => moveAstNode(current, draggingNodeId, targetRoot, targetParentId, targetIndex))
    setDraggingNodeId(null)
    setActiveDropKey(null)
  }

  const modeButtonClass = (value: EditorMode) =>
    `inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
      mode === value ? 'bg-ink text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
    }`

  return (
    <section className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-mist px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-ocean">
            <FolderTree size={14} />
            Dual AST Rule Builder
          </div>
          <h2 className="mt-3 font-display text-2xl text-ink">Visual Classification Logic</h2>
          <p className="text-sm text-slate-600">Switch between a drag-and-drop node graph and editable syntax. Both views update the same AST in real time.</p>
        </div>
        <div className="flex flex-col gap-3 md:items-end">
          <input value={name} onChange={(event) => setName(event.target.value)} className="rounded-full border border-slate-200 px-4 py-3" />
          <input value={rules.fallback_label} onChange={(event) => updateRules({ ...rules, fallback_label: event.target.value })} className="rounded-full border border-slate-200 px-4 py-3" placeholder="Fallback label" />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <button type="button" onClick={() => setMode('graph')} className={modeButtonClass('graph')}>
          <GitBranch size={16} />
          Node graph
        </button>
        <button type="button" onClick={() => setMode('syntax')} className={modeButtonClass('syntax')}>
          <Braces size={16} />
          Syntax
        </button>
        <button type="button" onClick={() => setMode('split')} className={modeButtonClass('split')}>
          <FolderTree size={16} />
          Split view
        </button>
      </div>

      {(mode === 'graph' || mode === 'split') && (
        <div className={`mt-6 grid gap-6 ${mode === 'split' ? '2xl:grid-cols-[1.2fr_0.8fr]' : ''}`}>
          <div className="grid gap-6 xl:grid-cols-2">
            <GraphRoot
              title="Must Have"
              accentClass="bg-mist text-ocean"
              rootKey="must_have"
              node={rules.must_have}
              columns={usableColumns}
              setRoot={(next) => updateRules({ ...rules, must_have: next })}
              draggingNodeId={draggingNodeId}
              activeDropKey={activeDropKey}
              onDragStart={setDraggingNodeId}
              onDragEnd={() => {
                setDraggingNodeId(null)
                setActiveDropKey(null)
              }}
              onDropTarget={handleDropTarget}
              setActiveDropKey={setActiveDropKey}
            />
            <GraphRoot
              title="Good to Have"
              accentClass="bg-sand text-ember"
              rootKey="good_to_have"
              node={rules.good_to_have}
              columns={usableColumns}
              setRoot={(next) => updateRules({ ...rules, good_to_have: next })}
              draggingNodeId={draggingNodeId}
              activeDropKey={activeDropKey}
              onDragStart={setDraggingNodeId}
              onDragEnd={() => {
                setDraggingNodeId(null)
                setActiveDropKey(null)
              }}
              onDropTarget={handleDropTarget}
              setActiveDropKey={setActiveDropKey}
            />
          </div>

          {mode === 'split' && (
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-950 p-4 text-xs text-cyan-200">
              <div className="mb-2 font-display text-sm uppercase tracking-[0.2em] text-cyan-100">Live syntax</div>
              <textarea
                value={syntaxText}
                onChange={(event) => handleSyntaxChange(event.target.value)}
                spellCheck={false}
                className="min-h-[34rem] w-full rounded-2xl border border-cyan-900 bg-slate-950 px-4 py-4 font-mono text-xs text-cyan-200 outline-none"
              />
              {syntaxError && <p className="mt-3 text-sm text-red-300">Syntax error: {syntaxError}</p>}
            </div>
          )}
        </div>
      )}

      {mode === 'syntax' && (
        <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_320px]">
          <div className="rounded-[1.5rem] border border-slate-200 bg-slate-950 p-4 text-cyan-200">
            <div className="mb-2 font-display text-sm uppercase tracking-[0.2em] text-cyan-100">AST syntax editor</div>
            <textarea
              value={syntaxText}
              onChange={(event) => handleSyntaxChange(event.target.value)}
              spellCheck={false}
              className="min-h-[38rem] w-full rounded-2xl border border-cyan-900 bg-slate-950 px-4 py-4 font-mono text-xs text-cyan-200 outline-none"
            />
            {syntaxError && <p className="mt-3 text-sm text-red-300">Syntax error: {syntaxError}</p>}
          </div>
          <div className="rounded-[1.5rem] border border-slate-200 bg-sand p-4">
            <p className="text-sm font-semibold text-ember">Interchangeable editing</p>
            <p className="mt-2 text-sm text-slate-700">Valid JSON updates the node graph immediately. Dragging in the graph also rewrites the syntax view, so both editors stay aligned to the same nested AST.</p>
            <div className="mt-4 rounded-2xl bg-white p-4 text-sm text-slate-600">
              <p className="font-semibold text-ink">Tips</p>
              <p className="mt-2">Use `type: "group"` with `children` for nested logic and `type: "condition"` for leaves.</p>
              <p className="mt-2">Invalid JSON stays in the editor, but the graph keeps the last valid AST until the syntax is fixed.</p>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_320px]">
        <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
          <div className="mb-2 font-display text-sm uppercase tracking-[0.2em] text-slate-500">Current summary</div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl bg-mist p-4 text-sm text-ink">
              <p className="font-semibold">Must Have</p>
              <p className="mt-2">{summarizeNode(rules.must_have)}</p>
            </div>
            <div className="rounded-2xl bg-sand p-4 text-sm text-ink">
              <p className="font-semibold">Good to Have</p>
              <p className="mt-2">{summarizeNode(rules.good_to_have)}</p>
            </div>
          </div>
        </div>
        <div className="rounded-[1.5rem] border border-slate-200 bg-sand p-4">
          <p className="text-sm font-semibold text-ember">Versioned persistence</p>
          <p className="mt-2 text-sm text-slate-700">Every save creates a new ruleset version, preserving the exact nested structure and stable node identifiers for explanations.</p>
          <button type="button" onClick={handleSave} disabled={saving || !columns.length || Boolean(syntaxError)} className="mt-4 w-full rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
            {saving ? 'Saving...' : 'Save rule set'}
          </button>
        </div>
      </div>
    </section>
  )
}
