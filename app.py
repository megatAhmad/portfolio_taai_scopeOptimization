"""
MWCS - Maintenance Work Categorization System

Streamlit application entry point with enhanced rule engine.
"""

import logging
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.ai_service import AIProvider, AIService
from src.export import ExportFormat, ExportManager
from src.logic_engine import LogicEngine
from src.rules import (
    DecisionOutcome,
    LogicalOperator,
    NumericOperator,
    RuleBuilder,
    RuleCondition,
    RuleGroup,
    RuleSet,
    RuleType,
    TextOperator,
    get_predefined_business_rules,
)
from src.upload import DataUploader
from src.visualise import FlowchartVisualizer

# Enhanced rule engine imports
from src.enhanced_rule_engine import (
    ConditionOperator,
    ConditionRule,
    EnhancedRuleEngine,
    FunctionRule,
    AIGeneratedRule,
    RuleConnection,
    RuleType as EnhancedRuleType,
)
from src.rule_config_manager import RuleConfigManager, get_streamlit_config_manager
from src.predefined_functions import function_registry
from src.supporting_datasets import (
    SupportingDatasetManager,
    EquipmentClassification,
    WorkTypeCategory,
    EquipmentRedundancy,
    DecisionCategory,
)
from src.ai_code_generator import AICodeGenerator, create_code_generator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="MWCS - Maintenance Work Categorization",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "uploader" not in st.session_state:
    st.session_state.uploader = DataUploader()
if "rule_builder" not in st.session_state:
    st.session_state.rule_builder = RuleBuilder()
if "logic_engine" not in st.session_state:
    st.session_state.logic_engine = LogicEngine()
if "export_manager" not in st.session_state:
    st.session_state.export_manager = ExportManager()
if "visualizer" not in st.session_state:
    st.session_state.visualizer = FlowchartVisualizer()
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "evaluation_results" not in st.session_state:
    st.session_state.evaluation_results = None
if "justification_results" not in st.session_state:
    st.session_state.justification_results = None

# Enhanced rule engine session state
if "enhanced_rule_engine" not in st.session_state:
    st.session_state.enhanced_rule_engine = EnhancedRuleEngine()
if "config_manager" not in st.session_state:
    st.session_state.config_manager = RuleConfigManager()
    st.session_state.config_manager.initialize_session(st.session_state)
if "dataset_manager" not in st.session_state:
    st.session_state.dataset_manager = SupportingDatasetManager()
if "use_enhanced_engine" not in st.session_state:
    st.session_state.use_enhanced_engine = False
if "rule_audit_log" not in st.session_state:
    st.session_state.rule_audit_log = []


def main():
    """Main application entry point."""
    st.title("Maintenance Work Categorization System")
    st.markdown("Categorize maintenance work items using AI-powered rules evaluation.")

    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        step = st.radio(
            "Select Step",
            options=[
                "1. Upload Data",
                "2. Define Rules",
                "3. Preview",
                "4. Process",
                "5. Results & Export",
            ],
            index=st.session_state.current_step - 1,
        )
        st.session_state.current_step = int(step[0])

        st.divider()
        st.header("Quick Actions")

        if st.button("Reset All", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Render the appropriate step
    if st.session_state.current_step == 1:
        render_upload_step()
    elif st.session_state.current_step == 2:
        render_rules_step()
    elif st.session_state.current_step == 3:
        render_preview_step()
    elif st.session_state.current_step == 4:
        render_processing_step()
    elif st.session_state.current_step == 5:
        render_results_step()


def render_upload_step():
    """Render the data upload step."""
    st.header("Step 1: Upload Data")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload Excel File (.xlsx)",
            type=["xlsx"],
            help="Upload your maintenance work items Excel file. The first sheet will be used as the main dataset.",
        )

        if uploaded_file is not None:
            try:
                # Load the file
                data = st.session_state.uploader.load_from_bytes(
                    uploaded_file.getvalue(), uploaded_file.name
                )

                st.success(f"Loaded: {uploaded_file.name}")

                # Show validation results
                if data.validation:
                    if data.validation.is_valid:
                        st.success("Data validation passed!")
                    else:
                        st.error("Validation errors found:")
                        for error in data.validation.errors:
                            st.error(f"- {error}")

                    if data.validation.warnings:
                        st.warning("Warnings:")
                        for warning in data.validation.warnings:
                            st.warning(f"- {warning}")

                # Show preview
                st.subheader("Data Preview (First 10 rows)")
                preview = st.session_state.uploader.get_preview(10)
                if preview is not None:
                    st.dataframe(preview, use_container_width=True)

            except Exception as e:
                st.error(f"Error loading file: {e}")
                logger.exception("Error loading file")

    with col2:
        st.subheader("Required Columns")
        st.markdown(
            """
        - Work ID
        - Description
        - Priority
        - Category
        - Estimated Hours
        - Last Service Date
        """
        )

        st.subheader("Optional Columns")
        st.markdown(
            """
        - Asset ID
        - Location
        - Cost Estimate
        - Risk Level
        - Dependencies
        """
        )

        # Show column stats if data is loaded
        if st.session_state.uploader.uploaded_data is not None:
            st.subheader("Column Statistics")
            stats = st.session_state.uploader.get_column_stats()
            if stats:
                stats_df = pd.DataFrame(
                    [
                        {"Column": col, "Type": s["dtype"], "Non-Null": s["non_null_count"]}
                        for col, s in stats.items()
                    ]
                )
                st.dataframe(stats_df, use_container_width=True, hide_index=True)

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col2:
        if st.session_state.uploader.uploaded_data is not None:
            if st.button("Next: Define Rules →", type="primary"):
                st.session_state.current_step = 2
                st.rerun()


def render_rules_step():
    """Render the rule definition step."""
    st.header("Step 2: Define Rules")

    # Toggle between standard and enhanced rule engine
    col1, col2 = st.columns([3, 1])
    with col1:
        st.session_state.use_enhanced_engine = st.toggle(
            "Use Enhanced Rule Engine (3 Rule Types)",
            value=st.session_state.use_enhanced_engine,
            help="Enable condition-based, function-based, and AI-powered rules"
        )

    if st.session_state.use_enhanced_engine:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Condition Rules",
            "Function Rules",
            "AI Rules",
            "Supporting Datasets",
            "Rule Configuration"
        ])

        with tab1:
            render_condition_rule_builder()

        with tab2:
            render_function_rule_builder()

        with tab3:
            render_ai_rule_builder()

        with tab4:
            render_supporting_datasets()

        with tab5:
            render_enhanced_rule_config()
    else:
        tab1, tab2, tab3 = st.tabs(["Rule Builder", "Load Template", "View Rules"])

        with tab1:
            render_rule_builder()

        with tab2:
            render_template_loader()

        with tab3:
            render_rules_viewer()

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back to Upload"):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        has_rules = (
            st.session_state.rule_builder.current_ruleset is not None or
            len(st.session_state.enhanced_rule_engine.rules) > 0
        )
        if has_rules:
            if st.button("Next: Preview →", type="primary"):
                st.session_state.current_step = 3
                st.rerun()


def render_rule_builder():
    """Render the rule builder interface."""
    st.subheader("Create New Ruleset")

    # Ruleset name
    ruleset_name = st.text_input(
        "Ruleset Name", value="My Maintenance Rules", key="ruleset_name"
    )

    if st.button("Create New Ruleset"):
        st.session_state.rule_builder.new_ruleset(ruleset_name)
        st.success(f"Created ruleset: {ruleset_name}")

    # If ruleset exists, show rule addition form
    if st.session_state.rule_builder.current_ruleset is not None:
        st.divider()
        st.subheader("Add New Rule")

        with st.form("add_rule_form"):
            rule_name = st.text_input("Rule Name")
            rule_priority = st.slider("Priority", 0, 100, 50)

            st.markdown("**Condition**")
            col1, col2, col3 = st.columns(3)

            with col1:
                # Get available columns from uploaded data
                columns = ["Priority", "Category", "Estimated Hours", "Cost Estimate", "Risk Level"]
                if st.session_state.uploader.uploaded_data is not None:
                    columns = list(st.session_state.uploader.uploaded_data.main_df.columns)

                field = st.selectbox("Field", columns)

            with col2:
                rule_type = st.selectbox(
                    "Type",
                    options=["numeric", "text", "date"],
                    format_func=lambda x: x.title(),
                )

            with col3:
                if rule_type == "numeric":
                    operators = [">", "<", "=", ">=", "<=", "between"]
                elif rule_type == "text":
                    operators = ["contains", "exact_match", "starts_with", "ends_with"]
                else:
                    operators = ["before", "after", "within_days"]

                operator = st.selectbox("Operator", operators)

            value = st.text_input("Value")

            outcome = st.selectbox(
                "Outcome",
                options=["ACCEPTED", "REJECTED", "RECONSIDER"],
            )

            submitted = st.form_submit_button("Add Rule")

            if submitted and rule_name and value:
                try:
                    condition = RuleCondition(
                        field=field,
                        rule_type=RuleType(rule_type),
                        operator=operator,
                        value=value if rule_type == "text" else float(value),
                    )

                    st.session_state.rule_builder.add_rule(
                        name=rule_name,
                        conditions=[condition],
                        outcome=DecisionOutcome(outcome),
                        priority=rule_priority,
                    )
                    st.success(f"Added rule: {rule_name}")
                except Exception as e:
                    st.error(f"Error adding rule: {e}")


def render_template_loader():
    """Render the template loader interface."""
    st.subheader("Load from Template")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Predefined Templates**")
        predefined = get_predefined_business_rules()

        template_choice = st.selectbox(
            "Select Template",
            options=list(predefined.keys()),
            format_func=lambda x: predefined[x].name,
        )

        if st.button("Load Predefined Template"):
            st.session_state.rule_builder._current_ruleset = predefined[template_choice]
            st.success(f"Loaded template: {predefined[template_choice].name}")
            st.rerun()

    with col2:
        st.markdown("**Saved Templates**")
        saved_templates = st.session_state.rule_builder.list_templates()

        if saved_templates:
            selected_template = st.selectbox("Select Saved Template", saved_templates)
            if st.button("Load Saved Template"):
                st.session_state.rule_builder.load_template(selected_template)
                st.success(f"Loaded template: {selected_template}")
                st.rerun()
        else:
            st.info("No saved templates found.")

    # Save current ruleset
    st.divider()
    st.subheader("Save Current Ruleset")

    if st.session_state.rule_builder.current_ruleset is not None:
        save_name = st.text_input(
            "Template Name",
            value=st.session_state.rule_builder.current_ruleset.name.lower().replace(" ", "_"),
        )
        if st.button("Save as Template"):
            filepath = st.session_state.rule_builder.save_template(save_name)
            st.success(f"Saved to: {filepath}")


def render_rules_viewer():
    """Render the rules viewer interface."""
    st.subheader("Current Rules")

    ruleset = st.session_state.rule_builder.current_ruleset

    if ruleset is None:
        st.info("No ruleset defined. Create one in the Rule Builder tab or load a template.")
        return

    st.markdown(f"**Ruleset:** {ruleset.name}")
    st.markdown(f"**Version:** {ruleset.version}")
    st.markdown(f"**Default Outcome:** {ruleset.default_outcome.value}")
    st.markdown(f"**Total Rules:** {len(ruleset.rules)}")

    st.divider()

    for i, rule in enumerate(ruleset.rules):
        with st.expander(f"Rule {i+1}: {rule.name} (Priority: {rule.priority})"):
            st.markdown(f"**Outcome:** {rule.outcome.value if hasattr(rule, 'outcome') else rule.then_outcome.value}")
            st.markdown(f"**Enabled:** {rule.enabled}")

            if rule.description:
                st.markdown(f"**Description:** {rule.description}")

            st.markdown("**Conditions:**")
            for condition in rule.conditions:
                if hasattr(condition, "field"):
                    st.code(
                        f"{condition.field} {condition.operator} {condition.value}"
                    )

            if st.button(f"Delete Rule", key=f"delete_rule_{i}"):
                st.session_state.rule_builder.remove_rule(rule.name)
                st.rerun()


# Enhanced Rule Engine UI Functions

def render_condition_rule_builder():
    """Render the condition-based rule builder interface."""
    st.subheader("Condition-Based Rules")
    st.markdown("Create rules based on column values with comparison operators.")

    with st.form("add_condition_rule_form"):
        col1, col2 = st.columns(2)

        with col1:
            rule_id = st.text_input("Rule ID", value=f"cond_rule_{len(st.session_state.enhanced_rule_engine.rules) + 1}")
            rule_name = st.text_input("Rule Name")
            rule_priority = st.slider("Priority", 0, 100, 50)

        with col2:
            # Get available columns from uploaded data
            columns = ["Priority", "Category", "Estimated Hours", "Cost Estimate", "Risk Level"]
            if st.session_state.uploader.uploaded_data is not None:
                columns = list(st.session_state.uploader.uploaded_data.main_df.columns)

            column = st.selectbox("Column", columns)
            operator = st.selectbox(
                "Operator",
                options=[op.value for op in ConditionOperator],
                format_func=lambda x: x.replace("_", " ").title()
            )
            value = st.text_input("Value")

        outcome = st.selectbox(
            "Outcome",
            options=["ACCEPTED", "REJECTED", "RECONSIDER"],
        )
        description = st.text_area("Description (optional)")

        submitted = st.form_submit_button("Add Condition Rule")

        if submitted and rule_name and value:
            try:
                # Convert value to appropriate type
                try:
                    parsed_value = float(value)
                except ValueError:
                    parsed_value = value

                rule = ConditionRule(
                    rule_id=rule_id,
                    name=rule_name,
                    column=column,
                    operator=ConditionOperator(operator),
                    value=parsed_value,
                    outcome=outcome,
                    description=description,
                    priority=rule_priority,
                )
                st.session_state.enhanced_rule_engine.add_rule(rule)
                st.success(f"Added condition rule: {rule_name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding rule: {e}")

    # Display existing condition rules
    st.divider()
    st.subheader("Existing Condition Rules")
    condition_rules = [r for r in st.session_state.enhanced_rule_engine.rules
                       if r.rule_type == EnhancedRuleType.CONDITION]

    if not condition_rules:
        st.info("No condition rules defined yet.")
    else:
        for rule in condition_rules:
            with st.expander(f"{rule.name} (Priority: {rule.priority})"):
                st.markdown(f"**ID:** {rule.rule_id}")
                st.markdown(f"**Condition:** `{rule.column} {rule.operator.value} {rule.value}`")
                st.markdown(f"**Outcome:** {rule.outcome}")
                st.markdown(f"**Enabled:** {rule.enabled}")
                if rule.description:
                    st.markdown(f"**Description:** {rule.description}")

                if st.button("Delete", key=f"del_cond_{rule.rule_id}"):
                    st.session_state.enhanced_rule_engine.remove_rule(rule.rule_id)
                    st.rerun()


def render_function_rule_builder():
    """Render the function-based rule builder interface."""
    st.subheader("Function-Based Rules")
    st.markdown("Create rules using predefined Python functions with custom parameters.")

    # Show available functions
    with st.expander("Available Functions"):
        functions = function_registry.list_functions()
        for func_name, func_info in functions.items():
            st.markdown(f"**{func_name}**")
            st.markdown(f"  - Category: {func_info['category']}")
            st.markdown(f"  - Description: {func_info['description']}")
            if func_info['parameters']:
                st.markdown(f"  - Parameters: {', '.join(func_info['parameters'].keys())}")

    with st.form("add_function_rule_form"):
        col1, col2 = st.columns(2)

        with col1:
            rule_id = st.text_input("Rule ID", value=f"func_rule_{len(st.session_state.enhanced_rule_engine.rules) + 1}")
            rule_name = st.text_input("Rule Name")
            rule_priority = st.slider("Priority", 0, 100, 50)

        with col2:
            function_names = list(function_registry.list_functions().keys())
            function_name = st.selectbox("Function", function_names)

            # Get function parameters
            func_info = function_registry.get_function_info(function_name)
            params = {}
            if func_info and func_info.get("parameters"):
                st.markdown("**Function Parameters:**")
                for param_name, param_info in func_info["parameters"].items():
                    default = param_info.get("default", "")
                    param_type = param_info.get("type", "str")
                    param_value = st.text_input(
                        f"{param_name} ({param_type})",
                        value=str(default) if default else "",
                        key=f"param_{function_name}_{param_name}"
                    )
                    if param_value:
                        try:
                            if param_type == "float":
                                params[param_name] = float(param_value)
                            elif param_type == "int":
                                params[param_name] = int(param_value)
                            elif param_type == "bool":
                                params[param_name] = param_value.lower() in ("true", "1", "yes")
                            else:
                                params[param_name] = param_value
                        except ValueError:
                            params[param_name] = param_value

        outcome = st.selectbox(
            "Outcome if True",
            options=["ACCEPTED", "REJECTED", "RECONSIDER"],
        )
        description = st.text_area("Description (optional)")

        submitted = st.form_submit_button("Add Function Rule")

        if submitted and rule_name and function_name:
            try:
                rule = FunctionRule(
                    rule_id=rule_id,
                    name=rule_name,
                    function_name=function_name,
                    parameters=params,
                    outcome=outcome,
                    description=description,
                    priority=rule_priority,
                )
                st.session_state.enhanced_rule_engine.add_rule(rule)
                st.success(f"Added function rule: {rule_name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding rule: {e}")

    # Display existing function rules
    st.divider()
    st.subheader("Existing Function Rules")
    function_rules = [r for r in st.session_state.enhanced_rule_engine.rules
                      if r.rule_type == EnhancedRuleType.FUNCTION]

    if not function_rules:
        st.info("No function rules defined yet.")
    else:
        for rule in function_rules:
            with st.expander(f"{rule.name} (Priority: {rule.priority})"):
                st.markdown(f"**ID:** {rule.rule_id}")
                st.markdown(f"**Function:** `{rule.function_name}`")
                st.markdown(f"**Parameters:** {rule.parameters}")
                st.markdown(f"**Outcome:** {rule.outcome}")
                st.markdown(f"**Enabled:** {rule.enabled}")

                if st.button("Delete", key=f"del_func_{rule.rule_id}"):
                    st.session_state.enhanced_rule_engine.remove_rule(rule.rule_id)
                    st.rerun()


def render_ai_rule_builder():
    """Render the AI-powered rule builder interface."""
    st.subheader("AI-Powered Rules")
    st.markdown("Create rules using natural language that AI converts to executable code.")

    # Check AI configuration
    has_azure = os.environ.get("AZURE_OPENAI_API_KEY") and os.environ.get("AZURE_OPENAI_ENDPOINT")
    has_openrouter = os.environ.get("OPENROUTER_API_KEY")

    if not has_azure and not has_openrouter:
        st.warning("AI service not configured. Please set AZURE_OPENAI_API_KEY/ENDPOINT or OPENROUTER_API_KEY.")

    with st.form("add_ai_rule_form"):
        col1, col2 = st.columns(2)

        with col1:
            rule_id = st.text_input("Rule ID", value=f"ai_rule_{len(st.session_state.enhanced_rule_engine.rules) + 1}")
            rule_name = st.text_input("Rule Name")
            rule_priority = st.slider("Priority", 0, 100, 50)

        with col2:
            ai_provider = st.selectbox(
                "AI Provider",
                options=["azure_openai", "openrouter"],
                format_func=lambda x: "Azure OpenAI" if x == "azure_openai" else "OpenRouter"
            )

        prompt = st.text_area(
            "Natural Language Rule Description",
            placeholder="E.g., Accept the work order if priority is High and cost is under $5000",
            height=100
        )

        outcome = st.selectbox(
            "Outcome if True",
            options=["ACCEPTED", "REJECTED", "RECONSIDER"],
        )
        description = st.text_area("Description (optional)")

        submitted = st.form_submit_button("Add AI Rule")

        if submitted and rule_name and prompt:
            try:
                rule = AIGeneratedRule(
                    rule_id=rule_id,
                    name=rule_name,
                    prompt=prompt,
                    outcome=outcome,
                    description=description,
                    priority=rule_priority,
                    model="gpt-4" if ai_provider == "azure_openai" else "openai/gpt-4-turbo",
                )
                st.session_state.enhanced_rule_engine.add_rule(rule)
                st.success(f"Added AI rule: {rule_name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding rule: {e}")

    # Display existing AI rules
    st.divider()
    st.subheader("Existing AI Rules")
    ai_rules = [r for r in st.session_state.enhanced_rule_engine.rules
                if r.rule_type == EnhancedRuleType.AI_GENERATED]

    if not ai_rules:
        st.info("No AI rules defined yet.")
    else:
        for rule in ai_rules:
            with st.expander(f"{rule.name} (Priority: {rule.priority})"):
                st.markdown(f"**ID:** {rule.rule_id}")
                st.markdown(f"**Prompt:** {rule.prompt}")
                st.markdown(f"**Model:** {rule.model}")
                st.markdown(f"**Outcome:** {rule.outcome}")
                st.markdown(f"**Enabled:** {rule.enabled}")
                if rule.generated_code:
                    st.markdown("**Generated Code:**")
                    st.code(rule.generated_code, language="python")

                if st.button("Delete", key=f"del_ai_{rule.rule_id}"):
                    st.session_state.enhanced_rule_engine.remove_rule(rule.rule_id)
                    st.rerun()


def render_supporting_datasets():
    """Render the supporting datasets configuration interface."""
    st.subheader("Supporting Datasets")
    st.markdown("Configure classification datasets that drive accept/reconsider/reject decisions.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Equipment Classification",
        "Work Type Categorization",
        "Equipment Redundancy",
        "Decision Matrix"
    ])

    dm = st.session_state.dataset_manager

    with tab1:
        st.markdown("**Equipment Classification Master**")
        st.markdown("Maps equipment types to criticality levels: Critical, Standard, Low Priority")

        # Show current classifications
        equip_data = dm.generate_equipment_classification_sample()
        st.dataframe(equip_data, use_container_width=True, hide_index=True)

        # Add custom classification
        with st.expander("Add Custom Equipment Classification"):
            with st.form("add_equipment_class"):
                eq_id = st.text_input("Equipment ID")
                eq_name = st.text_input("Equipment Name")
                classification = st.selectbox(
                    "Classification",
                    options=[e.value for e in EquipmentClassification]
                )
                if st.form_submit_button("Add"):
                    # Would add to dataset manager in real implementation
                    st.success(f"Added {eq_name} as {classification}")

    with tab2:
        st.markdown("**Work Type Categorization Reference**")
        st.markdown("Maps work categories to urgency levels: Emergency, Planned, Deferred")

        work_type_data = dm.generate_work_type_sample()
        st.dataframe(work_type_data, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("**Equipment Redundancy Master**")
        st.markdown("Defines backup availability: No Dependency, Single, Dual, Uncertain")

        redundancy_data = dm.generate_redundancy_sample()
        st.dataframe(redundancy_data, use_container_width=True, hide_index=True)

    with tab4:
        st.markdown("**Decision Matrix**")
        st.markdown("How classifications map to final decisions:")

        matrix_data = []
        for eq_class in EquipmentClassification:
            for work_type in WorkTypeCategory:
                decision = dm.get_decision_from_matrix(eq_class, work_type)
                matrix_data.append({
                    "Equipment Class": eq_class.value,
                    "Work Type": work_type.value,
                    "Decision": decision.value
                })

        matrix_df = pd.DataFrame(matrix_data)
        st.dataframe(matrix_df, use_container_width=True, hide_index=True)


def render_enhanced_rule_config():
    """Render the enhanced rule configuration interface."""
    st.subheader("Rule Configuration Management")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Current Configuration**")
        summary = {
            "Total Rules": len(st.session_state.enhanced_rule_engine.rules),
            "Condition Rules": len([r for r in st.session_state.enhanced_rule_engine.rules
                                   if r.rule_type == EnhancedRuleType.CONDITION]),
            "Function Rules": len([r for r in st.session_state.enhanced_rule_engine.rules
                                  if r.rule_type == EnhancedRuleType.FUNCTION]),
            "AI Rules": len([r for r in st.session_state.enhanced_rule_engine.rules
                            if r.rule_type == EnhancedRuleType.AI_GENERATED]),
            "Connections": len(st.session_state.enhanced_rule_engine.connections),
        }

        for key, value in summary.items():
            st.metric(key, value)

    with col2:
        st.markdown("**Save/Load Configuration**")

        # Save configuration
        config_name = st.text_input("Configuration Name", value="my_rules")
        if st.button("Save Configuration"):
            try:
                cm = st.session_state.config_manager
                cm.new_config(config_name)

                # Sync rules to config manager
                for rule in st.session_state.enhanced_rule_engine.rules:
                    if rule.rule_type == EnhancedRuleType.CONDITION:
                        cm.add_condition_rule(
                            rule.rule_id, rule.name, rule.column,
                            rule.operator, rule.value, rule.outcome,
                            rule.description, rule.priority, rule.enabled
                        )
                    elif rule.rule_type == EnhancedRuleType.FUNCTION:
                        cm.add_function_rule(
                            rule.rule_id, rule.name, rule.function_name,
                            rule.parameters, rule.outcome,
                            rule.description, rule.priority, rule.enabled
                        )

                filepath = cm.save_config(config_name)
                st.success(f"Saved to {filepath}")
            except Exception as e:
                st.error(f"Error saving: {e}")

        # Load configuration
        st.divider()
        saved_configs = st.session_state.config_manager.list_saved_configs()
        if saved_configs:
            config_options = {c["name"]: c["filepath"] for c in saved_configs}
            selected_config = st.selectbox("Load Configuration", options=list(config_options.keys()))
            if st.button("Load"):
                try:
                    cm = st.session_state.config_manager
                    cm.load_config(config_options[selected_config])
                    engine = cm.get_rule_engine()
                    if engine:
                        st.session_state.enhanced_rule_engine = engine
                    st.success(f"Loaded {selected_config}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading: {e}")

    # Rule connections
    st.divider()
    st.subheader("Rule Connections")
    st.markdown("Define execution order by connecting rules.")

    with st.form("add_connection_form"):
        col1, col2, col3 = st.columns(3)

        rule_ids = ["START"] + [r.rule_id for r in st.session_state.enhanced_rule_engine.rules]

        with col1:
            from_rule = st.selectbox("From Rule", options=rule_ids)
        with col2:
            to_rule = st.selectbox("To Rule", options=rule_ids[1:])  # Exclude START as target
        with col3:
            condition = st.selectbox("Condition", options=["any", "match", "no_match"])

        if st.form_submit_button("Add Connection"):
            try:
                connection = RuleConnection(
                    from_rule_id=from_rule,
                    to_rule_id=to_rule,
                    condition=condition
                )
                st.session_state.enhanced_rule_engine.add_connection(connection)
                st.success(f"Added connection: {from_rule} -> {to_rule}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # Show existing connections
    if st.session_state.enhanced_rule_engine.connections:
        st.markdown("**Existing Connections:**")
        for conn in st.session_state.enhanced_rule_engine.connections:
            st.markdown(f"- {conn.from_rule_id} → {conn.to_rule_id} (on {conn.condition})")


def render_preview_step():
    """Render the preview step."""
    st.header("Step 3: Preview")

    # Check for rules (either standard or enhanced)
    has_standard_rules = st.session_state.rule_builder.current_ruleset is not None
    has_enhanced_rules = len(st.session_state.enhanced_rule_engine.rules) > 0

    if not has_standard_rules and not has_enhanced_rules:
        st.warning("Please define rules first.")
        return

    if st.session_state.uploader.uploaded_data is None:
        st.warning("Please upload data first.")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Rule Flowchart")
        fig = st.session_state.visualizer.create_ruleset_flowchart(
            st.session_state.rule_builder.current_ruleset
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Sample Evaluation Preview")

        # Set up logic engine
        st.session_state.logic_engine.ruleset = st.session_state.rule_builder.current_ruleset
        st.session_state.logic_engine.set_supporting_data(
            st.session_state.uploader.get_supporting_datasets()
        )

        preview_df = st.session_state.visualizer.create_rule_preview_table(
            st.session_state.rule_builder.current_ruleset,
            st.session_state.uploader.uploaded_data.main_df,
            num_samples=5,
        )
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back to Rules"):
            st.session_state.current_step = 2
            st.rerun()
    with col2:
        if st.button("Next: Process →", type="primary"):
            st.session_state.current_step = 4
            st.rerun()


def render_processing_step():
    """Render the processing step."""
    st.header("Step 4: Process Data")

    if st.session_state.rule_builder.current_ruleset is None:
        st.warning("Please define rules first.")
        return

    if st.session_state.uploader.uploaded_data is None:
        st.warning("Please upload data first.")
        return

    # AI Configuration
    st.subheader("AI Justification Settings")

    col1, col2 = st.columns(2)

    with col1:
        use_ai = st.checkbox("Enable AI Justifications", value=True)

        if use_ai:
            ai_provider = st.selectbox(
                "AI Provider",
                options=["azure_openai", "openrouter"],
                format_func=lambda x: "Azure OpenAI" if x == "azure_openai" else "OpenRouter",
            )

    with col2:
        if use_ai:
            if ai_provider == "azure_openai":
                api_key_env = "AZURE_OPENAI_API_KEY"
                endpoint_env = "AZURE_OPENAI_ENDPOINT"
                has_key = os.environ.get(api_key_env) is not None
                has_endpoint = os.environ.get(endpoint_env) is not None

                if has_key and has_endpoint:
                    st.success("Azure OpenAI is configured")
                else:
                    if not has_key:
                        st.warning(f"{api_key_env} not found in environment")
                    if not has_endpoint:
                        st.warning(f"{endpoint_env} not found in environment")
                    manual_key = st.text_input("Enter Azure API Key", type="password")
                    manual_endpoint = st.text_input("Enter Azure Endpoint")
                    if manual_key:
                        os.environ[api_key_env] = manual_key
                    if manual_endpoint:
                        os.environ[endpoint_env] = manual_endpoint
            else:
                api_key_env = "OPENROUTER_API_KEY"
                has_key = os.environ.get(api_key_env) is not None

                if has_key:
                    st.success("OpenRouter is configured")
                else:
                    st.warning(f"{api_key_env} not found in environment")
                    manual_key = st.text_input("Enter OpenRouter API Key", type="password")
                    if manual_key:
                        os.environ[api_key_env] = manual_key

    st.divider()

    # Processing
    df = st.session_state.uploader.uploaded_data.main_df
    total_rows = len(df)

    st.markdown(f"**Total rows to process:** {total_rows}")

    if st.button("Start Processing", type="primary"):
        # Set up engine
        st.session_state.logic_engine.ruleset = st.session_state.rule_builder.current_ruleset
        st.session_state.logic_engine.set_supporting_data(
            st.session_state.uploader.get_supporting_datasets()
        )

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total):
            progress_bar.progress(current / total)
            status_text.text(f"Processing row {current} of {total}...")

        # Rule evaluation
        status_text.text("Evaluating rules...")
        batch_result = st.session_state.logic_engine.evaluate_batch(
            df, progress_callback=update_progress
        )
        st.session_state.evaluation_results = batch_result

        # AI justifications
        if use_ai:
            status_text.text("Generating AI justifications...")
            try:
                ai_service = AIService(provider=AIProvider(ai_provider))
                justifications = ai_service.generate_batch_justifications(
                    df, batch_result.results, progress_callback=update_progress
                )
                st.session_state.justification_results = justifications
            except Exception as e:
                st.warning(f"AI justification failed: {e}. Using fallback justifications.")
                # Generate fallback justifications
                from src.ai_service import JustificationResult

                justifications = []
                for idx, (row_idx, row) in enumerate(df.iterrows()):
                    eval_result = batch_result.results[idx]
                    fallback_text = AIService.get_fallback_justification(
                        eval_result.outcome.value,
                        eval_result.matched_rules,
                        row,
                    )
                    justifications.append(
                        JustificationResult(
                            justification=fallback_text,
                            confidence_score=eval_result.score,
                            provider=AIProvider.AZURE_OPENAI,
                            model="fallback",
                        )
                    )
                st.session_state.justification_results = justifications
        else:
            # Generate fallback justifications
            from src.ai_service import JustificationResult

            justifications = []
            for idx, (row_idx, row) in enumerate(df.iterrows()):
                eval_result = batch_result.results[idx]
                fallback_text = AIService.get_fallback_justification(
                    eval_result.outcome.value,
                    eval_result.matched_rules,
                    row,
                )
                justifications.append(
                    JustificationResult(
                        justification=fallback_text,
                        confidence_score=eval_result.score,
                        provider=AIProvider.AZURE_OPENAI,
                        model="fallback",
                    )
                )
            st.session_state.justification_results = justifications

        # Prepare export
        st.session_state.export_manager.prepare_export(
            df,
            batch_result.results,
            st.session_state.justification_results,
            batch_result.processing_time_ms,
        )

        progress_bar.progress(100)
        status_text.text("Processing complete!")

        st.success("Processing complete! View results in the next step.")

        # Show summary
        summary = st.session_state.logic_engine.get_evaluation_summary(batch_result)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Accepted", summary["accepted"]["count"])
        with col2:
            st.metric("Rejected", summary["rejected"]["count"])
        with col3:
            st.metric("Reconsider", summary["reconsider"]["count"])
        with col4:
            st.metric("Processing Time", f"{summary['processing_time_ms']:.0f}ms")

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back to Preview"):
            st.session_state.current_step = 3
            st.rerun()
    with col2:
        if st.session_state.evaluation_results is not None:
            if st.button("Next: Results →", type="primary"):
                st.session_state.current_step = 5
                st.rerun()


def render_results_step():
    """Render the results and export step."""
    st.header("Step 5: Results & Export")

    if st.session_state.export_manager.results_df is None:
        st.warning("Please process data first.")
        return

    results_df = st.session_state.export_manager.results_df

    # Summary metrics
    st.subheader("Summary")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        accepted = (results_df["Status"] == "ACCEPTED").sum()
        st.metric("Accepted", accepted, f"{accepted/len(results_df)*100:.1f}%")

    with col2:
        rejected = (results_df["Status"] == "REJECTED").sum()
        st.metric("Rejected", rejected, f"{rejected/len(results_df)*100:.1f}%")

    with col3:
        reconsider = (results_df["Status"] == "RECONSIDER").sum()
        st.metric("Reconsider", reconsider, f"{reconsider/len(results_df)*100:.1f}%")

    with col4:
        avg_conf = results_df["ConfidenceScore"].mean()
        st.metric("Avg Confidence", f"{avg_conf:.1f}%")

    # Visualizations
    st.subheader("Visualizations")

    tab1, tab2, tab3 = st.tabs(["Dashboard", "Detailed Charts", "Data Table"])

    with tab1:
        fig = st.session_state.visualizer.create_dashboard(results_df)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            fig = st.session_state.visualizer.create_results_summary_chart(results_df)
            st.plotly_chart(fig, use_container_width=True)

            fig = st.session_state.visualizer.create_confidence_distribution_chart(results_df)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = st.session_state.visualizer.create_confidence_by_status_chart(results_df)
            st.plotly_chart(fig, use_container_width=True)

            if "Category" in results_df.columns:
                fig = st.session_state.visualizer.create_category_breakdown_chart(results_df)
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=["ACCEPTED", "REJECTED", "RECONSIDER"],
                default=["ACCEPTED", "REJECTED", "RECONSIDER"],
            )

        with col2:
            conf_min = st.slider("Min Confidence", 0, 100, 0)

        with col3:
            conf_max = st.slider("Max Confidence", 0, 100, 100)

        # Filter data
        filtered_df = st.session_state.export_manager.get_filtered_export(
            status_filter=status_filter,
            confidence_min=conf_min,
            confidence_max=conf_max,
        )

        st.markdown(f"Showing {len(filtered_df)} of {len(results_df)} rows")
        st.dataframe(filtered_df, use_container_width=True)

    # Export section
    st.divider()
    st.subheader("Export Results")

    col1, col2, col3 = st.columns(3)

    with col1:
        xlsx_buffer = st.session_state.export_manager.export_xlsx()
        st.download_button(
            label="Download Excel (.xlsx)",
            data=xlsx_buffer,
            file_name=st.session_state.export_manager.get_download_filename(ExportFormat.XLSX),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col2:
        csv_buffer = st.session_state.export_manager.export_csv()
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name=st.session_state.export_manager.get_download_filename(ExportFormat.CSV),
            mime="text/csv",
        )

    with col3:
        json_str = st.session_state.export_manager.export_json()
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=st.session_state.export_manager.get_download_filename(ExportFormat.JSON),
            mime="application/json",
        )

    # Audit metadata
    st.divider()
    st.subheader("Audit Metadata")

    if st.session_state.export_manager.metadata:
        meta = st.session_state.export_manager.metadata
        st.json(meta.to_dict())

    # Navigation
    if st.button("← Start Over"):
        st.session_state.current_step = 1
        st.rerun()


if __name__ == "__main__":
    main()
