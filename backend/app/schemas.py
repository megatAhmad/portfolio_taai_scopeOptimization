from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectRead(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = {'from_attributes': True}


class SheetPreview(BaseModel):
    columns: list[str]
    preview_rows: list[dict[str, Any]]


class ColumnProfile(BaseModel):
    source: str
    inferred_type: Literal['text', 'numeric', 'date', 'empty']
    sample_values: list[str]
    null_ratio: float


class MappingEntry(BaseModel):
    source: str
    target: str
    include: bool = True
    inferred_type: Literal['text', 'numeric', 'date', 'empty'] = 'text'
    suggested_target: str | None = None


class MatchingConfig(BaseModel):
    strategy: Literal['exact', 'normalized', 'fuzzy'] = 'normalized'
    fuzzy_threshold: float = 0.82


class EquipmentIdCleaningConfig(BaseModel):
    enabled: bool = False
    remove_bracketed_content: bool = True
    bridge_bracket_gap_with_dash: bool = True
    expand_compound_ids: bool = True
    remove_whitespace: bool = True
    uppercase: bool = False


class EquipmentIdAuditRecord(BaseModel):
    source_row_index: int
    equipment_id_raw: str
    equipment_id_intermediate: str | None = None
    equipment_id_final: list[str] = Field(default_factory=list)
    change_types: list[str] = Field(default_factory=list)
    parse_status: Literal['unchanged', 'cleaned', 'expanded', 'ambiguous'] = 'unchanged'
    notes: list[str] = Field(default_factory=list)


class DerivedCondition(BaseModel):
    column: str
    data_type: Literal['text', 'numeric', 'date']
    operator: str
    value: Any | None = None
    secondary_value: Any | None = None


class DerivedColumnDefinition(BaseModel):
    name: str
    conditions: list[DerivedCondition] = Field(default_factory=list)
    true_value: str
    false_value: str | None = None
    null_value: str | None = None


class DerivedConditionAuditRecord(BaseModel):
    column: str
    operator: str
    data_type: Literal['text', 'numeric', 'date']
    expected_value: Any | None = None
    secondary_value: Any | None = None
    actual_value: Any | None = None
    result: bool | None = None


class DerivedColumnAuditRecord(BaseModel):
    source_row_index: int
    derived_column: str
    output_value: Any | None = None
    branch_taken: Literal['true', 'false', 'null']
    conditions: list[DerivedConditionAuditRecord] = Field(default_factory=list)


class DatasetInspectionResponse(BaseModel):
    file_name: str
    file_type: Literal['csv', 'excel']
    sheet_names: list[str] = Field(default_factory=list)
    selected_sheet: str | None = None
    columns: list[str] = Field(default_factory=list)
    preview_rows: list[dict[str, Any]] = Field(default_factory=list)
    schema_profile: list[ColumnProfile] = Field(default_factory=list)
    mapping_suggestions: list[MappingEntry] = Field(default_factory=list)
    transformed_columns: list[str] = Field(default_factory=list)
    transformed_preview_rows: list[dict[str, Any]] = Field(default_factory=list)
    equipment_id_audit: list[EquipmentIdAuditRecord] = Field(default_factory=list)
    derived_column_audit: list[DerivedColumnAuditRecord] = Field(default_factory=list)
    transformed_row_count: int = 0
    changed_row_count: int = 0


class DatasetRead(BaseModel):
    id: int
    project_id: int
    name: str
    role: str
    file_name: str
    sheet_name: str | None
    equipment_id_column: str
    canonical_join_column: str | None
    column_mapping: dict[str, str]
    mapping_rules: list[MappingEntry]
    derived_columns: list[DerivedColumnDefinition]
    preview_rows: list[dict[str, Any]]
    schema_profile: list[ColumnProfile]
    matching_config: MatchingConfig
    equipment_id_cleaning_config: EquipmentIdCleaningConfig
    created_at: datetime

    model_config = {'from_attributes': True}


class RuleConditionNode(BaseModel):
    id: str
    type: Literal['condition']
    field: str
    data_type: Literal['text', 'numeric', 'date']
    operator: str
    value: Any | None = None
    secondary_value: Any | None = None
    values: list[Any] | None = None


class RuleGroupNode(BaseModel):
    id: str
    type: Literal['group']
    name: str | None = None
    combinator: Literal['AND', 'OR'] = 'AND'
    children: list['RuleNode'] = Field(default_factory=list)


RuleNode = RuleConditionNode | RuleGroupNode
RuleGroupNode.model_rebuild()


class RuleSetAst(BaseModel):
    must_have: RuleGroupNode
    good_to_have: RuleGroupNode
    fallback_label: str = 'Not Needed'

    @model_validator(mode='after')
    def ensure_unique_ids(self):
        seen: set[str] = set()

        def walk(node: RuleNode):
            if node.id in seen:
                raise ValueError(f'duplicate rule node id: {node.id}')
            seen.add(node.id)
            if isinstance(node, RuleGroupNode):
                for child in node.children:
                    walk(child)

        walk(self.must_have)
        walk(self.good_to_have)
        return self


class RuleSetPayload(BaseModel):
    name: str = 'Default Rule Set'
    ast_json: RuleSetAst


class RuleSetRead(BaseModel):
    id: int
    project_id: int
    version_no: int
    name: str
    ast_json: RuleSetAst
    created_at: datetime

    model_config = {'from_attributes': True}


class ConditionTrace(BaseModel):
    node_id: str
    field: str
    operator: str
    data_type: str
    result: bool | None
    actual_value: Any | None = None
    expected_value: Any | None = None
    secondary_value: Any | None = None


class GroupTrace(BaseModel):
    node_id: str
    combinator: str
    result: bool
    children: list['TraceNode']


TraceNode = ConditionTrace | GroupTrace
GroupTrace.model_rebuild()


class RowExplanation(BaseModel):
    row_index: int
    equipment_id: str
    classification: str
    matched_rule: str
    rule_path: list[str]
    source_fields: list[str]
    condition_trace: TraceNode


class ClassificationRunRead(BaseModel):
    id: int
    project_id: int
    ruleset_id: int
    ruleset_version: int
    status: str
    summary: dict[str, int]
    columns: list[str]
    total_rows: int
    created_at: datetime

    model_config = {'from_attributes': True}


class ClassificationRowsPage(BaseModel):
    run_id: int
    rows: list[dict[str, Any]]
    explanations: list[RowExplanation]
    columns: list[str]
    total_rows: int
    offset: int
    limit: int


class ClassificationResult(BaseModel):
    run_id: int
    summary: dict[str, int]
    rows: list[dict[str, Any]]
    columns: list[str]
    ruleset_version: int
    explanations: list[RowExplanation]
    total_rows: int
    offset: int
    limit: int
