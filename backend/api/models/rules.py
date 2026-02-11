"""
Pydantic models for rules API endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class RuleTypeEnum(str, Enum):
    """Types of rules."""
    NUMERIC = "numeric"
    TEXT = "text"
    DATE = "date"
    LOOKUP = "lookup"
    AGGREGATION = "aggregation"
    CONDITIONAL = "conditional"
    BUSINESS = "business"


class DecisionOutcomeEnum(str, Enum):
    """Possible decision outcomes."""
    ACCEPTED = "ACCEPTED"
    RECONSIDER = "RECONSIDER"
    REJECTED = "REJECTED"


class RuleConditionModel(BaseModel):
    """Model for a rule condition."""
    
    field: str
    rule_type: RuleTypeEnum
    operator: str
    value: Any
    value_end: Optional[Any] = None
    lookup_dataset: Optional[str] = None
    lookup_field: Optional[str] = None


class StandardRuleRequest(BaseModel):
    """Request model for creating a standard rule."""
    
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    conditions: List[RuleConditionModel]
    logical_operator: str = Field(default="AND", pattern="^(AND|OR)$")
    outcome: DecisionOutcomeEnum
    priority: int = Field(default=1, ge=1, le=100)
    enabled: bool = True


class ConditionRuleRequest(BaseModel):
    """Request model for creating a condition-based rule."""
    
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    if_conditions: List[RuleConditionModel]
    then_outcome: DecisionOutcomeEnum
    else_outcome: Optional[DecisionOutcomeEnum] = None
    priority: int = Field(default=1, ge=1, le=100)
    enabled: bool = True


class FunctionRuleRequest(BaseModel):
    """Request model for creating a function-based rule."""
    
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    function_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    outcome_mapping: Dict[str, DecisionOutcomeEnum]
    priority: int = Field(default=1, ge=1, le=100)
    enabled: bool = True


class AIRuleRequest(BaseModel):
    """Request model for creating an AI-based rule."""
    
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    prompt_template: str
    fields_to_analyze: List[str]
    outcome_mapping: Dict[str, DecisionOutcomeEnum]
    priority: int = Field(default=1, ge=1, le=100)
    enabled: bool = True


class RuleResponse(BaseModel):
    """Response model for a rule."""
    
    rule_id: str
    name: str
    description: Optional[str]
    rule_type: str  # standard, condition, function, ai
    priority: int
    enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RuleListResponse(BaseModel):
    """Response model for list of rules."""
    
    rules: List[RuleResponse]
    total_count: int


class RuleUpdateRequest(BaseModel):
    """Request model for updating a rule."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=100)
    enabled: Optional[bool] = None


class TemplateListResponse(BaseModel):
    """Response model for available templates."""
    
    templates: List[Dict[str, Any]]


class LoadTemplateRequest(BaseModel):
    """Request model for loading a template."""
    
    template_name: str


class SaveTemplateRequest(BaseModel):
    """Request model for saving current rules as template."""
    
    template_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class FunctionListResponse(BaseModel):
    """Response model for available predefined functions."""
    
    functions: List[Dict[str, Any]]


class RuleConnectionRequest(BaseModel):
    """Request model for creating a rule connection."""
    
    from_rule_id: str
    to_rule_id: str
    connection_type: str = Field(default="sequential", pattern="^(sequential|conditional|parallel)$")


class RuleConnectionResponse(BaseModel):
    """Response model for a rule connection."""
    
    connection_id: str
    from_rule_id: str
    to_rule_id: str
    connection_type: str


class RuleConnectionsListResponse(BaseModel):
    """Response model for list of rule connections."""
    
    connections: List[RuleConnectionResponse]
