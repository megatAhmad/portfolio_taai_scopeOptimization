"""
Rule Configuration Manager - handles persistence of rules and connections.

Provides session state management with file-based backup for rule configurations.
"""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.enhanced_rule_engine import (
    AIGeneratedRule,
    ConditionOperator,
    ConditionRule,
    EnhancedRuleEngine,
    FunctionRule,
    RuleConnection,
    RuleType,
)
from src.supporting_datasets import (
    DecisionCategory,
    EquipmentClassification,
    EquipmentRedundancy,
    SupportingDatasetManager,
    WorkTypeCategory,
)

logger = logging.getLogger(__name__)


@dataclass
class RuleConfigMetadata:
    """Metadata for a rule configuration."""

    name: str
    description: str = ""
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    author: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class RuleConfiguration:
    """Complete rule configuration with metadata."""

    metadata: RuleConfigMetadata
    rules: list[dict[str, Any]] = field(default_factory=list)
    connections: list[dict[str, Any]] = field(default_factory=list)
    supporting_datasets: dict[str, Any] = field(default_factory=dict)
    decision_matrix: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "metadata": asdict(self.metadata),
            "rules": self.rules,
            "connections": self.connections,
            "supporting_datasets": self.supporting_datasets,
            "decision_matrix": self.decision_matrix,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuleConfiguration":
        """Create configuration from dictionary."""
        metadata = RuleConfigMetadata(**data.get("metadata", {"name": "Unnamed"}))
        return cls(
            metadata=metadata,
            rules=data.get("rules", []),
            connections=data.get("connections", []),
            supporting_datasets=data.get("supporting_datasets", {}),
            decision_matrix=data.get("decision_matrix", {}),
        )


class RuleConfigManager:
    """
    Manages rule configurations with session state and file persistence.

    Features:
    - Session state storage for active configuration
    - File-based backup and restore
    - Import/export of configurations
    - Configuration versioning
    - Template management
    """

    DEFAULT_CONFIG_DIR = "templates"
    DEFAULT_BACKUP_DIR = "backups"
    CONFIG_EXTENSION = ".json"

    def __init__(
        self,
        config_dir: Optional[str] = None,
        backup_dir: Optional[str] = None,
        auto_backup: bool = True,
    ):
        """Initialize the configuration manager.

        Args:
            config_dir: Directory for saved configurations
            backup_dir: Directory for automatic backups
            auto_backup: Whether to auto-backup on changes
        """
        self.config_dir = Path(config_dir or self.DEFAULT_CONFIG_DIR)
        self.backup_dir = Path(backup_dir or self.DEFAULT_BACKUP_DIR)
        self.auto_backup = auto_backup

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # In-memory state (session state substitute when not in Streamlit)
        self._session_state: dict[str, Any] = {}
        self._active_config: Optional[RuleConfiguration] = None
        self._rule_engine: Optional[EnhancedRuleEngine] = None
        self._dataset_manager: Optional[SupportingDatasetManager] = None

    def initialize_session(self, session_state: Optional[dict] = None) -> None:
        """Initialize or restore session state.

        Args:
            session_state: Streamlit session_state or dict for testing
        """
        if session_state is not None:
            self._session_state = session_state

        # Initialize default keys if not present
        defaults = {
            "rule_config": None,
            "rule_engine": None,
            "dataset_manager": None,
            "config_dirty": False,
            "last_backup": None,
        }

        for key, default_value in defaults.items():
            if key not in self._session_state:
                self._session_state[key] = default_value

        # Restore from backup if available and no active config
        if self._session_state["rule_config"] is None:
            latest_backup = self._get_latest_backup()
            if latest_backup:
                try:
                    self.load_config(latest_backup)
                    logger.info(f"Restored configuration from backup: {latest_backup}")
                except Exception as e:
                    logger.warning(f"Failed to restore from backup: {e}")

    def new_config(self, name: str, description: str = "") -> RuleConfiguration:
        """Create a new rule configuration.

        Args:
            name: Configuration name
            description: Configuration description

        Returns:
            New RuleConfiguration instance
        """
        metadata = RuleConfigMetadata(name=name, description=description)
        config = RuleConfiguration(metadata=metadata)

        self._active_config = config
        self._rule_engine = EnhancedRuleEngine()
        self._dataset_manager = SupportingDatasetManager()

        # Update session state
        self._session_state["rule_config"] = config.to_dict()
        self._session_state["rule_engine"] = self._rule_engine.to_dict()
        self._session_state["config_dirty"] = True

        if self.auto_backup:
            self._create_backup()

        return config

    def get_active_config(self) -> Optional[RuleConfiguration]:
        """Get the active configuration."""
        if self._active_config is None and self._session_state.get("rule_config"):
            self._active_config = RuleConfiguration.from_dict(
                self._session_state["rule_config"]
            )
        return self._active_config

    def get_rule_engine(self) -> Optional[EnhancedRuleEngine]:
        """Get the active rule engine."""
        if self._rule_engine is None and self._session_state.get("rule_engine"):
            self._rule_engine = EnhancedRuleEngine.from_dict(
                self._session_state["rule_engine"]
            )
        return self._rule_engine

    def get_dataset_manager(self) -> SupportingDatasetManager:
        """Get the dataset manager."""
        if self._dataset_manager is None:
            self._dataset_manager = SupportingDatasetManager()
        return self._dataset_manager

    def add_condition_rule(
        self,
        rule_id: str,
        name: str,
        column: str,
        operator: ConditionOperator,
        value: Any,
        outcome: str = "RECONSIDER",
        description: str = "",
        priority: int = 0,
        enabled: bool = True,
    ) -> ConditionRule:
        """Add a condition-based rule.

        Args:
            rule_id: Unique rule identifier
            name: Rule name
            column: Column to evaluate
            operator: Comparison operator
            value: Value to compare against
            outcome: Decision outcome if rule matches
            description: Rule description
            priority: Rule priority (higher = evaluated first)
            enabled: Whether rule is active

        Returns:
            Created ConditionRule
        """
        engine = self.get_rule_engine()
        if engine is None:
            raise ValueError("No active configuration. Call new_config() first.")

        rule = ConditionRule.create_simple(
            rule_id=rule_id,
            name=name,
            column=column,
            operator=operator,
            value=value,
            outcome=outcome,
            description=description,
            priority=priority,
            enabled=enabled,
        )

        engine.add_rule(rule)
        self._sync_to_session()

        return rule

    def add_function_rule(
        self,
        rule_id: str,
        name: str,
        function_name: str,
        parameters: dict[str, Any],
        outcome: str = "RECONSIDER",
        description: str = "",
        priority: int = 0,
        enabled: bool = True,
    ) -> FunctionRule:
        """Add a function-based rule.

        Args:
            rule_id: Unique rule identifier
            name: Rule name
            function_name: Name of predefined function to call
            parameters: Function parameters
            outcome: Decision outcome if function returns True
            description: Rule description
            priority: Rule priority
            enabled: Whether rule is active

        Returns:
            Created FunctionRule
        """
        engine = self.get_rule_engine()
        if engine is None:
            raise ValueError("No active configuration. Call new_config() first.")

        rule = FunctionRule.create_simple(
            rule_id=rule_id,
            name=name,
            function_name=function_name,
            parameters=parameters,
            outcome=outcome,
            description=description,
            priority=priority,
            enabled=enabled,
        )

        engine.add_rule(rule)
        self._sync_to_session()

        return rule

    def add_ai_rule(
        self,
        rule_id: str,
        name: str,
        prompt: str,
        outcome: str = "RECONSIDER",
        description: str = "",
        priority: int = 0,
        enabled: bool = True,
        model: str = "gpt-4",
        max_tokens: int = 500,
    ) -> AIGeneratedRule:
        """Add an AI-powered rule.

        Args:
            rule_id: Unique rule identifier
            name: Rule name
            prompt: Prompt for AI code generation
            outcome: Decision outcome if AI evaluation returns True
            description: Rule description
            priority: Rule priority
            enabled: Whether rule is active
            model: AI model to use
            max_tokens: Maximum tokens for response

        Returns:
            Created AIGeneratedRule
        """
        engine = self.get_rule_engine()
        if engine is None:
            raise ValueError("No active configuration. Call new_config() first.")

        rule = AIGeneratedRule.create_simple(
            rule_id=rule_id,
            name=name,
            prompt=prompt,
            outcome=outcome,
            description=description,
            priority=priority,
            enabled=enabled,
            model=model,
        )

        engine.add_rule(rule)
        self._sync_to_session()

        return rule

    def add_connection(
        self,
        from_rule_id: str,
        to_rule_id: str,
        condition: str = "any",
        priority: int = 0,
    ) -> RuleConnection:
        """Add a connection between rules.

        Args:
            from_rule_id: Source rule ID (or "START" for entry rules)
            to_rule_id: Target rule ID
            condition: Connection condition ("match", "no_match", "any")
            priority: Connection priority

        Returns:
            Created RuleConnection
        """
        engine = self.get_rule_engine()
        if engine is None:
            raise ValueError("No active configuration. Call new_config() first.")

        conn_id = f"conn_{uuid.uuid4().hex[:8]}"
        connection = RuleConnection(
            id=conn_id,
            from_rule_id=from_rule_id,
            to_rule_id=to_rule_id,
            condition=condition,
            priority=priority,
        )

        engine.add_connection(connection)
        self._sync_to_session()

        return connection

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if rule was removed
        """
        engine = self.get_rule_engine()
        if engine is None:
            return False

        result = engine.remove_rule(rule_id)
        if result:
            self._sync_to_session()
        return result

    def update_rule_enabled(self, rule_id: str, enabled: bool) -> bool:
        """Enable or disable a rule.

        Args:
            rule_id: Rule ID to update
            enabled: New enabled state

        Returns:
            True if rule was updated
        """
        engine = self.get_rule_engine()
        if engine is None:
            return False

        for rule in engine.rules:
            if rule.rule_id == rule_id:
                rule.enabled = enabled
                self._sync_to_session()
                return True

        return False

    def _sync_to_session(self) -> None:
        """Sync current state to session state."""
        if self._active_config:
            self._active_config.metadata.updated_at = datetime.now().isoformat()

            # Sync rule engine state to config
            if self._rule_engine:
                engine_dict = self._rule_engine.to_dict()
                self._active_config.rules = engine_dict.get("rules", [])
                self._active_config.connections = engine_dict.get("connections", [])

            self._session_state["rule_config"] = self._active_config.to_dict()

        if self._rule_engine:
            self._session_state["rule_engine"] = self._rule_engine.to_dict()

        self._session_state["config_dirty"] = True

        if self.auto_backup:
            self._create_backup()

    def save_config(self, filename: Optional[str] = None) -> str:
        """Save configuration to file.

        Args:
            filename: Filename (without extension). Uses config name if not provided.

        Returns:
            Path to saved file
        """
        config = self.get_active_config()
        if config is None:
            raise ValueError("No active configuration to save.")

        if filename is None:
            filename = self._sanitize_filename(config.metadata.name)

        filepath = self.config_dir / f"{filename}{self.CONFIG_EXTENSION}"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

        self._session_state["config_dirty"] = False
        logger.info(f"Configuration saved to {filepath}")

        return str(filepath)

    def load_config(self, filepath: str) -> RuleConfiguration:
        """Load configuration from file.

        Args:
            filepath: Path to configuration file

        Returns:
            Loaded RuleConfiguration
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = RuleConfiguration.from_dict(data)
        self._active_config = config

        # Recreate rule engine from config
        engine_data = {
            "rules": config.rules,
            "connections": config.connections,
        }
        self._rule_engine = EnhancedRuleEngine.from_dict(engine_data)

        # Update session state
        self._session_state["rule_config"] = config.to_dict()
        self._session_state["rule_engine"] = self._rule_engine.to_dict()
        self._session_state["config_dirty"] = False

        logger.info(f"Configuration loaded from {filepath}")

        return config

    def list_saved_configs(self) -> list[dict[str, Any]]:
        """List all saved configurations.

        Returns:
            List of configuration summaries
        """
        configs = []

        for filepath in self.config_dir.glob(f"*{self.CONFIG_EXTENSION}"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})
                configs.append(
                    {
                        "filepath": str(filepath),
                        "name": metadata.get("name", filepath.stem),
                        "description": metadata.get("description", ""),
                        "version": metadata.get("version", "1.0"),
                        "updated_at": metadata.get("updated_at", ""),
                        "rule_count": len(data.get("rules", [])),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read config {filepath}: {e}")

        return sorted(configs, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete_config(self, filepath: str) -> bool:
        """Delete a saved configuration.

        Args:
            filepath: Path to configuration file

        Returns:
            True if deleted successfully
        """
        try:
            Path(filepath).unlink()
            logger.info(f"Configuration deleted: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete config: {e}")
            return False

    def export_config(self, filepath: str) -> str:
        """Export configuration to a specific path.

        Args:
            filepath: Full path for export

        Returns:
            Path to exported file
        """
        config = self.get_active_config()
        if config is None:
            raise ValueError("No active configuration to export.")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Configuration exported to {filepath}")
        return filepath

    def import_config(self, filepath: str) -> RuleConfiguration:
        """Import configuration from external file.

        Args:
            filepath: Path to configuration file

        Returns:
            Imported RuleConfiguration
        """
        return self.load_config(filepath)

    def _create_backup(self) -> str:
        """Create a backup of the current configuration.

        Returns:
            Path to backup file
        """
        config = self.get_active_config()
        if config is None:
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}{self.CONFIG_EXTENSION}"
        filepath = self.backup_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

        self._session_state["last_backup"] = str(filepath)

        # Clean old backups (keep last 10)
        self._cleanup_backups(keep=10)

        return str(filepath)

    def _get_latest_backup(self) -> Optional[str]:
        """Get path to the most recent backup.

        Returns:
            Path to latest backup or None
        """
        backups = list(self.backup_dir.glob(f"backup_*{self.CONFIG_EXTENSION}"))
        if not backups:
            return None

        return str(sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)[0])

    def _cleanup_backups(self, keep: int = 10) -> None:
        """Remove old backups, keeping the most recent ones.

        Args:
            keep: Number of backups to keep
        """
        backups = list(self.backup_dir.glob(f"backup_*{self.CONFIG_EXTENSION}"))
        backups_sorted = sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)

        for backup in backups_sorted[keep:]:
            try:
                backup.unlink()
                logger.debug(f"Removed old backup: {backup}")
            except Exception as e:
                logger.warning(f"Failed to remove backup {backup}: {e}")

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename.

        Args:
            name: Original name

        Returns:
            Sanitized filename
        """
        # Replace spaces and special characters
        sanitized = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return sanitized.lower()

    def get_rule_summary(self) -> dict[str, Any]:
        """Get summary of current rule configuration.

        Returns:
            Dictionary with rule statistics
        """
        engine = self.get_rule_engine()
        config = self.get_active_config()

        if engine is None or config is None:
            return {
                "name": "No configuration",
                "total_rules": 0,
                "condition_rules": 0,
                "function_rules": 0,
                "ai_rules": 0,
                "connections": 0,
                "enabled_rules": 0,
            }

        condition_count = sum(1 for r in engine.rules if r.rule_type == RuleType.CONDITION)
        function_count = sum(1 for r in engine.rules if r.rule_type == RuleType.FUNCTION)
        ai_count = sum(1 for r in engine.rules if r.rule_type == RuleType.AI_GENERATED)
        enabled_count = sum(1 for r in engine.rules if r.enabled)

        return {
            "name": config.metadata.name,
            "description": config.metadata.description,
            "version": config.metadata.version,
            "updated_at": config.metadata.updated_at,
            "total_rules": len(engine.rules),
            "condition_rules": condition_count,
            "function_rules": function_count,
            "ai_rules": ai_count,
            "connections": len(engine.connections),
            "enabled_rules": enabled_count,
        }

    def create_template(
        self,
        template_name: str,
        include_default_rules: bool = True,
    ) -> RuleConfiguration:
        """Create a configuration from a predefined template.

        Args:
            template_name: Name of template to use
            include_default_rules: Whether to include default rules

        Returns:
            New RuleConfiguration based on template
        """
        config = self.new_config(
            name=template_name,
            description=f"Configuration based on {template_name} template",
        )

        if include_default_rules:
            self._add_default_rules(template_name)

        return config

    def _add_default_rules(self, template_name: str) -> None:
        """Add default rules based on template.

        Args:
            template_name: Template name
        """
        # Basic maintenance categorization rules
        if template_name in ["basic", "standard", "maintenance"]:
            # High priority acceptance rule
            self.add_condition_rule(
                rule_id="rule_high_priority",
                name="Accept High Priority",
                column="Priority",
                operator=ConditionOperator.EQUALS,
                value="High",
                outcome="ACCEPTED",
                description="Automatically accept high priority work",
                priority=100,
            )

            # Cost threshold rule
            self.add_function_rule(
                rule_id="rule_cost_check",
                name="Cost Threshold Check",
                function_name="check_cost_threshold",
                parameters={"threshold": 10000.0, "column": "Cost Estimate"},
                outcome="RECONSIDER",
                description="Flag items exceeding cost threshold",
                priority=90,
            )

            # Connect rules
            self.add_connection("START", "rule_high_priority", "any", 0)
            self.add_connection("rule_high_priority", "rule_cost_check", "no_match", 0)

        # Equipment criticality template
        elif template_name == "equipment_criticality":
            self.add_function_rule(
                rule_id="rule_critical_equipment",
                name="Critical Equipment Check",
                function_name="check_equipment_criticality",
                parameters={
                    "equipment_column": "Asset ID",
                    "criticality_level": "CRITICAL",
                },
                outcome="ACCEPTED",
                description="Accept work for critical equipment",
                priority=100,
            )

            self.add_connection("START", "rule_critical_equipment", "any", 0)


# Streamlit integration helper
def get_streamlit_config_manager() -> RuleConfigManager:
    """Get or create a RuleConfigManager integrated with Streamlit session state.

    Returns:
        RuleConfigManager instance connected to st.session_state
    """
    try:
        import streamlit as st

        if "config_manager" not in st.session_state:
            st.session_state["config_manager"] = RuleConfigManager()
            st.session_state["config_manager"].initialize_session(st.session_state)

        return st.session_state["config_manager"]

    except ImportError:
        # Not in Streamlit environment
        logger.warning("Streamlit not available. Using standalone config manager.")
        manager = RuleConfigManager()
        manager.initialize_session()
        return manager
