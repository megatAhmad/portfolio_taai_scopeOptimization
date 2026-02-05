"""
Supporting Datasets Module for MWCS.

Defines hierarchical classification masters that drive accept/consider/reject decisions:
- Equipment Classification Master (Critical/Standard/Low Priority)
- Work Type Categorization Reference (Emergency/Planned/Deferred)
- Equipment Redundancy Master (Single/Dual/No Dependency/Uncertain)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class EquipmentClassification(str, Enum):
    """Equipment classification hierarchy."""
    CRITICAL = "Critical"
    STANDARD = "Standard"
    LOW_PRIORITY = "Low Priority"
    UNCLASSIFIED = "Unclassified"


class WorkTypeCategory(str, Enum):
    """Work type categorization."""
    EMERGENCY = "Emergency"
    PLANNED = "Planned"
    DEFERRED = "Deferred"
    UNCLASSIFIED = "Unclassified"


class EquipmentRedundancy(str, Enum):
    """Equipment redundancy classification."""
    SINGLE_DEPENDENCY = "Single Dependency"
    DUAL_DEPENDENCY = "Dual Dependency"
    NO_DEPENDENCY = "No Dependency"
    UNCERTAIN = "Uncertain"


class DecisionCategory(str, Enum):
    """Final decision categories."""
    ACCEPTED = "ACCEPTED"
    RECONSIDER = "RECONSIDER"
    REJECTED = "REJECTED"


@dataclass
class ClassificationRule:
    """Rule for mapping classifications to decisions."""
    equipment_class: Optional[EquipmentClassification] = None
    work_type: Optional[WorkTypeCategory] = None
    redundancy: Optional[EquipmentRedundancy] = None
    decision: DecisionCategory = DecisionCategory.RECONSIDER
    priority: int = 0
    description: str = ""


# Default decision matrix based on classifications
DEFAULT_DECISION_MATRIX = [
    # Critical equipment rules
    ClassificationRule(
        equipment_class=EquipmentClassification.CRITICAL,
        work_type=WorkTypeCategory.EMERGENCY,
        decision=DecisionCategory.ACCEPTED,
        priority=100,
        description="Critical equipment with emergency work - always accept"
    ),
    ClassificationRule(
        equipment_class=EquipmentClassification.CRITICAL,
        work_type=WorkTypeCategory.PLANNED,
        redundancy=EquipmentRedundancy.SINGLE_DEPENDENCY,
        decision=DecisionCategory.ACCEPTED,
        priority=95,
        description="Critical equipment, planned work, single dependency - accept"
    ),
    ClassificationRule(
        equipment_class=EquipmentClassification.CRITICAL,
        work_type=WorkTypeCategory.PLANNED,
        redundancy=EquipmentRedundancy.DUAL_DEPENDENCY,
        decision=DecisionCategory.RECONSIDER,
        priority=90,
        description="Critical equipment, planned work, dual dependency - review"
    ),
    ClassificationRule(
        equipment_class=EquipmentClassification.CRITICAL,
        work_type=WorkTypeCategory.DEFERRED,
        decision=DecisionCategory.RECONSIDER,
        priority=85,
        description="Critical equipment with deferred work - needs review"
    ),

    # Standard equipment rules
    ClassificationRule(
        equipment_class=EquipmentClassification.STANDARD,
        work_type=WorkTypeCategory.EMERGENCY,
        decision=DecisionCategory.ACCEPTED,
        priority=80,
        description="Standard equipment with emergency work - accept"
    ),
    ClassificationRule(
        equipment_class=EquipmentClassification.STANDARD,
        work_type=WorkTypeCategory.PLANNED,
        redundancy=EquipmentRedundancy.SINGLE_DEPENDENCY,
        decision=DecisionCategory.ACCEPTED,
        priority=75,
        description="Standard equipment, planned, single dependency - accept"
    ),
    ClassificationRule(
        equipment_class=EquipmentClassification.STANDARD,
        work_type=WorkTypeCategory.PLANNED,
        redundancy=EquipmentRedundancy.NO_DEPENDENCY,
        decision=DecisionCategory.RECONSIDER,
        priority=70,
        description="Standard equipment, planned, no dependency - review"
    ),
    ClassificationRule(
        equipment_class=EquipmentClassification.STANDARD,
        work_type=WorkTypeCategory.DEFERRED,
        decision=DecisionCategory.REJECTED,
        priority=65,
        description="Standard equipment with deferred work - reject"
    ),

    # Low priority equipment rules
    ClassificationRule(
        equipment_class=EquipmentClassification.LOW_PRIORITY,
        work_type=WorkTypeCategory.EMERGENCY,
        decision=DecisionCategory.RECONSIDER,
        priority=60,
        description="Low priority equipment with emergency - review"
    ),
    ClassificationRule(
        equipment_class=EquipmentClassification.LOW_PRIORITY,
        work_type=WorkTypeCategory.PLANNED,
        decision=DecisionCategory.REJECTED,
        priority=55,
        description="Low priority equipment with planned work - reject"
    ),
    ClassificationRule(
        equipment_class=EquipmentClassification.LOW_PRIORITY,
        work_type=WorkTypeCategory.DEFERRED,
        decision=DecisionCategory.REJECTED,
        priority=50,
        description="Low priority equipment with deferred work - reject"
    ),
]


@dataclass
class EquipmentClassificationMaster:
    """Equipment Classification Master dataset."""
    data: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Column mappings
    ASSET_ID_COL = "Asset ID"
    ASSET_TYPE_COL = "Asset Type"
    CLASSIFICATION_COL = "Classification"
    CRITICALITY_SCORE_COL = "Criticality Score"
    BUSINESS_IMPACT_COL = "Business Impact"
    SAFETY_IMPACT_COL = "Safety Impact"

    def __post_init__(self):
        if self.data.empty:
            self.data = self._create_default_schema()

    def _create_default_schema(self) -> pd.DataFrame:
        """Create empty DataFrame with proper schema."""
        return pd.DataFrame(columns=[
            self.ASSET_ID_COL,
            self.ASSET_TYPE_COL,
            self.CLASSIFICATION_COL,
            self.CRITICALITY_SCORE_COL,
            self.BUSINESS_IMPACT_COL,
            self.SAFETY_IMPACT_COL,
        ])

    def get_classification(self, asset_id: str) -> EquipmentClassification:
        """Get equipment classification for an asset."""
        if self.data.empty:
            return EquipmentClassification.UNCLASSIFIED

        matches = self.data[self.data[self.ASSET_ID_COL] == asset_id]
        if matches.empty:
            return EquipmentClassification.UNCLASSIFIED

        classification = matches.iloc[0][self.CLASSIFICATION_COL]
        try:
            return EquipmentClassification(classification)
        except ValueError:
            return EquipmentClassification.UNCLASSIFIED

    def get_criticality_score(self, asset_id: str) -> float:
        """Get criticality score for an asset."""
        if self.data.empty:
            return 0.0

        matches = self.data[self.data[self.ASSET_ID_COL] == asset_id]
        if matches.empty:
            return 0.0

        return float(matches.iloc[0].get(self.CRITICALITY_SCORE_COL, 0.0))

    def load_from_dataframe(self, df: pd.DataFrame) -> None:
        """Load data from a DataFrame."""
        self.data = df.copy()
        logger.info(f"Loaded {len(df)} equipment classifications")


@dataclass
class WorkTypeCategorization:
    """Work Type Categorization Reference dataset."""
    data: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Column mappings
    WORK_TYPE_COL = "Work Type"
    CATEGORY_COL = "Category"
    KEYWORDS_COL = "Keywords"
    PRIORITY_MODIFIER_COL = "Priority Modifier"
    SLA_HOURS_COL = "SLA Hours"

    def __post_init__(self):
        if self.data.empty:
            self.data = self._create_default_schema()

    def _create_default_schema(self) -> pd.DataFrame:
        """Create empty DataFrame with proper schema."""
        return pd.DataFrame(columns=[
            self.WORK_TYPE_COL,
            self.CATEGORY_COL,
            self.KEYWORDS_COL,
            self.PRIORITY_MODIFIER_COL,
            self.SLA_HOURS_COL,
        ])

    def get_category(self, work_type: str) -> WorkTypeCategory:
        """Get work type category."""
        if self.data.empty:
            return WorkTypeCategory.UNCLASSIFIED

        # Exact match first
        matches = self.data[self.data[self.WORK_TYPE_COL].str.lower() == work_type.lower()]
        if not matches.empty:
            category = matches.iloc[0][self.CATEGORY_COL]
            try:
                return WorkTypeCategory(category)
            except ValueError:
                pass

        # Keyword-based matching
        for _, row in self.data.iterrows():
            keywords = str(row.get(self.KEYWORDS_COL, "")).lower().split(",")
            if any(kw.strip() in work_type.lower() for kw in keywords if kw.strip()):
                try:
                    return WorkTypeCategory(row[self.CATEGORY_COL])
                except ValueError:
                    pass

        return WorkTypeCategory.UNCLASSIFIED

    def categorize_by_description(self, description: str) -> WorkTypeCategory:
        """Categorize work based on description keywords."""
        description_lower = description.lower()

        # Emergency keywords
        emergency_keywords = ["emergency", "urgent", "critical", "breakdown", "failure", "safety"]
        if any(kw in description_lower for kw in emergency_keywords):
            return WorkTypeCategory.EMERGENCY

        # Planned keywords
        planned_keywords = ["scheduled", "planned", "preventive", "routine", "inspection"]
        if any(kw in description_lower for kw in planned_keywords):
            return WorkTypeCategory.PLANNED

        # Deferred keywords
        deferred_keywords = ["deferred", "postpone", "later", "backlog", "low priority"]
        if any(kw in description_lower for kw in deferred_keywords):
            return WorkTypeCategory.DEFERRED

        return WorkTypeCategory.UNCLASSIFIED

    def load_from_dataframe(self, df: pd.DataFrame) -> None:
        """Load data from a DataFrame."""
        self.data = df.copy()
        logger.info(f"Loaded {len(df)} work type categorizations")


@dataclass
class EquipmentRedundancyMaster:
    """Equipment Redundancy Master dataset."""
    data: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Column mappings
    ASSET_ID_COL = "Asset ID"
    REDUNDANCY_TYPE_COL = "Redundancy Type"
    BACKUP_ASSET_COL = "Backup Asset ID"
    FAILOVER_TIME_COL = "Failover Time (min)"
    DEPENDENCY_COUNT_COL = "Dependency Count"
    DEPENDENCY_ASSETS_COL = "Dependent Assets"

    def __post_init__(self):
        if self.data.empty:
            self.data = self._create_default_schema()

    def _create_default_schema(self) -> pd.DataFrame:
        """Create empty DataFrame with proper schema."""
        return pd.DataFrame(columns=[
            self.ASSET_ID_COL,
            self.REDUNDANCY_TYPE_COL,
            self.BACKUP_ASSET_COL,
            self.FAILOVER_TIME_COL,
            self.DEPENDENCY_COUNT_COL,
            self.DEPENDENCY_ASSETS_COL,
        ])

    def get_redundancy(self, asset_id: str) -> EquipmentRedundancy:
        """Get redundancy classification for an asset."""
        if self.data.empty:
            return EquipmentRedundancy.UNCERTAIN

        matches = self.data[self.data[self.ASSET_ID_COL] == asset_id]
        if matches.empty:
            return EquipmentRedundancy.UNCERTAIN

        redundancy_type = matches.iloc[0][self.REDUNDANCY_TYPE_COL]
        try:
            return EquipmentRedundancy(redundancy_type)
        except ValueError:
            return EquipmentRedundancy.UNCERTAIN

    def get_dependency_count(self, asset_id: str) -> int:
        """Get number of dependencies for an asset."""
        if self.data.empty:
            return 0

        matches = self.data[self.data[self.ASSET_ID_COL] == asset_id]
        if matches.empty:
            return 0

        return int(matches.iloc[0].get(self.DEPENDENCY_COUNT_COL, 0))

    def has_backup(self, asset_id: str) -> bool:
        """Check if asset has a backup."""
        if self.data.empty:
            return False

        matches = self.data[self.data[self.ASSET_ID_COL] == asset_id]
        if matches.empty:
            return False

        backup = matches.iloc[0].get(self.BACKUP_ASSET_COL, "")
        return bool(backup and str(backup).strip())

    def load_from_dataframe(self, df: pd.DataFrame) -> None:
        """Load data from a DataFrame."""
        self.data = df.copy()
        logger.info(f"Loaded {len(df)} equipment redundancy records")


class SupportingDatasetManager:
    """Manages all supporting datasets and their interactions."""

    def __init__(self):
        self.equipment_classification = EquipmentClassificationMaster()
        self.work_type_categorization = WorkTypeCategorization()
        self.equipment_redundancy = EquipmentRedundancyMaster()
        self.decision_matrix = DEFAULT_DECISION_MATRIX.copy()

    def load_from_excel_sheets(self, sheets: dict[str, pd.DataFrame]) -> None:
        """Load supporting datasets from Excel sheets."""
        # Try to load Equipment Classification
        for name in ["Equipment Classification", "EquipmentClassification", "Equipment_Classification"]:
            if name in sheets:
                self.equipment_classification.load_from_dataframe(sheets[name])
                break

        # Try to load Work Type Categorization
        for name in ["Work Type Categorization", "WorkTypeCategorization", "Work_Type_Categorization"]:
            if name in sheets:
                self.work_type_categorization.load_from_dataframe(sheets[name])
                break

        # Try to load Equipment Redundancy
        for name in ["Equipment Redundancy", "EquipmentRedundancy", "Equipment_Redundancy"]:
            if name in sheets:
                self.equipment_redundancy.load_from_dataframe(sheets[name])
                break

    def classify_work_item(
        self,
        asset_id: str,
        work_type: str,
        description: str,
    ) -> dict[str, Any]:
        """Classify a work item based on supporting datasets."""
        # Get classifications
        equipment_class = self.equipment_classification.get_classification(asset_id)
        criticality_score = self.equipment_classification.get_criticality_score(asset_id)

        # Get work type category - try exact match first, then description
        work_category = self.work_type_categorization.get_category(work_type)
        if work_category == WorkTypeCategory.UNCLASSIFIED:
            work_category = self.work_type_categorization.categorize_by_description(description)

        # Get redundancy
        redundancy = self.equipment_redundancy.get_redundancy(asset_id)
        dependency_count = self.equipment_redundancy.get_dependency_count(asset_id)
        has_backup = self.equipment_redundancy.has_backup(asset_id)

        # Determine decision based on matrix
        decision = self._apply_decision_matrix(equipment_class, work_category, redundancy)

        return {
            "equipment_classification": equipment_class.value,
            "criticality_score": criticality_score,
            "work_type_category": work_category.value,
            "redundancy_type": redundancy.value,
            "dependency_count": dependency_count,
            "has_backup": has_backup,
            "recommended_decision": decision.value,
        }

    def _apply_decision_matrix(
        self,
        equipment_class: EquipmentClassification,
        work_category: WorkTypeCategory,
        redundancy: EquipmentRedundancy,
    ) -> DecisionCategory:
        """Apply decision matrix to determine outcome."""
        best_match = None
        best_priority = -1

        for rule in self.decision_matrix:
            # Check if rule matches
            if rule.equipment_class and rule.equipment_class != equipment_class:
                continue
            if rule.work_type and rule.work_type != work_category:
                continue
            if rule.redundancy and rule.redundancy != redundancy:
                continue

            # This rule matches - check priority
            if rule.priority > best_priority:
                best_match = rule
                best_priority = rule.priority

        if best_match:
            return best_match.decision

        return DecisionCategory.RECONSIDER

    def get_classification_summary(self) -> dict[str, int]:
        """Get summary of classifications."""
        return {
            "equipment_classifications": len(self.equipment_classification.data),
            "work_type_categories": len(self.work_type_categorization.data),
            "redundancy_records": len(self.equipment_redundancy.data),
            "decision_rules": len(self.decision_matrix),
        }


def generate_sample_equipment_classification(num_assets: int = 50) -> pd.DataFrame:
    """Generate sample equipment classification data."""
    import random
    random.seed(44)

    classifications = [
        EquipmentClassification.CRITICAL.value,
        EquipmentClassification.STANDARD.value,
        EquipmentClassification.LOW_PRIORITY.value,
    ]
    weights = [0.2, 0.5, 0.3]  # 20% critical, 50% standard, 30% low priority

    data = []
    for i in range(1, num_assets + 1):
        classification = random.choices(classifications, weights=weights)[0]
        criticality = {
            EquipmentClassification.CRITICAL.value: random.uniform(80, 100),
            EquipmentClassification.STANDARD.value: random.uniform(40, 79),
            EquipmentClassification.LOW_PRIORITY.value: random.uniform(10, 39),
        }[classification]

        data.append({
            "Asset ID": f"AST-{1000 + i}",
            "Asset Type": random.choice(["Motor", "Pump", "Conveyor", "HVAC", "Compressor", "Sensor"]),
            "Classification": classification,
            "Criticality Score": round(criticality, 1),
            "Business Impact": random.choice(["High", "Medium", "Low"]),
            "Safety Impact": random.choice(["High", "Medium", "Low"]),
        })

    return pd.DataFrame(data)


def generate_sample_work_type_categorization() -> pd.DataFrame:
    """Generate sample work type categorization data."""
    data = [
        {
            "Work Type": "Emergency Repair",
            "Category": WorkTypeCategory.EMERGENCY.value,
            "Keywords": "emergency,urgent,breakdown,failure",
            "Priority Modifier": 1.5,
            "SLA Hours": 4,
        },
        {
            "Work Type": "Corrective Maintenance",
            "Category": WorkTypeCategory.EMERGENCY.value,
            "Keywords": "corrective,fix,repair,restore",
            "Priority Modifier": 1.3,
            "SLA Hours": 8,
        },
        {
            "Work Type": "Preventive Maintenance",
            "Category": WorkTypeCategory.PLANNED.value,
            "Keywords": "preventive,scheduled,routine,periodic",
            "Priority Modifier": 1.0,
            "SLA Hours": 48,
        },
        {
            "Work Type": "Inspection",
            "Category": WorkTypeCategory.PLANNED.value,
            "Keywords": "inspection,check,survey,audit",
            "Priority Modifier": 0.9,
            "SLA Hours": 72,
        },
        {
            "Work Type": "Calibration",
            "Category": WorkTypeCategory.PLANNED.value,
            "Keywords": "calibration,calibrate,adjust,tune",
            "Priority Modifier": 0.9,
            "SLA Hours": 48,
        },
        {
            "Work Type": "Upgrade",
            "Category": WorkTypeCategory.DEFERRED.value,
            "Keywords": "upgrade,improve,enhance,modernize",
            "Priority Modifier": 0.7,
            "SLA Hours": 168,
        },
        {
            "Work Type": "Backlog",
            "Category": WorkTypeCategory.DEFERRED.value,
            "Keywords": "backlog,deferred,postponed,later",
            "Priority Modifier": 0.5,
            "SLA Hours": 336,
        },
    ]

    return pd.DataFrame(data)


def generate_sample_equipment_redundancy(num_assets: int = 50) -> pd.DataFrame:
    """Generate sample equipment redundancy data."""
    import random
    random.seed(45)

    redundancy_types = [
        EquipmentRedundancy.SINGLE_DEPENDENCY.value,
        EquipmentRedundancy.DUAL_DEPENDENCY.value,
        EquipmentRedundancy.NO_DEPENDENCY.value,
        EquipmentRedundancy.UNCERTAIN.value,
    ]
    weights = [0.3, 0.25, 0.35, 0.1]

    data = []
    for i in range(1, num_assets + 1):
        asset_id = f"AST-{1000 + i}"
        redundancy = random.choices(redundancy_types, weights=weights)[0]

        # Determine backup and dependencies based on redundancy
        has_backup = redundancy in [
            EquipmentRedundancy.DUAL_DEPENDENCY.value,
            EquipmentRedundancy.NO_DEPENDENCY.value,
        ]
        backup_id = f"AST-{1000 + random.randint(1, num_assets)}" if has_backup else ""

        dep_count = {
            EquipmentRedundancy.SINGLE_DEPENDENCY.value: 1,
            EquipmentRedundancy.DUAL_DEPENDENCY.value: 2,
            EquipmentRedundancy.NO_DEPENDENCY.value: 0,
            EquipmentRedundancy.UNCERTAIN.value: random.randint(0, 3),
        }[redundancy]

        # Generate dependent assets
        dependent_assets = []
        for _ in range(random.randint(0, 3)):
            dependent_assets.append(f"AST-{1000 + random.randint(1, num_assets)}")

        data.append({
            "Asset ID": asset_id,
            "Redundancy Type": redundancy,
            "Backup Asset ID": backup_id,
            "Failover Time (min)": random.randint(5, 60) if has_backup else 0,
            "Dependency Count": dep_count,
            "Dependent Assets": ",".join(dependent_assets) if dependent_assets else "",
        })

    return pd.DataFrame(data)
