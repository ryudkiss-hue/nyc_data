"""Project Analyst Reports Module - NYC DOT Sidewalk Toolkit.

Provides reporting and analysis capabilities for Project Analysts to:
- Audit budget/progress changes with full before/after history
- Validate construction lists against design standards
- Trace data lineage for all metrics and KPIs
- Generate compliance reports

This module leverages the unified governance event stream to enable
transparent, auditable sidewalk program management.

Classes:
    ProjectAnalystReports: Main reporting interface

Example:
    >>> reports = ProjectAnalystReports(dsn="postgresql://...")
    >>> audit = reports.contract_budget_audit(contract_id="CONTR-2026-001")
    >>> print(f"Budget changed {len(audit)} times")
    >>> compliance = reports.construction_compliance(project_id="PROJ-2026-001")
    >>> print(f"Violations: {compliance['violations_count']}")
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    from socrata_toolkit.governance_processor import GovernanceProcessor
except ImportError:
    GovernanceProcessor = None  # type: ignore

logger = logging.getLogger(__name__)


class ProjectAnalystReports:
    """Generate reports for Project Analysts from governance data.
    
    Provides specialized reporting views for construction list management,
    budget tracking, and compliance validation.
    """
    
    def __init__(self, governance_processor: GovernanceProcessor):
        """Initialize reports with governance processor.
        
        Args:
            governance_processor: GovernanceProcessor instance
        """
        self.governance = governance_processor
        self.logger = logger.getChild(self.__class__.__name__)
    
    def contract_budget_audit(
        self,
        contract_id: str,
        days_back: int = 90,
    ) -> Dict[str, Any]:
        """Generate audit trail for contract budget changes.
        
        Shows all budget modifications with who, when, before/after values.
        Enables verification of spend accuracy and compliance.
        
        Args:
            contract_id: Contract identifier
            days_back: How many days of history to include
            
        Returns:
            Report with budget changes, totals, and variance analysis
            
        Example:
            >>> audit = reports.contract_budget_audit("CONTR-2026-001")
            >>> for change in audit['changes']:
            ...     print(f"{change['date']}: {change['old_budget']} → {change['new_budget']}")
        """
        try:
            # Get audit trail for contract
            audit_trail = self.governance.get_audit_trail(
                "contracts",
                contract_id,
                limit=500
            )
            
            budget_changes = []
            for event in audit_trail:
                if event.after and 'budget_amount' in event.after:
                    old_value = None
                    if event.before and 'budget_amount' in event.before:
                        old_value = event.before['budget_amount']
                    
                    budget_changes.append({
                        'event_id': event.event_id,
                        'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                        'operation': event.operation,
                        'old_budget': old_value,
                        'new_budget': event.after['budget_amount'],
                        'user_id': event.user_id,
                        'reason': event.change_reason,
                        'schema_valid': event.schema_valid,
                        'compliant': event.is_compliant,
                    })
            
            # Calculate variance
            if budget_changes:
                initial_budget = budget_changes[-1]['old_budget'] or 0
                final_budget = budget_changes[0]['new_budget'] or 0
                variance = final_budget - initial_budget
            else:
                initial_budget = 0
                final_budget = 0
                variance = 0
            
            return {
                'contract_id': contract_id,
                'changes_count': len(budget_changes),
                'initial_budget': initial_budget,
                'final_budget': final_budget,
                'variance': variance,
                'changes': budget_changes,
                'generated_at': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Budget audit error for {contract_id}: {e}")
            return {
                'contract_id': contract_id,
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat(),
            }
    
    def construction_compliance(
        self,
        project_id: str,
        segment_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate construction list against design standards.
        
        Checks that all segments in project comply with:
        - NYC Street Design Manual material requirements
        - ADA accessibility standards
        - Surface treatment specifications
        
        Args:
            project_id: Project identifier
            segment_ids: Optional list of specific segments to check
            
        Returns:
            Report with compliance violations and remediation steps
            
        Example:
            >>> compliance = reports.construction_compliance("PROJ-2026-001")
            >>> if compliance['is_compliant']:
            ...     print("All segments compliant!")
            ... else:
            ...     for v in compliance['violations']:
            ...         print(f"Segment {v['segment_id']}: {v['violation']}")
        """
        try:
            violations = self.governance.get_compliance_violations("segments")
            
            project_violations = []
            for violation in violations:
                # Filter by project/segment
                if segment_ids and violation.get('record_id') not in segment_ids:
                    continue
                
                project_violations.append({
                    'segment_id': violation['record_id'],
                    'violations': violation['violations'],
                    'timestamp': violation['timestamp'].isoformat(),
                    'remediation_required': len(violation['violations']) > 0,
                })
            
            return {
                'project_id': project_id,
                'is_compliant': len(project_violations) == 0,
                'violations_count': len(project_violations),
                'violations': project_violations,
                'generated_at': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Compliance check error for {project_id}: {e}")
            return {
                'project_id': project_id,
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat(),
            }
    
    def data_lineage_for_metric(
        self,
        metric_name: str,
        dataset: str,
    ) -> Dict[str, Any]:
        """Trace data lineage for a metric.
        
        Shows which source datasets fed into this metric and all
        transformations applied. Enables understanding of metric
        definitions and validation of calculation logic.
        
        Args:
            metric_name: Metric name (e.g., 'defect_density')
            dataset: Target dataset containing the metric
            
        Returns:
            Report with lineage chain and transformation steps
            
        Example:
            >>> lineage = reports.data_lineage_for_metric(
            ...     "defect_density", "sidewalk_kpis"
            ... )
            >>> print(f"Source: {lineage['sources']}")
            >>> print(f"Transformations: {lineage['transformations']}")
        """
        try:
            audit_trail = self.governance.get_audit_trail(dataset, metric_name, limit=100)
            
            lineage_chain = []
            for event in audit_trail:
                if event.lineage_metadata:
                    lineage_chain.append({
                        'event_id': event.event_id,
                        'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                        'operation': event.operation,
                        'columns': event.lineage_metadata.get('changed_columns', []),
                        'source_dataset': event.lineage_metadata.get('dataset'),
                    })
            
            return {
                'metric_name': metric_name,
                'dataset': dataset,
                'lineage_depth': len(lineage_chain),
                'lineage_chain': lineage_chain,
                'generated_at': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Lineage trace error for {metric_name}: {e}")
            return {
                'metric_name': metric_name,
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat(),
            }
    
    def repair_progress_summary(
        self,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """Generate repair progress summary for period.
        
        Shows completion rate, budget burn, and variance analysis
        across all active construction contracts.
        
        Args:
            days_back: Number of days to include in summary
            
        Returns:
            Report with progress metrics and trends
        """
        try:
            # Get repairs from audit trail in period
            start_date = datetime.utcnow() - timedelta(days=days_back)
            
            audit_trail = self.governance.get_audit_trail(
                "repairs",
                "summary",
                limit=1000
            )
            
            total_repairs = 0
            completed_repairs = 0
            total_budget = 0
            spent_budget = 0
            
            for event in audit_trail:
                if event.timestamp and event.timestamp >= start_date:
                    if event.operation == "INSERT":
                        total_repairs += 1
                        if event.after:
                            total_budget += event.after.get('budget', 0)
                    elif event.operation == "UPDATE" and event.after:
                        if event.after.get('status') == 'completed':
                            completed_repairs += 1
                            spent_budget += event.after.get('spent', 0)
            
            completion_rate = (
                (completed_repairs / total_repairs * 100)
                if total_repairs > 0 else 0
            )
            
            budget_variance = spent_budget - total_budget
            
            return {
                'period_days': days_back,
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat(),
                'total_repairs': total_repairs,
                'completed_repairs': completed_repairs,
                'completion_rate': round(completion_rate, 2),
                'total_budget': total_budget,
                'spent_budget': spent_budget,
                'budget_variance': budget_variance,
                'variance_percent': round(
                    (budget_variance / total_budget * 100) if total_budget > 0 else 0,
                    2
                ),
                'generated_at': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Repair progress summary error: {e}")
            return {
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat(),
            }
    
    def contractor_performance_audit(
        self,
        contractor_id: str,
    ) -> Dict[str, Any]:
        """Audit contractor performance metrics.
        
        Shows quality score changes, schedule compliance, budget adherence,
        and material standard violations over time.
        
        Args:
            contractor_id: Contractor identifier
            
        Returns:
            Report with performance trends and incidents
        """
        try:
            audit_trail = self.governance.get_audit_trail(
                "contractors",
                contractor_id,
                limit=500
            )
            
            score_changes = []
            violations = 0
            
            for event in audit_trail:
                if event.after and 'quality_score' in event.after:
                    score_changes.append({
                        'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                        'score': event.after['quality_score'],
                    })
                
                if event.design_rule_violations:
                    violations += len(event.design_rule_violations)
            
            avg_score = (
                sum(s['score'] for s in score_changes) / len(score_changes)
                if score_changes else 0
            )
            
            return {
                'contractor_id': contractor_id,
                'performance_changes': len(score_changes),
                'avg_quality_score': round(avg_score, 2),
                'design_violations': violations,
                'score_history': score_changes,
                'generated_at': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Contractor audit error for {contractor_id}: {e}")
            return {
                'contractor_id': contractor_id,
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat(),
            }
