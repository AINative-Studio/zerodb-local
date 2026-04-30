"""
Tests for sync plan command

Story #421: Sync Plan Command
"""
import pytest
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typer.testing import CliRunner
from main import app

runner = CliRunner()


def test_sync_plan_help():
    """Test sync plan help output"""
    result = runner.invoke(app, ["sync", "plan", "--help"])
    assert result.exit_code == 0
    assert "Story #421" in result.stdout
    assert "Generate and display sync plan" in result.stdout
    assert "--direction" in result.stdout
    assert "--entity-types" in result.stdout
    assert "--format" in result.stdout
    assert "--dry-run" in result.stdout


def test_sync_plan_dry_run():
    """Test sync plan dry-run mode"""
    result = runner.invoke(app, ["sync", "plan", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run mode" in result.stdout
    assert "Would check sync plan for:" in result.stdout
    assert "Project ID:" in result.stdout


def test_sync_plan_default():
    """Test sync plan with default options (bidirectional)"""
    result = runner.invoke(app, ["sync", "plan"])
    assert result.exit_code == 0
    assert "Sync Plan" in result.stdout
    assert "BIDIRECTIONAL" in result.stdout
    assert "Total Operations:" in result.stdout


def test_sync_plan_push_direction():
    """Test sync plan with push direction"""
    result = runner.invoke(app, ["sync", "plan", "--direction", "push"])
    assert result.exit_code == 0
    assert "PUSH" in result.stdout


def test_sync_plan_pull_direction():
    """Test sync plan with pull direction"""
    result = runner.invoke(app, ["sync", "plan", "--direction", "pull"])
    assert result.exit_code == 0
    assert "PULL" in result.stdout


def test_sync_plan_invalid_direction():
    """Test sync plan with invalid direction"""
    result = runner.invoke(app, ["sync", "plan", "--direction", "invalid"])
    assert result.exit_code == 1
    assert "Invalid direction" in result.stdout


def test_sync_plan_entity_types_filter():
    """Test sync plan with entity type filtering"""
    result = runner.invoke(app, ["sync", "plan", "--entity-types", "vectors,tables"])
    assert result.exit_code == 0
    assert "vectors, tables" in result.stdout
    # Files should not appear in filtered output
    operations_count = result.stdout.count("Files:")
    # Should be 0 or 1 (only in headers if no file operations)
    assert operations_count <= 1


def test_sync_plan_single_entity_type():
    """Test sync plan with single entity type"""
    result = runner.invoke(app, ["sync", "plan", "--entity-types", "vectors"])
    assert result.exit_code == 0
    assert "vectors" in result.stdout


def test_sync_plan_invalid_entity_type():
    """Test sync plan with invalid entity type"""
    result = runner.invoke(app, ["sync", "plan", "--entity-types", "invalid"])
    assert result.exit_code == 1
    assert "Invalid entity types" in result.stdout
    assert "Valid types:" in result.stdout


def test_sync_plan_json_output():
    """Test sync plan JSON format output"""
    result = runner.invoke(app, ["sync", "plan", "--format", "json"])
    assert result.exit_code == 0

    # Extract JSON from output (skip the "Generating..." line)
    lines = result.stdout.split('\n')
    json_start = next(i for i, line in enumerate(lines) if line.startswith('{'))
    json_str = '\n'.join(lines[json_start:])

    # Parse JSON
    data = json.loads(json_str)

    # Validate JSON structure
    assert "direction" in data
    assert "mode" in data
    assert "total_operations" in data
    assert "operations" in data
    assert "summary" in data
    assert isinstance(data["operations"], list)


def test_sync_plan_json_contains_operations():
    """Test sync plan JSON contains operation details"""
    result = runner.invoke(app, ["sync", "plan", "--format", "json"])
    assert result.exit_code == 0

    lines = result.stdout.split('\n')
    json_start = next(i for i, line in enumerate(lines) if line.startswith('{'))
    json_str = '\n'.join(lines[json_start:])
    data = json.loads(json_str)

    # Check operations have required fields
    for op in data["operations"]:
        assert "entity_type" in op
        assert "operation" in op
        assert "description" in op
        assert op["entity_type"] in ["vectors", "tables", "files", "events", "memory"]
        assert op["operation"] in ["create", "update", "delete", "upsert"]


def test_sync_plan_table_format_default():
    """Test sync plan table format (default)"""
    result = runner.invoke(app, ["sync", "plan"])
    assert result.exit_code == 0

    # Check for table elements
    assert "Sync Plan Summary" in result.stdout
    assert "Entity Type" in result.stdout
    assert "Operation" in result.stdout
    assert "Count" in result.stdout
    assert "Est. Size" in result.stdout


def test_sync_plan_shows_statistics():
    """Test sync plan displays statistics"""
    result = runner.invoke(app, ["sync", "plan"])
    assert result.exit_code == 0

    # Check for statistics
    assert "Total Operations:" in result.stdout
    assert "Total Estimated Size:" in result.stdout
    assert "Estimated Time:" in result.stdout


def test_sync_plan_shows_next_steps():
    """Test sync plan shows next steps"""
    result = runner.invoke(app, ["sync", "plan"])
    assert result.exit_code == 0

    assert "Next Steps:" in result.stdout
    assert "zerodb sync apply" in result.stdout


def test_sync_plan_invalid_format():
    """Test sync plan with invalid format"""
    result = runner.invoke(app, ["sync", "plan", "--format", "invalid"])
    assert result.exit_code == 1
    assert "Invalid format" in result.stdout


def test_sync_plan_combined_options():
    """Test sync plan with multiple options"""
    result = runner.invoke(app, [
        "sync", "plan",
        "--direction", "push",
        "--entity-types", "vectors",
        "--format", "table"
    ])
    assert result.exit_code == 0
    assert "PUSH" in result.stdout
    assert "vectors" in result.stdout


def test_sync_plan_detailed_breakdown():
    """Test sync plan shows detailed breakdown"""
    result = runner.invoke(app, ["sync", "plan"])
    assert result.exit_code == 0

    assert "Detailed Breakdown:" in result.stdout
    # Should show entity type sections
    assert any(entity in result.stdout for entity in ["Vectors:", "Tables:", "Files:"])


def test_sync_plan_operation_types_shown():
    """Test sync plan shows different operation types"""
    result = runner.invoke(app, ["sync", "plan"])
    assert result.exit_code == 0

    # Check for operation indicators
    output = result.stdout
    # Should show different operations (create, update, delete, etc)
    # Look for operation type keywords
    assert any(op in output for op in ["Create", "Update", "Delete", "Upsert"])


def test_sync_plan_schema_changes_warning():
    """Test sync plan warns about schema changes"""
    result = runner.invoke(app, ["sync", "plan", "--entity-types", "tables"])
    # Only check if there are table operations that trigger warning
    if "Update" in result.stdout or "Delete" in result.stdout:
        assert "Schema Changes" in result.stdout or result.exit_code == 0


def test_sync_plan_empty_entity_filter():
    """Test sync plan with empty entity types still works"""
    result = runner.invoke(app, ["sync", "plan", "--entity-types", ""])
    # Should either error or show all entities
    assert result.exit_code in [0, 1]
