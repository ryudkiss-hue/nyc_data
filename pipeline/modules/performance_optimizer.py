"""
Performance Optimizer Module
Query optimization, materialization strategies, and index recommendations.
"""

import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """
    Optimizes pipeline performance through:
    - Query plan analysis
    - Materialization recommendations
    - Partitioning strategies
    - Caching policies
    """

    def __init__(self, bridge):
        """Initialize performance optimizer."""
        self.bridge = bridge

    def analyze_table_statistics(self, schema: str, table: str) -> Dict:
        """Analyze table statistics for optimization."""
        try:
            # Get row count
            row_count_query = f"SELECT COUNT(*) as cnt FROM {schema}.{table}"
            result = self.bridge.query(row_count_query)
            row_count = result[0]['cnt'] if result else 0

            # Get column count
            col_count_query = f"""
                SELECT COUNT(*) as cnt FROM information_schema.columns
                WHERE table_schema = '{schema}' AND table_name = '{table}'
            """
            result = self.bridge.query(col_count_query)
            col_count = result[0]['cnt'] if result else 0

            stats = {
                'schema': schema,
                'table': table,
                'row_count': row_count,
                'column_count': col_count,
                'estimated_size_mb': (row_count * col_count * 8) / (1024 * 1024),
                'optimization_priority': 'high' if row_count > 1000000 else 'medium'
            }

            logger.info(f"Table stats for {schema}.{table}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to analyze {schema}.{table}: {str(e)}")
            return {}

    def get_materialization_recommendations(self, views: List[str]) -> List[Dict]:
        """
        Recommend which views to materialize based on complexity.
        """
        recommendations = []

        for view in views:
            rec = {
                'view': view,
                'recommendation': 'MATERIALIZE' if 'join' in view.lower() or 'group' in view.lower() else 'KEEP_AS_VIEW',
                'reason': 'Complex query with joins/aggregations' if 'join' in view.lower() else 'Simple view',
                'estimated_refresh_frequency': '6 hours' if 'materialize' in view else 'on-demand'
            }
            recommendations.append(rec)
            logger.info(f"Materialization recommendation: {rec}")

        return recommendations

    def get_partitioning_strategy(self, table: str) -> Dict:
        """
        Recommend partitioning strategy for large tables.
        """
        strategy = {
            'table': table,
            'recommended_partition_column': 'borough' if 'inspection' in table.lower() else 'date',
            'partition_type': 'list' if 'borough' in table.lower() else 'range',
            'estimated_partitions': 5 if 'borough' in table.lower() else 12,
            'benefit': 'Improved query performance on filtered queries',
            'estimated_speedup': '2-10x'
        }

        logger.info(f"Partitioning strategy for {table}: {strategy}")
        return strategy

    def get_index_recommendations(self, schema: str, table: str) -> List[Dict]:
        """
        Recommend indexes for frequently queried columns.
        Note: DuckDB has limited index support, recommend materialized views instead.
        """
        recommendations = []

        # Recommend column-specific optimizations
        common_filters = {
            'inspection': ['borough', 'inspection_date'],
            'violations': ['inspection_id', 'remediation_status'],
            'ramp_progress': ['ramp_id', 'completion_status'],
            'street_permits': ['permit_id', 'status', 'borough']
        }

        table_filters = common_filters.get(table, [])

        for col in table_filters:
            rec = {
                'column': col,
                'type': 'MATERIALIZED_VIEW' if col in ['borough', 'inspection_date'] else 'PROJECTION',
                'benefit': 'Speeds up filtered queries',
                'implementation': f'CREATE VIEW {table}_{col} AS SELECT DISTINCT {col}'
            }
            recommendations.append(rec)

        logger.info(f"Index recommendations for {schema}.{table}: {len(recommendations)} recommendations")
        return recommendations

    def generate_performance_report(self, tables: List[str]) -> Dict:
        """Generate comprehensive performance report."""
        report = {
            'summary': {
                'tables_analyzed': len(tables),
                'optimization_score': 0.0,
                'potential_improvement': 'Medium'
            },
            'tables': [],
            'recommendations': []
        }

        for table in tables:
            stats = self.analyze_table_statistics('staging', table)
            if stats:
                report['tables'].append(stats)

        # Calculate optimization score
        total_rows = sum(t.get('row_count', 0) for t in report['tables'])
        large_tables = sum(1 for t in report['tables'] if t.get('row_count', 0) > 100000)

        report['summary']['optimization_score'] = round(min(100, 50 + (large_tables * 10)), 2)
        report['summary']['potential_improvement'] = 'High' if large_tables >= 3 else 'Medium'

        logger.info(f"Performance report: {report['summary']}")
        return report


class QueryOptimizer:
    """Optimizes individual queries."""

    @staticmethod
    def recommend_aggregation_materialization(query: str) -> bool:
        """Check if query would benefit from materialization."""
        expensive_keywords = ['GROUP BY', 'HAVING', 'JOIN']
        return any(keyword in query.upper() for keyword in expensive_keywords)

    @staticmethod
    def suggest_column_pruning(table: str, columns_used: List[str]) -> Dict:
        """Suggest which columns to select for efficiency."""
        return {
            'table': table,
            'columns_to_select': columns_used,
            'benefit': 'Reduces data transfer and memory usage',
            'estimated_speedup': '1-5x depending on column count'
        }

    @staticmethod
    def analyze_join_order(joins: List[Tuple[str, str]]) -> Dict:
        """Analyze join order for optimization."""
        return {
            'joins': len(joins),
            'recommended_order': 'Start with smallest table',
            'benefit': 'Reduces intermediate result set sizes'
        }

