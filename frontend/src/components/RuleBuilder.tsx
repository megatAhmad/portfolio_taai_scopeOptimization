import { useEffect, useMemo, useState } from 'react'
import { Braces, FolderTree, GitBranch, Plus, Trash2 } from 'lucide-react'
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { RuleAst, RuleConditionNode, RuleGroupNode, RuleNode, RuleSet } from '../types'

const textOperators = ['=', '!=', 'CONTAINS', 'CONTAINS ANY', 'CONTAINS ALL', 'IN']
const rangeOperators = ['<', '>', '<=', '>=', 'BETWEEN']

type EditorMode = 'flowchart' | 'syntax' | 'split'
type RootKey = 'must_have' | 'good_to_have'

type FlowNodeData = {
  kind: 'root' | 'group' | 'condition'
  label: string
  summary: string
  accentClass: string
  selected: boolean
}

type SelectedNodeState =
  | { node: RuleGroupNode; rootKey: RootKey; isRoot: true; parentId: null }
  | { node: RuleGroupNode; rootKey: RootKey; isRoot: false; parentId: string }
  | { node: RuleConditionNode; rootKey: RootKey; isRoot: false; parentId: string }

type ConditionInputMode = 'single' | 'between' | 'multi_list'

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
    values: [''],
  }
}

function createGroup(): RuleGroupNode {
  return { id: createId(), type: 'group', name: '', combinator: 'AND', children: [] }
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
  const operator = typeof value.operator === 'string' && operatorPool.includes(value.operator) ? value.operator : operatorPool[0]
  const rawValue = typeof value.value === 'string' ? value.value : ''
  const rawSecondary = typeof value.secondary_value === 'string' ? value.secondary_value : ''
  const rawValues = Array.isArray(value.values) ? value.values.map((item) => (item == null ? '' : String(item))) : []
  const normalizedValues = getConditionInputMode(operator) === 'multi_list'
    ? normalizeMultiValueList(rawValues.length ? rawValues : splitCommaValues(rawValue))
    : undefined

  return {
    id: typeof value.id === 'string' && value.id ? value.id : createId(),
    type: 'condition',
    field: value.field || fallbackField,
    data_type: dataType,
    operator,
    value: rawValue,
    secondary_value: rawSecondary,
    values: normalizedValues,
  }
}

function normalizeRuleNode(value: unknown, columns: string[]): RuleNode {
  if (isGroupNode(value)) {
    return {
      id: typeof value.id === 'string' && value.id ? value.id : createId(),
      type: 'group',
      name: typeof value.name === 'string' ? value.name : '',
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

function summarizeNode(node: RuleNode): string {
  if (node.type === 'condition') {
    if (getConditionInputMode(node.operator) === 'multi_list') {
      const values = normalizeMultiValueList(node.values ?? splitCommaValues(node.value ?? ''))
      const rendered = values.filter((item) => item.trim()).join(', ')
      return `${node.field} ${node.operator}${rendered ? ` ${rendered}` : ''}`
    }
    const second = node.operator === 'BETWEEN' && node.secondary_value ? ` and ${node.secondary_value}` : ''
    const value = node.value ? ` ${node.value}` : ''
    return `${node.field} ${node.operator}${value}${second}`
  }
  const base = `${node.combinator} group with ${node.children.length} item${node.children.length === 1 ? '' : 's'}`
  return node.name ? `${node.name} • ${base}` : base
}

function getConditionInputMode(operator: string): ConditionInputMode {
  if (operator === 'BETWEEN') return 'between'
  if (operator === 'CONTAINS ANY' || operator === 'CONTAINS ALL') return 'multi_list'
  return 'single'
}

function splitCommaValues(raw: string): string[] {
  return raw
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function normalizeMultiValueList(values: string[]): string[] {
  const next = values.map((item) => item ?? '')
  return next.length ? next : ['']
}

function coerceConditionForOperator(condition: RuleConditionNode, operator: string): RuleConditionNode {
  const mode = getConditionInputMode(operator)
  const seedValues = normalizeMultiValueList(
    (condition.values && condition.values.length ? condition.values : splitCommaValues(condition.value ?? '')),
  )

  if (mode === 'multi_list') {
    return {
      ...condition,
      operator,
      value: seedValues[0] ?? '',
      secondary_value: '',
      values: seedValues,
    }
  }

  if (mode === 'between') {
    return {
      ...condition,
      operator,
      value: condition.value || seedValues[0] || '',
      secondary_value: condition.secondary_value || seedValues[1] || '',
      values: undefined,
    }
  }

  return {
    ...condition,
    operator,
    value: condition.value || seedValues[0] || '',
    secondary_value: '',
    values: undefined,
  }
}

function MultiValueEditor({
  values,
  onChange,
}: {
  values: string[]
  onChange: (next: string[]) => void
}) {
  return (
    <div className="space-y-3">
      {values.map((value, index) => (
        <div key={`${index}-${value}`} className="flex items-center gap-3">
          <input
            value={value}
            onChange={(event) => {
              const next = [...values]
              next[index] = event.target.value
              onChange(next)
            }}
            onBlur={(event) => {
              const parts = splitCommaValues(event.target.value)
              if (parts.length <= 1) return
              const next = [...values]
              next.splice(index, 1, ...parts)
              onChange(normalizeMultiValueList(next))
            }}
            placeholder={`Value ${index + 1}`}
            className="w-full rounded-2xl border border-slate-200 px-4 py-3"
          />
          <button
            type="button"
            onClick={() => {
              const next = values.filter((_, currentIndex) => currentIndex !== index)
              onChange(normalizeMultiValueList(next))
            }}
            disabled={values.length === 1}
            className="rounded-full border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-40"
          >
            -
          </button>
          <button
            type="button"
            onClick={() => {
              const next = [...values]
              next.splice(index + 1, 0, '')
              onChange(next)
            }}
            className="rounded-full border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700"
          >
            +
          </button>
        </div>
      ))}
      <p className="text-xs leading-5 text-slate-500">Each row accepts one value. Paste comma-separated text to split it into multiple rows.</p>
    </div>
  )
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

function countLeafSlots(node: RuleNode): number {
  if (node.type === 'condition' || node.children.length === 0) {
    return 1
  }
  return node.children.reduce((total, child) => total + countLeafSlots(child), 0)
}

function BaseFlowNode({
  data,
  chipLabel,
}: NodeProps<FlowNodeData> & { chipLabel: string }) {
  return (
    <div
      className={`theme-flow-node min-w-[210px] max-w-[240px] rounded-[1.35rem] border bg-white px-4 py-3 shadow-sm transition ${
        data.selected ? 'border-ember shadow-lg shadow-ember/15' : 'border-slate-200'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!h-3 !w-3 !border-2 !border-white !bg-slate-400" />
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className={`inline-flex rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${data.accentClass}`}>
            {chipLabel}
          </div>
          <div className="mt-2 text-sm font-semibold text-ink">{data.label}</div>
        </div>
        <div className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-500">
          Click
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-600">{data.summary}</p>
      <Handle type="source" position={Position.Bottom} className="!h-3 !w-3 !border-2 !border-white !bg-slate-400" />
    </div>
  )
}

function RootFlowNode(props: NodeProps<FlowNodeData>) {
  return <BaseFlowNode {...props} chipLabel="Root" />
}

function GroupFlowNode(props: NodeProps<FlowNodeData>) {
  return <BaseFlowNode {...props} chipLabel="Group" />
}

function ConditionFlowNode(props: NodeProps<FlowNodeData>) {
  return <BaseFlowNode {...props} chipLabel="Condition" />
}

const nodeTypes = {
  root: RootFlowNode,
  group: GroupFlowNode,
  condition: ConditionFlowNode,
}

function buildFlowLayout(rules: RuleAst, selectedNodeId: string | null): { nodes: Node<FlowNodeData>[]; edges: Edge[] } {
  const horizontalGap = 280
  const verticalGap = 170
  const rootGap = 2
  const nodes: Node<FlowNodeData>[] = []
  const edges: Edge[] = []

  function pushTree(node: RuleNode, options: { rootKey: RootKey; rootLabel: string; startSlot: number; depth: number; parentId: string | null; isRoot: boolean }) {
    const slotWidth = countLeafSlots(node)
    const centerSlot = options.startSlot + (slotWidth - 1) / 2
    const x = centerSlot * horizontalGap
    const y = options.depth * verticalGap
    const kind = options.isRoot ? 'root' : node.type
    const label = options.isRoot
      ? options.rootLabel
      : node.type === 'group'
        ? node.name || `${node.combinator} group`
        : node.field
    const accentClass = options.rootKey === 'must_have'
      ? kind === 'condition'
        ? 'bg-mist text-ocean'
        : 'bg-ocean/10 text-ocean'
      : kind === 'condition'
        ? 'bg-sand text-ember'
        : 'bg-amber-100 text-amber-900'

    nodes.push({
      id: node.id,
      type: kind,
      position: { x, y },
      draggable: false,
      selectable: true,
      data: {
        kind,
        label,
        summary: options.isRoot ? summarizeNode(node) : summarizeNode(node),
        accentClass,
        selected: selectedNodeId === node.id,
      },
    })

    if (options.parentId) {
      edges.push({
        id: `${options.parentId}-${node.id}`,
        source: options.parentId,
        target: node.id,
        markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
        style: { stroke: options.rootKey === 'must_have' ? '#0f4c81' : '#b45309', strokeWidth: 1.75 },
      })
    }

    if (node.type === 'group' && node.children.length > 0) {
      let childStart = options.startSlot
      for (const child of node.children) {
        const childWidth = countLeafSlots(child)
        pushTree(child, {
          rootKey: options.rootKey,
          rootLabel: options.rootLabel,
          startSlot: childStart,
          depth: options.depth + 1,
          parentId: node.id,
          isRoot: false,
        })
        childStart += childWidth
      }
    }
  }

  const mustWidth = countLeafSlots(rules.must_have)
  const goodWidth = countLeafSlots(rules.good_to_have)

  pushTree(rules.must_have, {
    rootKey: 'must_have',
    rootLabel: 'Must Have',
    startSlot: 0,
    depth: 0,
    parentId: null,
    isRoot: true,
  })
  pushTree(rules.good_to_have, {
    rootKey: 'good_to_have',
    rootLabel: 'Good to Have',
    startSlot: mustWidth + rootGap,
    depth: 0,
    parentId: null,
    isRoot: true,
  })

  if (mustWidth === 0 && goodWidth === 0) {
    return { nodes: [], edges: [] }
  }

  return { nodes, edges }
}

function findSelectedNode(ast: RuleAst, targetId: string | null): SelectedNodeState | null {
  if (!targetId) return null

  function visit(node: RuleNode, rootKey: RootKey, parentId: string | null, isRoot: boolean): SelectedNodeState | null {
    if (node.id === targetId) {
      if (node.type === 'group') {
        return {
          node,
          rootKey,
          isRoot,
          parentId,
        } as SelectedNodeState
      }
      return {
        node,
        rootKey,
        isRoot: false,
        parentId: parentId ?? ast[rootKey].id,
      }
    }

    if (node.type === 'group') {
      for (const child of node.children) {
        const result = visit(child, rootKey, node.id, false)
        if (result) return result
      }
    }

    return null
  }

  return visit(ast.must_have, 'must_have', null, true) ?? visit(ast.good_to_have, 'good_to_have', null, true)
}

function FlowchartCanvas({
  rules,
  selectedNodeId,
  onSelectNode,
}: {
  rules: RuleAst
  selectedNodeId: string | null
  onSelectNode: (nodeId: string) => void
}) {
  const flow = useMemo(() => buildFlowLayout(rules, selectedNodeId), [rules, selectedNodeId])

  return (
    <div className="theme-canvas h-[42rem] overflow-hidden rounded-[1.6rem] border border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(239,246,255,0.92))] transition-colors duration-300">
      <ReactFlow
        nodes={flow.nodes}
        edges={flow.edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.16 }}
        minZoom={0.45}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        onNodeClick={(_, node) => onSelectNode(node.id)}
        proOptions={{ hideAttribution: true }}
      >
        <MiniMap pannable zoomable nodeColor={(node) => (node.id === selectedNodeId ? '#c2410c' : '#94a3b8')} />
        <Controls showInteractive={false} />
        <Background gap={20} color="#d7e3f4" />
      </ReactFlow>
    </div>
  )
}

function InspectorSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="theme-subpanel rounded-[1.4rem] border border-slate-200 bg-white p-4 transition-colors duration-300">
      <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{title}</div>
      <div className="mt-3 space-y-3">{children}</div>
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
  const [mode, setMode] = useState<EditorMode>('flowchart')
  const [syntaxText, setSyntaxText] = useState(JSON.stringify(existingRuleSet?.ast_json ?? defaultRules, null, 2))
  const [syntaxError, setSyntaxError] = useState('')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(existingRuleSet?.ast_json.must_have.id ?? defaultRules.must_have.id)

  useEffect(() => {
    if (existingRuleSet) {
      setName(existingRuleSet.name)
      setRules(existingRuleSet.ast_json)
      setSyntaxText(JSON.stringify(existingRuleSet.ast_json, null, 2))
      setSyntaxError('')
      setSelectedNodeId(existingRuleSet.ast_json.must_have.id)
    }
  }, [existingRuleSet])

  useEffect(() => {
    setSyntaxText(JSON.stringify(rules, null, 2))
    setSyntaxError('')
  }, [rules])

  const usableColumns = columns.length ? columns : ['classification']
  const selectedNode = useMemo(() => findSelectedNode(rules, selectedNodeId), [rules, selectedNodeId])
  const selectedConditionMode = selectedNode?.node.type === 'condition' ? getConditionInputMode(selectedNode.node.operator) : null

  useEffect(() => {
    if (!selectedNode) {
      setSelectedNodeId(rules.must_have.id)
    }
  }, [selectedNode, rules.must_have.id])

  function updateRules(next: RuleAst) {
    setRules(normalizeRuleAst(next, usableColumns))
  }

  function updateRoot(rootKey: RootKey, updater: (root: RuleGroupNode) => RuleGroupNode) {
    updateRules({
      ...rules,
      [rootKey]: updater(rules[rootKey]),
    })
  }

  function updateSelectedGroup(updater: (group: RuleGroupNode) => RuleGroupNode) {
    if (!selectedNode || selectedNode.node.type !== 'group') return
    updateRoot(selectedNode.rootKey, (root) => mutateTree(root, selectedNode.node.id, updater))
  }

  function updateSelectedCondition(updater: (condition: RuleConditionNode) => RuleConditionNode) {
    if (!selectedNode || selectedNode.node.type !== 'condition') return
    updateRoot(selectedNode.rootKey, (root) =>
      mutateNode(root, selectedNode.node.id, (node) => {
        if (node.type !== 'condition') return node
        return updater(node)
      }),
    )
  }

  function addChild(childType: 'condition' | 'group') {
    if (!selectedNode || selectedNode.node.type !== 'group') return
    const child = childType === 'condition' ? createCondition(usableColumns[0] ?? '') : createGroup()
    updateSelectedGroup((group) => ({ ...group, children: [...group.children, child] }))
    setSelectedNodeId(child.id)
  }

  function deleteSelectedNode() {
    if (!selectedNode || selectedNode.isRoot) return
    updateRoot(selectedNode.rootKey, (root) => removeNode(root, selectedNode.node.id))
    setSelectedNodeId(selectedNode.parentId)
  }

  function handleSyntaxChange(value: string) {
    setSyntaxText(value)
    try {
      const parsed = JSON.parse(value) as unknown
      const normalized = normalizeRuleAst(parsed, usableColumns)
      setRules(normalized)
      setSyntaxError('')
      setSelectedNodeId((current) => findSelectedNode(normalized, current)?.node.id ?? normalized.must_have.id)
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

  const modeButtonClass = (value: EditorMode) =>
    `inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
      mode === value ? 'bg-ink text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
    }`

  return (
    <section className="theme-panel rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur transition-colors duration-300">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-mist px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-ocean">
            <FolderTree size={14} />
            AST Flowchart Builder
          </div>
          <h2 className="mt-3 font-display text-2xl text-ink">Visual Classification Logic</h2>
          <p className="text-sm text-slate-600">Edit the rule tree as a real flowchart. Click a node to configure it, then save the same AST structure already used by the backend.</p>
        </div>
        <div className="flex flex-col gap-3 md:items-end">
          <input value={name} onChange={(event) => setName(event.target.value)} className="rounded-full border border-slate-200 px-4 py-3" />
          <input value={rules.fallback_label} onChange={(event) => updateRules({ ...rules, fallback_label: event.target.value })} className="rounded-full border border-slate-200 px-4 py-3" placeholder="Fallback label" />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <button type="button" onClick={() => setMode('flowchart')} className={modeButtonClass('flowchart')}>
          <GitBranch size={16} />
          Flowchart
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

      {(mode === 'flowchart' || mode === 'split') && (
        <div className={`mt-6 grid gap-6 ${mode === 'split' ? '2xl:grid-cols-[1.55fr_0.9fr]' : 'xl:grid-cols-[1.6fr_0.7fr]'}`}>
          <FlowchartCanvas rules={rules} selectedNodeId={selectedNode?.node.id ?? null} onSelectNode={setSelectedNodeId} />

          <div className="space-y-4">
            <InspectorSection title="Inspector">
              {selectedNode ? (
                <>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-ink">
                        {selectedNode.isRoot ? 'Root group' : selectedNode.node.type === 'group' ? 'Group node' : 'Condition node'}
                      </div>
                      <p className="mt-1 text-sm text-slate-600">{summarizeNode(selectedNode.node)}</p>
                    </div>
                    {!selectedNode.isRoot && (
                      <button type="button" onClick={deleteSelectedNode} className="rounded-full bg-red-50 p-2 text-red-500">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>

                  {selectedNode.node.type === 'group' ? (
                    <>
                      <input
                        value={selectedNode.node.name ?? ''}
                        onChange={(event) =>
                          updateSelectedGroup((group) => ({ ...group, name: event.target.value }))
                        }
                        placeholder={selectedNode.isRoot ? 'Optional root group name' : 'Group name'}
                        className="w-full rounded-2xl border border-slate-200 px-4 py-3"
                      />
                      <select
                        value={selectedNode.node.combinator}
                        onChange={(event) =>
                          updateSelectedGroup((group) => ({ ...group, combinator: event.target.value as 'AND' | 'OR' }))
                        }
                        className="w-full rounded-2xl border border-slate-200 px-4 py-3"
                      >
                        <option value="AND">AND</option>
                        <option value="OR">OR</option>
                      </select>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <button type="button" onClick={() => addChild('condition')} className="rounded-full bg-mist px-4 py-3 text-sm font-semibold text-ocean">
                          <Plus size={14} className="mr-1 inline-block" />
                          Add condition
                        </button>
                        <button type="button" onClick={() => addChild('group')} className="rounded-full bg-sand px-4 py-3 text-sm font-semibold text-amber-900">
                          <Plus size={14} className="mr-1 inline-block" />
                          Add group
                        </button>
                      </div>
                      <p className="text-xs leading-5 text-slate-500">Groups define logical branches. Child nodes are attached visually under the selected group.</p>
                    </>
                  ) : (
                    <>
                      <select
                        value={selectedNode.node.field}
                        onChange={(event) => updateSelectedCondition((condition) => ({ ...condition, field: event.target.value }))}
                        className="w-full rounded-2xl border border-slate-200 px-4 py-3"
                      >
                        {usableColumns.map((column) => <option key={column} value={column}>{column}</option>)}
                      </select>
                      <div className="grid gap-3 md:grid-cols-2">
                        <select
                          value={selectedNode.node.data_type}
                          onChange={(event) => {
                            const dataType = event.target.value as 'text' | 'numeric' | 'date'
                            const nextOperator = dataType === 'text' ? 'CONTAINS' : '>'
                            updateSelectedCondition((condition) => ({
                              ...coerceConditionForOperator(condition, nextOperator),
                              data_type: dataType,
                            }))
                          }}
                          className="rounded-2xl border border-slate-200 px-4 py-3"
                        >
                          <option value="text">Text</option>
                          <option value="numeric">Numeric</option>
                          <option value="date">Date</option>
                        </select>
                        <select
                          value={selectedNode.node.operator}
                          onChange={(event) => updateSelectedCondition((condition) => coerceConditionForOperator(condition, event.target.value))}
                          className="rounded-2xl border border-slate-200 px-4 py-3"
                        >
                          {(selectedNode.node.data_type === 'text' ? textOperators : rangeOperators).map((operator) => (
                            <option key={operator} value={operator}>{operator}</option>
                          ))}
                        </select>
                      </div>
                      {selectedConditionMode === 'single' && (
                        <input
                          value={selectedNode.node.value ?? ''}
                          onChange={(event) => updateSelectedCondition((condition) => ({ ...condition, value: event.target.value }))}
                          placeholder="Value"
                          className="w-full rounded-2xl border border-slate-200 px-4 py-3"
                        />
                      )}
                      {selectedConditionMode === 'between' && (
                        <div className="grid gap-3 md:grid-cols-2">
                          <input
                            value={selectedNode.node.value ?? ''}
                            onChange={(event) => updateSelectedCondition((condition) => ({ ...condition, value: event.target.value }))}
                            placeholder="First value"
                            className="w-full rounded-2xl border border-slate-200 px-4 py-3"
                          />
                          <input
                            value={selectedNode.node.secondary_value ?? ''}
                            onChange={(event) => updateSelectedCondition((condition) => ({ ...condition, secondary_value: event.target.value }))}
                            placeholder="Second value"
                            className="w-full rounded-2xl border border-slate-200 px-4 py-3"
                          />
                        </div>
                      )}
                      {selectedConditionMode === 'multi_list' && (
                        <MultiValueEditor
                          values={normalizeMultiValueList(selectedNode.node.values ?? splitCommaValues(selectedNode.node.value ?? ''))}
                          onChange={(next) => updateSelectedCondition((condition) => ({
                            ...condition,
                            values: normalizeMultiValueList(next),
                            value: next[0] ?? '',
                            secondary_value: '',
                          }))}
                        />
                      )}
                    </>
                  )}
                </>
              ) : (
                <p className="text-sm text-slate-500">Select a node in the flowchart to inspect or edit it.</p>
              )}
            </InspectorSection>

            <InspectorSection title="Flowchart Rules">
              <p className="text-sm text-slate-600">This mode is no longer a sortable rule list. Nodes are visual summaries, and all configuration happens through selection.</p>
              <p className="text-sm text-slate-600">Use pan and zoom to navigate deeper trees. The AST JSON below stays synchronized with every valid change.</p>
            </InspectorSection>

            {mode === 'split' && (
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-950 p-4 text-xs text-cyan-200">
                <div className="mb-2 font-display text-sm uppercase tracking-[0.2em] text-cyan-100">Live syntax</div>
                <textarea
                  value={syntaxText}
                  onChange={(event) => handleSyntaxChange(event.target.value)}
                  spellCheck={false}
                  className="min-h-[26rem] w-full rounded-2xl border border-cyan-900 bg-slate-950 px-4 py-4 font-mono text-xs text-cyan-200 outline-none"
                />
                {syntaxError && <p className="mt-3 text-sm text-red-300">Syntax error: {syntaxError}</p>}
              </div>
            )}
          </div>
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
            <p className="text-sm font-semibold text-amber-900">Flowchart synchronization</p>
            <p className="mt-2 text-sm text-slate-700">Valid JSON updates the flowchart immediately. Node selection stays aligned to the same underlying AST whenever possible.</p>
            <div className="mt-4 rounded-2xl bg-white p-4 text-sm text-slate-600">
              <p className="font-semibold text-ink">Tips</p>
              <p className="mt-2">Use `type: "group"` with `children` for nested logic and `type: "condition"` for leaves.</p>
              <p className="mt-2">If a selected node disappears in JSON, the editor safely falls back to the `Must Have` root.</p>
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
          <p className="text-sm font-semibold text-amber-900">Versioned persistence</p>
          <p className="mt-2 text-sm text-slate-700">Every save still creates a new ruleset version. The flowchart changes only the visual interaction model, not the persisted AST contract.</p>
          <button type="button" onClick={handleSave} disabled={saving || !columns.length || Boolean(syntaxError)} className="mt-4 w-full rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
            {saving ? 'Saving...' : 'Save rule set'}
          </button>
        </div>
      </div>
    </section>
  )
}
