"""
Tests for zerodb schema sync — Pydantic model generation from ZeroDB table schemas.

AX-016: Tests cover the generate_model() function and type mapping.
"""
import ast
import sys
from pathlib import Path

import pytest

# Add CLI directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from commands.schema import generate_model, _python_type, _to_class_name, ZERODB_TYPE_MAP


class TestTypeMapping:
    """Scenario: ZeroDB field types map to correct Python types."""

    @pytest.mark.parametrize("zerodb_type,expected", [
        ("string", "str"),
        ("text", "str"),
        ("integer", "int"),
        ("int", "int"),
        ("bigint", "int"),
        ("float", "float"),
        ("double", "float"),
        ("number", "float"),
        ("boolean", "bool"),
        ("bool", "bool"),
        ("json", "Dict[str, Any]"),
        ("jsonb", "Dict[str, Any]"),
        ("object", "Dict[str, Any]"),
        ("array", "List[Any]"),
        ("uuid", "str"),
        ("binary", "bytes"),
        ("datetime", "datetime"),
        ("timestamp", "datetime"),
        ("date", "date"),
    ])
    def test_type_mapping(self, zerodb_type, expected):
        assert _python_type(zerodb_type) == expected

    def test_nullable_wraps_optional(self):
        assert _python_type("string", nullable=True) == "Optional[str]"
        assert _python_type("integer", nullable=True) == "Optional[int]"

    def test_unknown_type_returns_any(self):
        assert _python_type("weird_custom_type") == "Any"


class TestClassNameGeneration:
    """Scenario: Table names convert to PascalCase class names."""

    @pytest.mark.parametrize("table_name,expected", [
        ("users", "Users"),
        ("user_profiles", "UserProfiles"),
        ("api_usage_logs", "ApiUsageLogs"),
        ("order-items", "OrderItems"),
        ("a", "A"),
    ])
    def test_to_class_name(self, table_name, expected):
        assert _to_class_name(table_name) == expected


class TestGenerateModel:
    """Scenario: Full model generation from schema definitions."""

    def test_simple_schema(self):
        """Given a simple schema dict, generate valid Pydantic model."""
        schema = {
            "name": "string",
            "age": "integer",
            "email": "string",
        }
        code = generate_model("users", schema)
        ast.parse(code)  # Must be valid Python
        assert "class Users(BaseModel):" in code
        assert "name: str" in code
        assert "age: int" in code
        assert "email: str" in code

    def test_rich_schema_with_type_dicts(self):
        """Given a schema with type/nullable/default dicts, generate correct fields."""
        schema = {
            "id": {"type": "integer"},
            "title": {"type": "string"},
            "body": {"type": "text", "nullable": True},
            "status": {"type": "string", "default": "draft"},
            "tags": {"type": "array", "nullable": True},
            "metadata": {"type": "json"},
        }
        code = generate_model("blog_posts", schema)
        ast.parse(code)
        assert "class BlogPosts(BaseModel):" in code
        assert "id: int" in code
        assert "body: Optional[str] = None" in code
        assert 'status: str = "draft"' in code
        assert "tags: Optional[List[Any]] = None" in code
        assert "metadata: Dict[str, Any]" in code

    def test_empty_schema(self):
        """Given an empty schema, generate a model with pass."""
        code = generate_model("empty_table", {})
        ast.parse(code)
        assert "class EmptyTable(BaseModel):" in code
        assert "    pass" in code

    def test_generated_code_is_valid_python(self):
        """Every generated model must parse without SyntaxError."""
        schemas = [
            {"x": "string"},
            {"a": {"type": "int", "nullable": True}},
            {"data": {"type": "jsonb", "default": None, "nullable": True}},
            {"created_at": "timestamp", "updated_at": "datetime"},
        ]
        for schema in schemas:
            code = generate_model("test_table", schema)
            ast.parse(code)  # No SyntaxError = pass

    def test_includes_pydantic_import(self):
        code = generate_model("t", {"x": "string"})
        assert "from pydantic import BaseModel" in code

    def test_includes_config_from_attributes(self):
        code = generate_model("t", {"x": "string"})
        assert "from_attributes = True" in code

    def test_skips_underscore_fields(self):
        """Fields starting with _ should be skipped."""
        schema = {"name": "string", "_internal": "string", "__private": "int"}
        code = generate_model("t", schema)
        assert "name: str" in code
        assert "_internal" not in code
        assert "__private" not in code

    def test_description_as_comment(self):
        schema = {"name": {"type": "string", "description": "User full name"}}
        code = generate_model("t", schema)
        assert "# User full name" in code

    def test_datetime_imports_added(self):
        schema = {"created_at": "datetime", "birthday": "date"}
        code = generate_model("t", schema)
        assert "from datetime import datetime" in code
        assert "from datetime import date" in code

    def test_header_contains_table_name(self):
        code = generate_model("order_items", {"qty": "integer"})
        assert "table: order_items" in code


class TestGenerateModelEdgeCases:
    """Scenario: Edge cases and malformed schemas."""

    def test_field_info_is_none(self):
        schema = {"weird": None}
        code = generate_model("t", schema)
        ast.parse(code)
        assert "weird: Optional[Any] = None" in code

    def test_field_info_is_number(self):
        schema = {"weird": 42}
        code = generate_model("t", schema)
        ast.parse(code)
        assert "weird: Optional[Any] = None" in code

    def test_boolean_default(self):
        schema = {"active": {"type": "boolean", "default": True}}
        code = generate_model("t", schema)
        assert "active: bool = True" in code

    def test_numeric_default(self):
        schema = {"count": {"type": "integer", "default": 0}}
        code = generate_model("t", schema)
        assert "count: int = 0" in code
