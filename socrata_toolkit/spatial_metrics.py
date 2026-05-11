"""
Spatial Metrics and Observability Integration.

Integrates spatial data quality and coverage metrics with monitoring systems:
- Spatial coverage metrics (% of street network with data)
- Material distribution tracking
- Inspection density analysis
- Data gap identification
- SLA compliance monitoring
- Geographic completeness scoring
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SpatialCoverageMetric:
    """Spatial coverage metric."""
    metric_name: str
    value: float
    unit: str  # "percent", "count", "density", "km2"
    borough: Optional[str] = None
    district: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class MaterialDistributionMetric:
    """Material distribution by geography."""
    material_type: str
    total_length_meters: float
    segment_count: int
    percentage: float
    average_condition: float
    borough: Optional[str] = None


@dataclass
class InspectionDensityMetric:
    """Inspection activity density."""
    area_name: str
    inspections_per_km2: float
    total_inspections: int
    unique_segments_inspected: int
    time_period_days: int
    last_inspection_age_days: int


@dataclass
class SLAComplianceMetric:
    """SLA compliance status."""
    metric_name: str
    target_value: float
    actual_value: float
    compliance_percentage: float
    status: str  # "compliant", "at_risk", "non_compliant"
    borough: Optional[str] = None


class SpatialMetricsCollector:
    """
    Collects and aggregates spatial metrics for monitoring and KPIs.
    
    Integrates with observability stack (Prometheus, Grafana, etc.).
    """
    
    def __init__(self, db_connection: Any = None) -> None:
        """
        Initialize metrics collector.
        
        Args:
            db_connection: Optional database connection for querying
        """
        self.db_connection = db_connection
        self.metrics: list[dict[str, Any]] = []
        self.collection_timestamp = datetime.utcnow()
    
    def calculate_coverage_by_borough(self) -> list[SpatialCoverageMetric]:
        """
        Calculate percentage of street network covered by borough.
        
        Returns:
            List of coverage metrics by borough
        """
        try:
            if not self.db_connection:
                logger.warning("No database connection for coverage calculation")
                return []
            
            metrics = []
            
            # In production, would query database
            boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
            
            for borough in boroughs:
                # Calculate: segments with data / total street network length
                coverage_percent = self._get_borough_coverage(borough)
                
                metric = SpatialCoverageMetric(
                    metric_name="street_network_coverage_percent",
                    value=coverage_percent,
                    unit="percent",
                    borough=borough,
                )
                metrics.append(metric)
            
            logger.info(f"Calculated coverage for {len(metrics)} boroughs")
            return metrics
        
        except Exception as e:
            logger.error(f"Error calculating coverage by borough: {e}")
            return []
    
    def calculate_material_distribution(
        self,
        borough: Optional[str] = None,
    ) -> list[MaterialDistributionMetric]:
        """
        Calculate distribution of sidewalk materials.
        
        Args:
            borough: Optional filter by borough
            
        Returns:
            List of material distribution metrics
        """
        try:
            if not self.db_connection:
                return []
            
            metrics = []
            
            # Material types
            materials = ["asphalt", "concrete", "brick", "stone", "other"]
            
            for material in materials:
                # Query total length and count for each material
                result = self._get_material_stats(material, borough)
                
                metric = MaterialDistributionMetric(
                    material_type=material,
                    total_length_meters=result.get("length", 0),
                    segment_count=result.get("count", 0),
                    percentage=result.get("percentage", 0),
                    average_condition=result.get("avg_condition", 0),
                    borough=borough,
                )
                metrics.append(metric)
            
            logger.info(f"Calculated material distribution for {len(metrics)} materials")
            return metrics
        
        except Exception as e:
            logger.error(f"Error calculating material distribution: {e}")
            return []
    
    def calculate_inspection_density(
        self,
        area_name: str,
        days_lookback: int = 30,
    ) -> Optional[InspectionDensityMetric]:
        """
        Calculate inspection activity density.
        
        Args:
            area_name: Geographic area name
            days_lookback: Number of days to look back
            
        Returns:
            InspectionDensityMetric or None if error
        """
        try:
            if not self.db_connection:
                return None
            
            # Query inspection data
            result = self._get_inspection_stats(area_name, days_lookback)
            
            if not result:
                return None
            
            metric = InspectionDensityMetric(
                area_name=area_name,
                inspections_per_km2=result.get("density", 0),
                total_inspections=result.get("total", 0),
                unique_segments_inspected=result.get("segments", 0),
                time_period_days=days_lookback,
                last_inspection_age_days=result.get("age_days", 999),
            )
            
            logger.info(f"Inspection density for {area_name}: {metric.inspections_per_km2:.2f} per km²")
            return metric
        
        except Exception as e:
            logger.error(f"Error calculating inspection density: {e}")
            return None
    
    def calculate_sla_compliance(
        self,
        sla_definition: dict[str, Any],
    ) -> list[SLAComplianceMetric]:
        """
        Calculate SLA compliance for spatial data quality.
        
        Args:
            sla_definition: SLA definition with targets
            
        Returns:
            List of SLA compliance metrics
        """
        try:
            metrics = []
            
            # Example SLAs:
            # 1. 95% of street network must have data
            # 2. 50% of segments inspected within 12 months
            # 3. Average condition score >= 60
            
            slas = [
                {
                    "name": "coverage_target",
                    "target": sla_definition.get("coverage_percent", 95),
                    "actual": self._get_actual_coverage(),
                },
                {
                    "name": "inspection_frequency",
                    "target": sla_definition.get("inspection_percent", 50),
                    "actual": self._get_inspection_frequency(),
                },
                {
                    "name": "average_condition",
                    "target": sla_definition.get("min_condition", 60),
                    "actual": self._get_average_condition(),
                },
            ]
            
            for sla in slas:
                compliance_percent = (sla["actual"] / sla["target"] * 100) if sla["target"] > 0 else 0
                
                if compliance_percent >= 100:
                    status = "compliant"
                elif compliance_percent >= 90:
                    status = "at_risk"
                else:
                    status = "non_compliant"
                
                metric = SLAComplianceMetric(
                    metric_name=sla["name"],
                    target_value=sla["target"],
                    actual_value=sla["actual"],
                    compliance_percentage=min(compliance_percent, 100),
                    status=status,
                )
                metrics.append(metric)
            
            logger.info(f"Calculated SLA compliance: {len(metrics)} metrics")
            return metrics
        
        except Exception as e:
            logger.error(f"Error calculating SLA compliance: {e}")
            return []
    
    def calculate_spatial_gaps(self) -> dict[str, Any]:
        """
        Identify geographic areas with missing or incomplete data.
        
        Returns:
            Dictionary with gap analysis results
        """
        try:
            if not self.db_connection:
                return {}
            
            gaps = {
                "total_gaps": 0,
                "critical_gaps": [],
                "high_priority_gaps": [],
                "medium_priority_gaps": [],
            }
            
            # In production, would query for areas with:
            # - No segments (complete gaps)
            # - No recent inspections
            # - All segments in poor condition
            
            # Query critical gaps (no data at all)
            critical = self._get_critical_gaps()
            gaps["critical_gaps"] = critical
            gaps["total_gaps"] += len(critical)
            
            # Query high priority gaps (no recent inspections)
            high = self._get_high_priority_gaps()
            gaps["high_priority_gaps"] = high
            gaps["total_gaps"] += len(high)
            
            logger.info(f"Identified {gaps['total_gaps']} geographic gaps")
            return gaps
        
        except Exception as e:
            logger.error(f"Error calculating spatial gaps: {e}")
            return {}
    
    def export_metrics_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics text
        """
        lines = [
            "# HELP sidewalk_spatial_coverage_percent Percentage of street network with data",
            "# TYPE sidewalk_spatial_coverage_percent gauge",
        ]
        
        coverage_metrics = self.calculate_coverage_by_borough()
        for metric in coverage_metrics:
            labels = f'borough="{metric.borough}"'
            lines.append(f"sidewalk_spatial_coverage_percent{{{labels}}} {metric.value}")
        
        lines.append("")
        lines.append("# HELP sidewalk_inspection_density_per_km2 Inspections per square kilometer")
        lines.append("# TYPE sidewalk_inspection_density_per_km2 gauge")
        
        # Add inspection density metrics
        
        return "\n".join(lines)
    
    def export_metrics_json(self) -> dict[str, Any]:
        """
        Export metrics as JSON for API response.
        
        Returns:
            Dictionary with all metrics
        """
        return {
            "timestamp": self.collection_timestamp.isoformat(),
            "coverage": [
                {
                    "metric": m.metric_name,
                    "value": m.value,
                    "unit": m.unit,
                    "borough": m.borough,
                }
                for m in self.calculate_coverage_by_borough()
            ],
            "materials": [
                {
                    "type": m.material_type,
                    "length_meters": m.total_length_meters,
                    "segment_count": m.segment_count,
                    "percentage": m.percentage,
                    "avg_condition": m.average_condition,
                }
                for m in self.calculate_material_distribution()
            ],
            "sla_compliance": [
                {
                    "metric": m.metric_name,
                    "target": m.target_value,
                    "actual": m.actual_value,
                    "compliance_percent": m.compliance_percentage,
                    "status": m.status,
                }
                for m in self.calculate_sla_compliance({})
            ],
        }
    
    # Helper methods (would query database in production)
    
    def _get_borough_coverage(self, borough: str) -> float:
        """Get coverage percentage for borough."""
        # Placeholder: would query database
        coverage_map = {
            "Manhattan": 89.5,
            "Brooklyn": 87.2,
            "Queens": 82.1,
            "Bronx": 80.5,
            "Staten Island": 75.3,
        }
        return coverage_map.get(borough, 0)
    
    def _get_material_stats(
        self,
        material: str,
        borough: Optional[str] = None,
    ) -> dict[str, float]:
        """Get statistics for material type."""
        # Placeholder: would query database
        return {
            "length": 1500.0 if material == "asphalt" else 1200.0,
            "count": 50 if material == "asphalt" else 40,
            "percentage": 55 if material == "asphalt" else 45,
            "avg_condition": 65 if material == "concrete" else 55,
        }
    
    def _get_inspection_stats(
        self,
        area_name: str,
        days_lookback: int,
    ) -> dict[str, float]:
        """Get inspection statistics."""
        # Placeholder: would query database
        return {
            "density": 12.5,
            "total": 45,
            "segments": 30,
            "age_days": 5,
        }
    
    def _get_actual_coverage(self) -> float:
        """Get actual coverage percentage."""
        return 87.5  # Placeholder
    
    def _get_inspection_frequency(self) -> float:
        """Get percentage of segments inspected recently."""
        return 48.2  # Placeholder
    
    def _get_average_condition(self) -> float:
        """Get average condition score."""
        return 62.4  # Placeholder
    
    def _get_critical_gaps(self) -> list[dict[str, Any]]:
        """Get areas with no data at all."""
        return []  # Placeholder
    
    def _get_high_priority_gaps(self) -> list[dict[str, Any]]:
        """Get areas needing urgent inspection."""
        return []  # Placeholder


class SpatialQualityScorer:
    """
    Calculate spatial data quality scores for observability.
    
    Combines multiple quality dimensions into single quality metric.
    """
    
    @staticmethod
    def calculate_completeness_score(
        segments_with_data: int,
        total_street_network_segments: int,
    ) -> float:
        """
        Calculate data completeness score (0-100).
        
        Args:
            segments_with_data: Count of segments with data
            total_street_network_segments: Total network segments
            
        Returns:
            Completeness score 0-100
        """
        if total_street_network_segments == 0:
            return 0.0
        
        return (segments_with_data / total_street_network_segments) * 100
    
    @staticmethod
    def calculate_recency_score(
        days_since_last_inspection: int,
        target_inspection_interval_days: int = 365,
    ) -> float:
        """
        Calculate data recency score (0-100).
        
        Args:
            days_since_last_inspection: Days since last inspection
            target_inspection_interval_days: Target inspection interval
            
        Returns:
            Recency score 0-100
        """
        if days_since_last_inspection <= 0:
            return 100.0
        
        if days_since_last_inspection >= target_inspection_interval_days * 2:
            return 0.0
        
        return max(0, 100 - (days_since_last_inspection / target_inspection_interval_days * 100))
    
    @staticmethod
    def calculate_accuracy_score(
        average_gps_accuracy_meters: float,
        target_accuracy_meters: float = 5.0,
    ) -> float:
        """
        Calculate GPS accuracy score (0-100).
        
        Args:
            average_gps_accuracy_meters: Average GPS accuracy
            target_accuracy_meters: Target accuracy
            
        Returns:
            Accuracy score 0-100
        """
        if average_gps_accuracy_meters <= target_accuracy_meters:
            return 100.0
        
        degradation = (average_gps_accuracy_meters - target_accuracy_meters) / target_accuracy_meters
        return max(0, 100 - (degradation * 50))  # 50% penalty per unit
    
    @staticmethod
    def calculate_consistency_score(
        duplicate_segments: int,
        total_segments: int,
    ) -> float:
        """
        Calculate data consistency score (0-100).
        
        Args:
            duplicate_segments: Count of duplicate/conflicting records
            total_segments: Total segments
            
        Returns:
            Consistency score 0-100
        """
        if total_segments == 0:
            return 100.0
        
        duplicate_rate = duplicate_segments / total_segments
        return max(0, 100 - (duplicate_rate * 100))
    
    @staticmethod
    def calculate_overall_quality(
        completeness: float,
        recency: float,
        accuracy: float,
        consistency: float,
        weights: Optional[dict[str, float]] = None,
    ) -> float:
        """
        Calculate weighted overall quality score.
        
        Args:
            completeness: Completeness score 0-100
            recency: Recency score 0-100
            accuracy: Accuracy score 0-100
            consistency: Consistency score 0-100
            weights: Optional weight dictionary
            
        Returns:
            Overall quality score 0-100
        """
        if weights is None:
            weights = {
                "completeness": 0.35,
                "recency": 0.30,
                "accuracy": 0.20,
                "consistency": 0.15,
            }
        
        overall = (
            completeness * weights.get("completeness", 0) +
            recency * weights.get("recency", 0) +
            accuracy * weights.get("accuracy", 0) +
            consistency * weights.get("consistency", 0)
        )
        
        return min(100, max(0, overall))
