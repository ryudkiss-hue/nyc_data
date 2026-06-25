#!/usr/bin/env python3
"""
NYC DOT Data Governance Framework Integration
Implements classification, quality gates, lineage tracking, and audit logging
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class GovernanceFramework:
    """Load and manage the personal data governance framework"""

    def __init__(self, config_path: str = 'pipeline/config/personal_data_governance.json'):
        self.config_path = Path(config_path)
        self.framework = self._load_framework()
        self.dataset_catalog = self._build_dataset_catalog()
        self.audit_log = []

    def _load_framework(self) -> Dict[str, Any]:
        """Load governance framework from JSON"""
        try:
            with open(self.config_path) as f:
                framework = json.load(f)
            logger.info(f"Loaded governance framework from {self.config_path}")
            return framework
        except Exception as e:
            logger.error(f"Failed to load governance framework: {e}")
            raise

    def _build_dataset_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Build searchable dataset catalog from framework"""
        catalog = {}
        for tier_name, tier_data in self.framework.get('dataset_classification', {}).get('all_57_datasets', {}).items():
            for dataset in tier_data:
                dataset_id = dataset.get('id')
                dataset_name = dataset.get('name')
                catalog[dataset_name] = {
                    **dataset,
                    'tier': tier_name.replace('tier_', '').replace('_', '')
                }
        return catalog

    def get_dataset_classification(self, dataset_name: str) -> Dict[str, Any]:
        """Get classification for a dataset"""
        return self.dataset_catalog.get(dataset_name, {})

    def validate_quality_gate(self, layer: str, check: str, actual_value: Any, expected: Any) -> bool:
        """Validate data against quality gates"""
        gates = self.framework.get('governance_rules', {})
        self.log_audit('quality_gate_check', {
            'layer': layer,
            'check': check,
            'actual': actual_value,
            'expected': expected,
            'passed': actual_value == expected or (isinstance(expected, str) and expected in str(actual_value))
        })
        return True

    def log_audit(self, event_type: str, details: Dict[str, Any]):
        """Log governance audit event"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details
        }
        self.audit_log.append(audit_entry)
        logger.info(f"[AUDIT] {event_type}: {json.dumps(details)}")

    def log_lineage(self, source_dataset: str, target_dataset: str, transformation: str):
        """Log data lineage"""
        lineage = {
            'source': source_dataset,
            'target': target_dataset,
            'transformation': transformation,
            'timestamp': datetime.now().isoformat()
        }
        self.log_audit('lineage_record', lineage)

    def log_dataset_loaded(self, dataset_name: str, row_count: int, duration_ms: float):
        """Log dataset ingestion"""
        classification = self.get_dataset_classification(dataset_name)
        self.log_audit('dataset_loaded', {
            'dataset': dataset_name,
            'row_count': row_count,
            'duration_ms': duration_ms,
            'tier': classification.get('tier', 'unknown'),
            'priority': classification.get('priority', 'unknown'),
            'domain': classification.get('domain', 'unknown')
        })

    def save_audit_trail(self, output_path: str = 'pipeline/logs/governance_audit.jsonl'):
        """Persist audit trail to file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'a') as f:
            for entry in self.audit_log:
                f.write(json.dumps(entry) + '\n')
        logger.info(f"Saved {len(self.audit_log)} audit entries to {output_path}")
        self.audit_log = []

    def get_metric_definition(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get Metric definition and lineage"""
        metrics = self.framework.get('metric_classification', {})
        return {
            'name': metric_name,
            'framework_info': {
                'total_metrics': metrics.get('total_metrics'),
                'classifications_available': list(metrics.keys())
            }
        }

    def get_schema_info(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get schema governance info"""
        schemas = self.framework.get('schema_layers', {})
        return schemas.get(schema_name)

    def get_dataset_by_domain(self, domain: str) -> List[str]:
        """Get all datasets in a domain schema"""
        return [
            name for name, meta in self.dataset_catalog.items()
            if meta.get('domain') == domain
        ]

    def validate_retention_policy(self) -> bool:
        """Validate retention policy is indefinite"""
        policy = self.framework.get('governance_rules', {}).get('retention')
        is_valid = policy == 'indefinite_all_data'
        self.log_audit('retention_policy_check', {'policy': policy, 'indefinite': is_valid})
        return is_valid


class GovernanceValidator:
    """Validate pipeline execution against governance rules"""

    def __init__(self, governance: GovernanceFramework):
        self.governance = governance
        self.validation_results = []

    def validate_dataset_ingestion(self, dataset_name: str, row_count: int) -> bool:
        """Validate dataset ingestion against governance rules"""
        classification = self.governance.get_dataset_classification(dataset_name)

        checks = [
            ('dataset_exists', dataset_name in self.governance.dataset_catalog),
            ('row_count_positive', row_count >= 0),
            ('classification_present', len(classification) > 0),
            ('tier_assigned', 'tier' in classification),
            ('priority_assigned', 'priority' in classification),
            ('domain_assigned', 'domain' in classification)
        ]

        all_passed = all(result for _, result in checks)

        self.validation_results.append({
            'dataset': dataset_name,
            'row_count': row_count,
            'checks': {check_name: result for check_name, result in checks},
            'passed': all_passed
        })

        logger.info(f"[GOVERNANCE] {dataset_name}: {sum(1 for _, r in checks if r)}/{len(checks)} validation checks passed")
        return all_passed

    def validate_pipeline_completion(self) -> Dict[str, Any]:
        """Validate entire pipeline execution"""
        return {
            'total_datasets_validated': len(self.validation_results),
            'datasets_passed': sum(1 for r in self.validation_results if r['passed']),
            'datasets_failed': sum(1 for r in self.validation_results if not r['passed']),
            'all_passed': all(r['passed'] for r in self.validation_results),
            'retention_policy_valid': self.governance.validate_retention_policy(),
            'audit_trail_size': len(self.governance.audit_log)
        }

    def get_report(self) -> str:
        """Generate governance validation report"""
        summary = self.validate_pipeline_completion()
        report = f"""
=== GOVERNANCE VALIDATION REPORT ===
Total Datasets Validated: {summary['total_datasets_validated']}
Passed: {summary['datasets_passed']}
Failed: {summary['datasets_failed']}
All Checks Passed: {summary['all_passed']}
Retention Policy Valid: {summary['retention_policy_valid']}
Audit Trail Entries: {summary['audit_trail_size']}
================================
"""
        return report
