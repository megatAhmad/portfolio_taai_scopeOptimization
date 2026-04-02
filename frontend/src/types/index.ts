export type Project = {
  id: number
  name: string
  description: string | null
  created_at: string
}

export type ColumnProfile = {
  source: string
  inferred_type: 'text' | 'numeric' | 'date' | 'empty'
  sample_values: string[]
  null_ratio: number
}

export type MappingEntry = {
  source: string
  target: string
  include: boolean
  inferred_type: 'text' | 'numeric' | 'date' | 'empty'
  suggested_target?: string | null
}

export type MatchingConfig = {
  strategy: 'exact' | 'normalized' | 'fuzzy'
  fuzzy_threshold: number
}

export type EquipmentIdCleaningConfig = {
  enabled: boolean
  remove_bracketed_content: boolean
  bridge_bracket_gap_with_dash: boolean
  expand_compound_ids: boolean
  remove_whitespace: boolean
  uppercase: boolean
}

export type EquipmentIdAuditRecord = {
  source_row_index: number
  equipment_id_raw: string
  equipment_id_intermediate?: string | null
  equipment_id_final: string[]
  change_types: string[]
  parse_status: 'unchanged' | 'cleaned' | 'expanded' | 'ambiguous'
  notes: string[]
}

export type DerivedCondition = {
  column: string
  data_type: 'text' | 'numeric' | 'date'
  operator: string
  value?: string
  secondary_value?: string
}

export type DerivedColumn = {
  name: string
  conditions: DerivedCondition[]
  true_value: string
  false_value?: string
  null_value?: string
}

export type DerivedConditionAuditRecord = {
  column: string
  operator: string
  data_type: 'text' | 'numeric' | 'date'
  expected_value?: unknown
  secondary_value?: unknown
  actual_value?: unknown
  result?: boolean | null
}

export type DerivedColumnAuditRecord = {
  source_row_index: number
  derived_column: string
  output_value?: unknown
  branch_taken: 'true' | 'false' | 'null'
  conditions: DerivedConditionAuditRecord[]
}

export type DatasetInspection = {
  file_name: string
  file_type: 'csv' | 'excel'
  sheet_names: string[]
  selected_sheet: string | null
  columns: string[]
  preview_rows: Record<string, unknown>[]
  schema_profile: ColumnProfile[]
  mapping_suggestions: MappingEntry[]
  transformed_columns: string[]
  transformed_preview_rows: Record<string, unknown>[]
  equipment_id_audit: EquipmentIdAuditRecord[]
  derived_column_audit: DerivedColumnAuditRecord[]
  transformed_row_count: number
  changed_row_count: number
}

export type Dataset = {
  id: number
  project_id: number
  name: string
  role: string
  file_name: string
  sheet_name: string | null
  equipment_id_column: string
  canonical_join_column: string | null
  column_mapping: Record<string, string>
  mapping_rules: MappingEntry[]
  derived_columns: DerivedColumn[]
  preview_rows: Record<string, unknown>[]
  schema_profile: ColumnProfile[]
  matching_config: MatchingConfig
  equipment_id_cleaning_config: EquipmentIdCleaningConfig
  created_at: string
}

export type RuleConditionNode = {
  id: string
  type: 'condition'
  field: string
  data_type: 'text' | 'numeric' | 'date'
  operator: string
  value?: string
  secondary_value?: string
  values?: string[]
}

export type RuleGroupNode = {
  id: string
  type: 'group'
  name?: string
  combinator: 'AND' | 'OR'
  children: RuleNode[]
}

export type RuleNode = RuleConditionNode | RuleGroupNode

export type RuleAst = {
  must_have: RuleGroupNode
  good_to_have: RuleGroupNode
  fallback_label: string
}

export type RuleSet = {
  id: number
  project_id: number
  version_no: number
  name: string
  ast_json: RuleAst
  created_at: string
}

export type ConditionTrace = {
  node_id: string
  field: string
  operator: string
  data_type: string
  result: boolean | null
  actual_value?: unknown
  expected_value?: unknown
  secondary_value?: unknown
}

export type GroupTrace = {
  node_id: string
  combinator: string
  result: boolean
  children: TraceNode[]
}

export type TraceNode = ConditionTrace | GroupTrace

export type RowExplanation = {
  row_index: number
  equipment_id: string
  classification: string
  matched_rule: string
  rule_path: string[]
  source_fields: string[]
  condition_trace: TraceNode
}

export type ClassificationRun = {
  id: number
  project_id: number
  ruleset_id: number
  ruleset_version: number
  status: string
  summary: Record<string, number>
  columns: string[]
  total_rows: number
  created_at: string
}

export type ProjectDetail = {
  project: Project
  datasets: Dataset[]
  latest_ruleset: RuleSet | null
  latest_run: ClassificationRun | null
}

export type ClassificationRowsPage = {
  run_id: number
  rows: Record<string, unknown>[]
  explanations: RowExplanation[]
  columns: string[]
  total_rows: number
  offset: number
  limit: number
}

export type ClassificationResult = {
  run_id: number
  summary: Record<string, number>
  rows: Record<string, unknown>[]
  columns: string[]
  ruleset_version: number
  explanations: RowExplanation[]
  total_rows: number
  offset: number
  limit: number
}
