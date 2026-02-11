"""
Export module for MWCS - generates output files in various formats.
"""

import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""

    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"


@dataclass
class AuditMetadata:
    """Audit metadata for exports."""

    processing_timestamp: str
    logic_version_id: str
    total_records: int
    accepted_count: int
    rejected_count: int
    reconsider_count: int
    processing_duration_ms: float
    data_quality_metrics: dict[str, Any]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "processing_timestamp": self.processing_timestamp,
            "logic_version_id": self.logic_version_id,
            "total_records": self.total_records,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "reconsider_count": self.reconsider_count,
            "processing_duration_ms": self.processing_duration_ms,
            "data_quality_metrics": self.data_quality_metrics,
        }


class ExportManager:
    """Manages export of categorization results."""

    def __init__(self):
        """Initialize the export manager."""
        self._results_df: Optional[pd.DataFrame] = None
        self._metadata: Optional[AuditMetadata] = None

    def prepare_export(
        self,
        original_df: pd.DataFrame,
        evaluation_results: list,
        justification_results: list,
        processing_time_ms: float,
        logic_version: str = "1.0",
    ) -> pd.DataFrame:
        """Prepare data for export by combining original data with results."""
        # Create copy of original dataframe
        export_df = original_df.copy()

        # Add result columns
        statuses = []
        justifications = []
        confidence_scores = []

        for eval_result, just_result in zip(evaluation_results, justification_results):
            statuses.append(eval_result.outcome.value)
            justifications.append(just_result.justification)
            # Use AI confidence if available, otherwise use rule engine confidence
            confidence = (
                just_result.confidence_score
                if just_result.confidence_score > 0
                else eval_result.score
            )
            confidence_scores.append(confidence)

        export_df["Status"] = statuses
        export_df["Justification"] = justifications
        export_df["ConfidenceScore"] = confidence_scores

        # Calculate counts
        accepted = statuses.count("ACCEPTED")
        rejected = statuses.count("REJECTED")
        reconsider = statuses.count("RECONSIDER")

        # Calculate data quality metrics
        quality_metrics = self._calculate_quality_metrics(export_df, confidence_scores)

        # Create metadata
        self._metadata = AuditMetadata(
            processing_timestamp=datetime.now().isoformat(),
            logic_version_id=logic_version,
            total_records=len(export_df),
            accepted_count=accepted,
            rejected_count=rejected,
            reconsider_count=reconsider,
            processing_duration_ms=processing_time_ms,
            data_quality_metrics=quality_metrics,
        )

        self._results_df = export_df
        logger.info(f"Prepared {len(export_df)} rows for export")

        return export_df

    def _calculate_quality_metrics(
        self, df: pd.DataFrame, confidence_scores: list
    ) -> dict[str, Any]:
        """Calculate data quality metrics."""
        metrics = {
            "total_rows": len(df),
            "null_percentage": (df.isnull().sum().sum() / df.size * 100) if df.size > 0 else 0,
            "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "high_confidence_count": sum(1 for c in confidence_scores if c >= 85),
            "low_confidence_count": sum(1 for c in confidence_scores if c < 40),
        }
        return metrics

    def export_xlsx(self, filepath: Optional[str] = None) -> io.BytesIO:
        """Export results to Excel format."""
        if self._results_df is None:
            raise ValueError("No data to export. Call prepare_export() first.")

        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            # Main results sheet
            self._results_df.to_excel(writer, sheet_name="Results", index=False)

            # Summary sheet
            summary_df = self._create_summary_df()
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

            # Metadata sheet
            if self._metadata:
                metadata_df = pd.DataFrame([self._metadata.to_dict()])
                metadata_df.to_excel(writer, sheet_name="Audit_Metadata", index=False)

        buffer.seek(0)

        if filepath:
            with open(filepath, "wb") as f:
                f.write(buffer.getvalue())
            logger.info(f"Exported to {filepath}")

        return buffer

    def export_csv(self, filepath: Optional[str] = None) -> io.StringIO:
        """Export results to CSV format (UTF-8)."""
        if self._results_df is None:
            raise ValueError("No data to export. Call prepare_export() first.")

        buffer = io.StringIO()
        self._results_df.to_csv(buffer, index=False, encoding="utf-8")
        buffer.seek(0)

        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(buffer.getvalue())
            logger.info(f"Exported to {filepath}")

        return buffer

    def export_json(self, filepath: Optional[str] = None) -> str:
        """Export results to JSON format."""
        if self._results_df is None:
            raise ValueError("No data to export. Call prepare_export() first.")

        export_data = {
            "metadata": self._metadata.to_dict() if self._metadata else {},
            "summary": self._create_summary_dict(),
            "results": self._results_df.to_dict(orient="records"),
        }

        json_str = json.dumps(export_data, indent=2, default=str)

        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
            logger.info(f"Exported to {filepath}")

        return json_str

    def export(
        self, format: ExportFormat, filepath: Optional[str] = None
    ) -> io.BytesIO | io.StringIO | str:
        """Export results in the specified format."""
        if format == ExportFormat.XLSX:
            return self.export_xlsx(filepath)
        elif format == ExportFormat.CSV:
            return self.export_csv(filepath)
        elif format == ExportFormat.JSON:
            return self.export_json(filepath)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _create_summary_df(self) -> pd.DataFrame:
        """Create a summary DataFrame."""
        if self._results_df is None or self._metadata is None:
            return pd.DataFrame()

        summary_data = [
            {"Metric": "Total Records", "Value": self._metadata.total_records},
            {"Metric": "Accepted", "Value": self._metadata.accepted_count},
            {"Metric": "Rejected", "Value": self._metadata.rejected_count},
            {"Metric": "Needs Reconsideration", "Value": self._metadata.reconsider_count},
            {
                "Metric": "Accepted %",
                "Value": f"{self._metadata.accepted_count / self._metadata.total_records * 100:.1f}%"
                if self._metadata.total_records > 0
                else "0%",
            },
            {
                "Metric": "Processing Time (ms)",
                "Value": f"{self._metadata.processing_duration_ms:.2f}",
            },
            {"Metric": "Logic Version", "Value": self._metadata.logic_version_id},
            {
                "Metric": "Processing Timestamp",
                "Value": self._metadata.processing_timestamp,
            },
            {
                "Metric": "Avg Confidence Score",
                "Value": f"{self._metadata.data_quality_metrics.get('avg_confidence', 0):.1f}",
            },
        ]

        return pd.DataFrame(summary_data)

    def _create_summary_dict(self) -> dict[str, Any]:
        """Create a summary dictionary."""
        if self._results_df is None or self._metadata is None:
            return {}

        return {
            "total_records": self._metadata.total_records,
            "status_counts": {
                "accepted": self._metadata.accepted_count,
                "rejected": self._metadata.rejected_count,
                "reconsider": self._metadata.reconsider_count,
            },
            "percentages": {
                "accepted": (
                    self._metadata.accepted_count / self._metadata.total_records * 100
                    if self._metadata.total_records > 0
                    else 0
                ),
                "rejected": (
                    self._metadata.rejected_count / self._metadata.total_records * 100
                    if self._metadata.total_records > 0
                    else 0
                ),
                "reconsider": (
                    self._metadata.reconsider_count / self._metadata.total_records * 100
                    if self._metadata.total_records > 0
                    else 0
                ),
            },
            "confidence_bands": self._get_confidence_bands(),
        }

    def _get_confidence_bands(self) -> dict[str, int]:
        """Get confidence score distribution by band."""
        if self._results_df is None or "ConfidenceScore" not in self._results_df.columns:
            return {}

        scores = self._results_df["ConfidenceScore"]
        return {
            "high_85_100": int((scores >= 85).sum()),
            "medium_60_84": int(((scores >= 60) & (scores < 85)).sum()),
            "low_40_59": int(((scores >= 40) & (scores < 60)).sum()),
            "very_low_0_39": int((scores < 40).sum()),
        }

    def get_filtered_export(
        self,
        status_filter: Optional[list[str]] = None,
        confidence_min: Optional[float] = None,
        confidence_max: Optional[float] = None,
    ) -> pd.DataFrame:
        """Get filtered results for export."""
        if self._results_df is None:
            raise ValueError("No data available. Call prepare_export() first.")

        filtered_df = self._results_df.copy()

        if status_filter:
            filtered_df = filtered_df[filtered_df["Status"].isin(status_filter)]

        if confidence_min is not None:
            filtered_df = filtered_df[filtered_df["ConfidenceScore"] >= confidence_min]

        if confidence_max is not None:
            filtered_df = filtered_df[filtered_df["ConfidenceScore"] <= confidence_max]

        return filtered_df

    @property
    def results_df(self) -> Optional[pd.DataFrame]:
        """Get the current results DataFrame."""
        return self._results_df

    @property
    def metadata(self) -> Optional[AuditMetadata]:
        """Get the current audit metadata."""
        return self._metadata

    def get_download_filename(self, format: ExportFormat, prefix: str = "mwcs_results") -> str:
        """Generate a filename for download."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{format.value}"
