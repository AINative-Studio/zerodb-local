"""
Schema Commands - Generate Pydantic models from ZeroDB table schemas

AX-016: Pydantic schema auto-sync between ZeroDB tables and Python models.

Usage:
    zerodb schema sync --table my_table --output models.py
    zerodb schema sync --table my_table  # prints to stdout
    zerodb schema list                   # list all tables with field counts
"""
import ast
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import typer
import httpx
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ..config import load_config, get_project_id
except ImportError:
    from config import load_config, get_project_id

app = typer.Typer(help="Generate Pydantic models from ZeroDB table schemas")
console = Console()

# ZeroDB type → Python type mapping
ZERODB_TYPE_MAP = {
    "string": "str",
    "text": "str",
    "varchar": "str",
    "char": "str",
    "integer": "int",
    "int": "int",
    "bigint": "int",
    "smallint": "int",
    "float": "float",
    "double": "float",
    "decimal": "float",
    "number": "float",
    "numeric": "float",
    "boolean": "bool",
    "bool": "bool",
    "date": "date",
    "datetime": "datetime",
    "timestamp": "datetime",
    "timestamptz": "datetime",
    "json": "Dict[str, Any]",
    "jsonb": "Dict[str, Any]",
    "object": "Dict[str, Any]",
    "array": "List[Any]",
    "list": "List[Any]",
    "uuid": "str",
    "binary": "bytes",
    "bytea": "bytes",
}

# Types that need imports
IMPORT_TYPES = {
    "date": "from datetime import date",
    "datetime": "from datetime import datetime",
    "Dict[str, Any]": "from typing import Dict, Any",
    "List[Any]": "from typing import List, Any",
}


def _get_api_client() -> tuple:
    """Get API URL and auth headers from config."""
    config = load_config()
    api_url = os.getenv(
        "ZERODB_API_URL",
        config.get("cloud_api_url", "https://api.ainative.studio"),
    )
    api_key = os.getenv("ZERODB_API_KEY", "")
    project_id = os.getenv("ZERODB_PROJECT_ID", "") or get_project_id() or ""

    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    return api_url, headers, project_id


def _fetch_tables(api_url: str, headers: dict, project_id: str) -> List[Dict]:
    """Fetch table list from ZeroDB API."""
    url = f"{api_url}/api/v1/zerodb/projects/{project_id}/database/tables"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data if isinstance(data, list) else data.get("tables", data.get("items", []))


def _fetch_table_schema(api_url: str, headers: dict, project_id: str, table_id: str) -> Dict:
    """Fetch a single table's schema from ZeroDB API."""
    url = f"{api_url}/api/v1/zerodb/projects/{project_id}/database/tables/{table_id}"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers, params={"include_stats": "true"})
        resp.raise_for_status()
        return resp.json()


def _python_type(zerodb_type: str, nullable: bool = False) -> str:
    """Map a ZeroDB field type to a Python type string."""
    base = zerodb_type.lower().strip()
    py_type = ZERODB_TYPE_MAP.get(base, "Any")
    if nullable:
        return f"Optional[{py_type}]"
    return py_type


def _to_class_name(table_name: str) -> str:
    """Convert table_name to PascalCase class name."""
    parts = table_name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts if p)


def generate_model(table_name: str, schema_def: Dict[str, Any]) -> str:
    """Generate Pydantic BaseModel code from a table schema definition.

    Args:
        table_name: The ZeroDB table name.
        schema_def: Dict mapping field names to type info. Supports formats:
            - {"field": "string"}
            - {"field": {"type": "string", "nullable": true, "default": "x"}}
    """
    class_name = _to_class_name(table_name)
    fields = []
    extra_imports = set()
    extra_imports.add("from typing import Optional, Any")

    for field_name, field_info in schema_def.items():
        if field_name.startswith("_"):
            continue

        if isinstance(field_info, str):
            ftype = field_info
            nullable = False
            default = None
            description = None
        elif isinstance(field_info, dict):
            ftype = field_info.get("type", "any")
            nullable = field_info.get("nullable", False)
            default = field_info.get("default")
            description = field_info.get("description")
        else:
            ftype = "any"
            nullable = True
            default = None
            description = None

        py_type = _python_type(ftype, nullable)

        # Track needed imports
        base_type = py_type.replace("Optional[", "").rstrip("]")
        if base_type in IMPORT_TYPES:
            extra_imports.add(IMPORT_TYPES[base_type])

        # Build field line
        if default is not None:
            if isinstance(default, str):
                field_line = f'    {field_name}: {py_type} = "{default}"'
            else:
                field_line = f"    {field_name}: {py_type} = {default}"
        elif nullable:
            field_line = f"    {field_name}: {py_type} = None"
        else:
            field_line = f"    {field_name}: {py_type}"

        if description:
            field_line = f'{field_line}  # {description}'

        fields.append(field_line)

    if not fields:
        fields.append("    pass")

    imports = sorted(extra_imports)
    imports_block = "\n".join(imports)

    code = f'''"""Auto-generated Pydantic model for ZeroDB table: {table_name}

Generated by: zerodb schema sync --table {table_name}
Generated at: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
"""
from pydantic import BaseModel
{imports_block}


class {class_name}(BaseModel):
    """{table_name} table model."""
{chr(10).join(fields)}

    class Config:
        from_attributes = True
'''
    return code


@app.command("sync")
def schema_sync(
    table: str = typer.Option(..., "--table", "-t", help="Table name or ID to generate model for"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (prints to stdout if omitted)"),
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID (uses config default if omitted)"),
):
    """
    Generate a Pydantic model from a ZeroDB table schema.

    Fetches the table's schema definition from the API and generates
    a valid Python file with a Pydantic BaseModel class.

    Examples:
        zerodb schema sync --table users --output models.py
        zerodb schema sync --table orders
        zerodb schema sync --table events -p abc123 -o event_model.py
    """
    try:
        api_url, headers, pid = _get_api_client()
        if project_id:
            pid = project_id

        if not pid:
            console.print("[red]Error:[/red] No project ID. Set ZERODB_PROJECT_ID or use --project-id.")
            raise typer.Exit(1)

        console.print(f"[dim]Fetching schema for table '{table}'...[/dim]")
        table_data = _fetch_table_schema(api_url, headers, pid, table)

        schema_def = table_data.get("schema_definition") or table_data.get("schema", {})
        table_name = table_data.get("table_name", table)

        if not schema_def:
            console.print(f"[yellow]Warning:[/yellow] Table '{table}' has no schema definition. Generating empty model.")
            schema_def = {}

        code = generate_model(table_name, schema_def)

        # Validate generated code is syntactically correct
        try:
            ast.parse(code)
        except SyntaxError as e:
            console.print(f"[red]Error:[/red] Generated code has syntax error: {e}")
            console.print(code)
            raise typer.Exit(1)

        if output:
            Path(output).write_text(code)
            console.print(f"[green]✓[/green] Model written to [bold]{output}[/bold]")
            console.print(f"  Class: [cyan]{_to_class_name(table_name)}[/cyan]")
            console.print(f"  Fields: [cyan]{len(schema_def)}[/cyan]")
        else:
            syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
            console.print(syntax)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] Table '{table}' not found.")
        else:
            console.print(f"[red]Error:[/red] API returned {e.response.status_code}: {e.response.text[:200]}")
        raise typer.Exit(1)
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot reach ZeroDB API. Check ZERODB_API_URL and network.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def schema_list(
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List all tables with their field counts.

    Examples:
        zerodb schema list
        zerodb schema list --project-id abc123
        zerodb schema list --json
    """
    try:
        api_url, headers, pid = _get_api_client()
        if project_id:
            pid = project_id

        if not pid:
            console.print("[red]Error:[/red] No project ID. Set ZERODB_PROJECT_ID or use --project-id.")
            raise typer.Exit(1)

        tables = _fetch_tables(api_url, headers, pid)

        if json_output:
            import json
            console.print_json(json.dumps([
                {
                    "table_name": t.get("table_name", ""),
                    "fields": len(t.get("schema_definition", {}) or {}),
                    "class_name": _to_class_name(t.get("table_name", "")),
                }
                for t in tables
            ]))
            return

        tbl = Table(title=f"Tables — Project {pid[:8]}...")
        tbl.add_column("Table Name", style="cyan")
        tbl.add_column("Fields", justify="right", style="magenta")
        tbl.add_column("Pydantic Class", style="green")
        tbl.add_column("Sync Command", style="dim")

        for t in tables:
            name = t.get("table_name", "")
            schema = t.get("schema_definition") or {}
            tbl.add_row(
                name,
                str(len(schema)),
                _to_class_name(name),
                f"zerodb schema sync -t {name}",
            )

        console.print(tbl)
        console.print(f"\n[dim]Total: {len(tables)} table(s)[/dim]")

    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot reach ZeroDB API.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
