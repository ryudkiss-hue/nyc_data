"""
Dynamic Value Injection System for Reports

Replaces {placeholder} markers in hardcoded templates with actual values from MotherDuck.
No narrative structures are built here - only value substitution.
"""

import re
from datetime import date, datetime
from typing import Any


class ValueInjectionError(Exception):
    """Raised when value injection fails."""
    pass

class ValueInjector:
    """Injects dynamic values into hardcoded narrative templates."""

    def __init__(self, values_dict: dict[str, Any]):
        """
        Initialize with a dictionary of values to inject.

        Args:
            values_dict: Dictionary mapping placeholder names to values
                Example: {
                    'morans_i_value': 0.342,
                    'borough': 'MANHATTAN',
                    'location_count': 5823,
                    ...
                }
        """
        self.values = self._normalize_values(values_dict)
        self._validate_values()

    def _normalize_values(self, values: dict[str, Any]) -> dict[str, str]:
        """Normalize all values to strings for template injection."""
        normalized = {}

        for key, value in values.items():
            if value is None:
                normalized[key] = 'N/A'
            elif isinstance(value, bool):
                normalized[key] = 'Yes' if value else 'No'
            elif isinstance(value, float):
                # Store float with reasonable precision (handled per-context in templates)
                normalized[key] = value
            elif isinstance(value, int):
                normalized[key] = value
            elif isinstance(value, (date, datetime)):
                normalized[key] = value.isoformat()
            elif isinstance(value, (list, tuple)):
                # Convert list to comma-separated string
                normalized[key] = ', '.join(str(v) for v in value)
            else:
                normalized[key] = str(value)

        return normalized

    def _validate_values(self):
        """Validate that all required keys are present (basic check)."""
        if not self.values:
            raise ValueInjectionError("No values provided for injection")

    def inject(self, template: str) -> str:
        """
        Inject values into template, replacing {placeholder} with actual values.

        Args:
            template: Template string with {placeholder} markers

        Returns:
            String with all placeholders replaced

        Raises:
            ValueInjectionError: If placeholder not found in values dictionary
        """
        result = template

        # Find all placeholders
        placeholders = re.findall(r'\{([^}]+)\}', template)

        for placeholder in placeholders:
            # Extract format specifier if present (e.g., "value:.2f")
            parts = placeholder.split(':')
            key = parts[0].strip()

            if key not in self.values:
                raise ValueInjectionError(
                    f"Placeholder '{key}' not found in values dictionary. "
                    f"Available keys: {list(self.values.keys())}"
                )

            value = self.values[key]

            # Apply format specifier if present
            if len(parts) > 1:
                format_spec = parts[1].strip()
                try:
                    formatted_value = f"{value:{format_spec}}"
                except (ValueError, TypeError) as e:
                    raise ValueInjectionError(
                        f"Cannot format value '{value}' with spec '{format_spec}': {e}"
                    )
            else:
                formatted_value = str(value)

            # Replace placeholder with formatted value
            result = result.replace('{' + placeholder + '}', formatted_value)

        return result

    def inject_formatted_list(self, template: str, list_key: str, item_template: str) -> str:
        """
        Inject a formatted list into a template.

        Example:
            template = "Items:\n{items_list}"
            item_template = "  - {item_value} ({item_label})"
            inject_formatted_list(template, "items_list", item_template)
            → "Items:\n  - Item 1 (Label 1)\n  - Item 2 (Label 2)"

        Args:
            template: Main template with {list_key} placeholder
            list_key: The placeholder key to replace
            item_template: Template for each item in the list

        Returns:
            Template with list placeholder replaced
        """
        if list_key not in self.values:
            raise ValueInjectionError(f"List key '{list_key}' not found in values")

        items = self.values[list_key]
        if not isinstance(items, (list, tuple)):
            raise ValueInjectionError(f"Value for '{list_key}' must be list or tuple")

        formatted_items = []
        for item in items:
            if isinstance(item, dict):
                item_str = self.inject(item_template)
                # Re-inject with item values
                item_injector = ValueInjector(item)
                item_str = item_injector.inject(item_str)
                formatted_items.append(item_str)
            else:
                # Simple string item
                item_injector = ValueInjector({'item': item})
                formatted_items.append(item_injector.inject(item_template))

        formatted_list = '\n'.join(formatted_items)
        return template.replace('{' + list_key + '}', formatted_list)

    def get_value(self, key: str, default: Any = None) -> Any:
        """Safely retrieve a value without injection."""
        return self.values.get(key, default)

def create_injector(data_dict: dict[str, Any]) -> ValueInjector:
    """Factory function to create a ValueInjector instance."""
    return ValueInjector(data_dict)

def inject_into_template(template: str, values: dict[str, Any]) -> str:
    """
    One-shot template injection function.

    Args:
        template: Template string with {placeholder} markers
        values: Dictionary of values to inject

    Returns:
        Template with all placeholders replaced
    """
    injector = ValueInjector(values)
    return injector.inject(template)
