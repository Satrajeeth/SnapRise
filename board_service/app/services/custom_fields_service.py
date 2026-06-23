from typing import Any, Dict, List
from datetime import datetime

class CustomFieldsService:
    @staticmethod
    def validate_custom_fields(fields_data: Dict[str, Any], schema: List[Dict[str, Any]]) -> List[str]:
        """
        Validate fields_data against the custom_fields_schema defined on the Board.
        Schema format: [{'name': 'Priority', 'type': 'string', 'required': True, 'options': ['High', 'Low']}]
        Returns a list of error strings. Empty list means valid.
        """
        errors = []
        schema_dict = {field["name"]: field for field in schema}

        for field_name, value in fields_data.items():
            if field_name not in schema_dict:
                errors.append(f"Field '{field_name}' is not defined in the board schema.")
                continue
                
            field_def = schema_dict[field_name]
            field_type = field_def.get("type", "string")
            
            if field_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{field_name}' must be a string.")
            elif field_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field '{field_name}' must be a number.")
            elif field_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field '{field_name}' must be a boolean.")
            elif field_type == "date":
                try:
                    datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    errors.append(f"Field '{field_name}' must be a valid ISO format date string.")
            
            options = field_def.get("options")
            if options and value not in options:
                errors.append(f"Field '{field_name}' must be one of {options}.")

        for field_name, field_def in schema_dict.items():
            if field_def.get("required", False) and field_name not in fields_data:
                errors.append(f"Required field '{field_name}' is missing.")

        return errors