"""
Visualisation module for MWCS - renders flowcharts and preview charts.
"""

import logging
from typing import Any, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .rules import (
    ConditionalRule,
    DecisionOutcome,
    Rule,
    RuleCondition,
    RuleGroup,
    RuleSet,
)

logger = logging.getLogger(__name__)

# Color schemes
OUTCOME_COLORS = {
    "ACCEPTED": "#28a745",  # Green
    "REJECTED": "#dc3545",  # Red
    "RECONSIDER": "#ffc107",  # Yellow/Orange
}

CONFIDENCE_COLORS = {
    "high": "#28a745",
    "medium": "#17a2b8",
    "low": "#ffc107",
    "very_low": "#dc3545",
}


class FlowchartVisualizer:
    """Visualizes rule flowcharts and evaluation results."""

    def __init__(self):
        """Initialize the visualizer."""
        pass

    def create_ruleset_flowchart(self, ruleset: RuleSet) -> go.Figure:
        """Create a flowchart visualization of the ruleset."""
        if not ruleset.rules:
            return self._create_empty_figure("No rules defined")

        # Build node and edge data
        nodes = []
        edges = []

        # Start node
        nodes.append(
            {
                "id": "start",
                "label": "Start",
                "x": 0,
                "y": 0,
                "color": "#6c757d",
            }
        )

        y_offset = 1
        for i, rule in enumerate(ruleset.rules):
            rule_id = f"rule_{i}"
            outcome_id = f"outcome_{i}"

            # Rule node
            if isinstance(rule, ConditionalRule):
                label = f"{rule.name}\n(IF-THEN-ELSE)"
            else:
                label = f"{rule.name}\nPriority: {rule.priority}"

            nodes.append(
                {
                    "id": rule_id,
                    "label": label,
                    "x": 0,
                    "y": y_offset,
                    "color": "#007bff",
                }
            )

            # Edge from previous
            if i == 0:
                edges.append({"from": "start", "to": rule_id})
            else:
                edges.append({"from": f"rule_{i-1}", "to": rule_id})

            # Outcome node
            outcome = rule.outcome if isinstance(rule, Rule) else rule.then_outcome
            nodes.append(
                {
                    "id": outcome_id,
                    "label": outcome.value,
                    "x": 1,
                    "y": y_offset,
                    "color": OUTCOME_COLORS.get(outcome.value, "#6c757d"),
                }
            )
            edges.append({"from": rule_id, "to": outcome_id, "label": "Match"})

            y_offset += 1

        # Default outcome node
        nodes.append(
            {
                "id": "default",
                "label": f"Default:\n{ruleset.default_outcome.value}",
                "x": 0,
                "y": y_offset,
                "color": OUTCOME_COLORS.get(ruleset.default_outcome.value, "#6c757d"),
            }
        )
        if ruleset.rules:
            edges.append({"from": f"rule_{len(ruleset.rules)-1}", "to": "default", "label": "No Match"})

        return self._create_flowchart_figure(nodes, edges, ruleset.name)

    def _create_flowchart_figure(
        self, nodes: list[dict], edges: list[dict], title: str
    ) -> go.Figure:
        """Create a Plotly figure from nodes and edges."""
        fig = go.Figure()

        # Add edges
        for edge in edges:
            from_node = next((n for n in nodes if n["id"] == edge["from"]), None)
            to_node = next((n for n in nodes if n["id"] == edge["to"]), None)

            if from_node and to_node:
                fig.add_trace(
                    go.Scatter(
                        x=[from_node["x"], to_node["x"]],
                        y=[from_node["y"], to_node["y"]],
                        mode="lines",
                        line=dict(color="#adb5bd", width=2),
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )

        # Add nodes
        for node in nodes:
            fig.add_trace(
                go.Scatter(
                    x=[node["x"]],
                    y=[node["y"]],
                    mode="markers+text",
                    marker=dict(size=40, color=node["color"]),
                    text=[node["label"]],
                    textposition="middle center",
                    textfont=dict(size=10, color="white"),
                    hoverinfo="text",
                    showlegend=False,
                )
            )

        fig.update_layout(
            title=dict(text=f"Rule Flowchart: {title}", x=0.5),
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange="reversed"),
            plot_bgcolor="white",
            height=max(400, len(nodes) * 80),
        )

        return fig

    def _create_empty_figure(self, message: str) -> go.Figure:
        """Create an empty figure with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=200,
        )
        return fig

    def create_results_summary_chart(self, results_df: pd.DataFrame) -> go.Figure:
        """Create a summary pie chart of categorization results."""
        if "Status" not in results_df.columns:
            return self._create_empty_figure("No status data available")

        status_counts = results_df["Status"].value_counts()

        colors = [OUTCOME_COLORS.get(status, "#6c757d") for status in status_counts.index]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=status_counts.index,
                    values=status_counts.values,
                    hole=0.4,
                    marker=dict(colors=colors),
                    textinfo="label+percent",
                    textposition="outside",
                )
            ]
        )

        fig.update_layout(
            title=dict(text="Categorization Results", x=0.5),
            showlegend=True,
            height=400,
        )

        return fig

    def create_confidence_distribution_chart(self, results_df: pd.DataFrame) -> go.Figure:
        """Create a histogram of confidence scores."""
        if "ConfidenceScore" not in results_df.columns:
            return self._create_empty_figure("No confidence data available")

        fig = go.Figure()

        # Add histogram
        fig.add_trace(
            go.Histogram(
                x=results_df["ConfidenceScore"],
                nbinsx=20,
                name="Confidence Distribution",
                marker=dict(color="#007bff", line=dict(color="white", width=1)),
            )
        )

        # Add vertical lines for confidence bands
        for threshold, color, label in [
            (85, CONFIDENCE_COLORS["high"], "High (85+)"),
            (60, CONFIDENCE_COLORS["medium"], "Medium (60-84)"),
            (40, CONFIDENCE_COLORS["low"], "Low (40-59)"),
        ]:
            fig.add_vline(
                x=threshold,
                line_dash="dash",
                line_color=color,
                annotation_text=label,
                annotation_position="top",
            )

        fig.update_layout(
            title=dict(text="Confidence Score Distribution", x=0.5),
            xaxis_title="Confidence Score",
            yaxis_title="Count",
            height=400,
        )

        return fig

    def create_dashboard(self, results_df: pd.DataFrame) -> go.Figure:
        """Create a dashboard with multiple charts."""
        if results_df.empty:
            return self._create_empty_figure("No data available")

        fig = make_subplots(
            rows=2,
            cols=2,
            specs=[
                [{"type": "pie"}, {"type": "histogram"}],
                [{"type": "bar", "colspan": 2}, None],
            ],
            subplot_titles=(
                "Status Distribution",
                "Confidence Distribution",
                "Status by Category",
            ),
            vertical_spacing=0.15,
            horizontal_spacing=0.1,
        )

        # Pie chart - Status distribution
        if "Status" in results_df.columns:
            status_counts = results_df["Status"].value_counts()
            colors = [OUTCOME_COLORS.get(s, "#6c757d") for s in status_counts.index]
            fig.add_trace(
                go.Pie(
                    labels=status_counts.index,
                    values=status_counts.values,
                    hole=0.4,
                    marker=dict(colors=colors),
                    showlegend=True,
                ),
                row=1,
                col=1,
            )

        # Histogram - Confidence distribution
        if "ConfidenceScore" in results_df.columns:
            fig.add_trace(
                go.Histogram(
                    x=results_df["ConfidenceScore"],
                    nbinsx=20,
                    marker=dict(color="#007bff"),
                    showlegend=False,
                ),
                row=1,
                col=2,
            )

        # Bar chart - Status by Category
        if "Status" in results_df.columns and "Category" in results_df.columns:
            category_status = (
                results_df.groupby(["Category", "Status"]).size().unstack(fill_value=0)
            )
            for status in ["ACCEPTED", "REJECTED", "RECONSIDER"]:
                if status in category_status.columns:
                    fig.add_trace(
                        go.Bar(
                            x=category_status.index,
                            y=category_status[status],
                            name=status,
                            marker_color=OUTCOME_COLORS.get(status, "#6c757d"),
                        ),
                        row=2,
                        col=1,
                    )

        fig.update_layout(
            height=800,
            title=dict(text="Results Dashboard", x=0.5, font=dict(size=20)),
            barmode="group",
        )

        return fig

    def create_rule_preview_table(
        self, ruleset: RuleSet, sample_df: pd.DataFrame, num_samples: int = 5
    ) -> pd.DataFrame:
        """Create a preview table showing sample rows with expected outcomes."""
        from .logic_engine import LogicEngine

        if sample_df.empty:
            return pd.DataFrame({"Message": ["No sample data available"]})

        engine = LogicEngine(ruleset)
        preview_data = []

        for idx, row in sample_df.head(num_samples).iterrows():
            result = engine.evaluate_row(row)

            preview_row = {
                "Row #": idx + 1,
                "Work ID": row.get("Work ID", "N/A"),
                "Description": str(row.get("Description", "N/A"))[:50] + "...",
                "Expected Status": result.outcome.value,
                "Confidence": f"{result.score:.0f}%",
                "Matched Rules": ", ".join(result.matched_rules[:2]) or "Default",
            }
            preview_data.append(preview_row)

        return pd.DataFrame(preview_data)

    def create_category_breakdown_chart(self, results_df: pd.DataFrame) -> go.Figure:
        """Create a chart showing breakdown by category."""
        if "Category" not in results_df.columns or "Status" not in results_df.columns:
            return self._create_empty_figure("Category or Status data not available")

        # Group by category and status
        grouped = results_df.groupby(["Category", "Status"]).size().reset_index(name="Count")

        fig = px.bar(
            grouped,
            x="Category",
            y="Count",
            color="Status",
            color_discrete_map=OUTCOME_COLORS,
            barmode="group",
            title="Status Distribution by Category",
        )

        fig.update_layout(height=400)
        return fig

    def create_priority_analysis_chart(self, results_df: pd.DataFrame) -> go.Figure:
        """Create a chart analyzing results by priority."""
        if "Priority" not in results_df.columns or "Status" not in results_df.columns:
            return self._create_empty_figure("Priority or Status data not available")

        # Group by priority and status
        grouped = results_df.groupby(["Priority", "Status"]).size().reset_index(name="Count")

        fig = px.bar(
            grouped,
            x="Priority",
            y="Count",
            color="Status",
            color_discrete_map=OUTCOME_COLORS,
            barmode="stack",
            title="Status Distribution by Priority",
        )

        fig.update_layout(height=400)
        return fig

    def create_confidence_by_status_chart(self, results_df: pd.DataFrame) -> go.Figure:
        """Create a box plot showing confidence distribution by status."""
        if "ConfidenceScore" not in results_df.columns or "Status" not in results_df.columns:
            return self._create_empty_figure("Required data not available")

        fig = px.box(
            results_df,
            x="Status",
            y="ConfidenceScore",
            color="Status",
            color_discrete_map=OUTCOME_COLORS,
            title="Confidence Score Distribution by Status",
        )

        fig.update_layout(height=400, showlegend=False)
        return fig
