import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class CustomFieldsService:
    @staticmethod
    def validate_custom_fields(fields: Dict[str,Any], schema: List[Dict[str,Any]]) -> List[str]:
        """
        Validate custom fields against a schema.
        Schema example: [{"name": "priority", "type": "number", "required": true}]
        """
        errors = []
        for field_def in schema:
            name = field_def.get("name")
            field_type = field_def.get("type")
            required = field_def.get("required", False)

            value = fields.get(name)

            if value is None:
                if required:
                    errors.append(f"Custom field '{name}' is required.")
                continue

            if field_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Custom field '{name}' should be a number.")
            elif field_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Custom field '{name}' should be a boolean.")
            elif field_type == "string" and not isinstance(value, str):
                errors.append(f"Custom field '{name}' should be a string.")

        return errors