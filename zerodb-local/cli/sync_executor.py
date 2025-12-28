"""
Sync Executor - Executes sync plans with progress tracking and rollback support
"""
from typing import Dict, List, Any, Optional, Callable
import requests
from rich.progress import Progress, TaskID
from rich.console import Console

try:
    from .sync_planner import SyncPlan, SyncOperation
except ImportError:
    from sync_planner import SyncPlan, SyncOperation

console = Console()


class SyncExecutionError(Exception):
    """Raised when sync execution fails"""
    pass


class SyncExecutor:
    """Executes sync plans and manages sync state"""

    def __init__(
        self,
        local_api_url: str = "http://localhost:8000",
        cloud_api_url: str = "https://api.ainative.studio",
        cloud_api_key: Optional[str] = None
    ):
        self.local_api_url = local_api_url
        self.cloud_api_url = cloud_api_url
        self.cloud_api_key = cloud_api_key
        self.executed_operations: List[SyncOperation] = []

    def execute_plan(
        self,
        plan: SyncPlan,
        project_id: str,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute a sync plan

        Args:
            plan: SyncPlan to execute
            project_id: Project ID
            dry_run: If True, show what would be done without executing
            progress_callback: Optional callback for progress updates

        Returns:
            Execution result with statistics

        Raises:
            SyncExecutionError: If execution fails
        """
        if dry_run:
            return self._dry_run(plan)

        results = {
            'status': 'success',
            'total_operations': plan.total_operations,
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        try:
            with Progress() as progress:
                task = progress.add_task(
                    f"[cyan]Syncing {plan.direction}...",
                    total=plan.total_operations
                )

                for idx, operation in enumerate(plan.operations):
                    try:
                        # Execute the operation
                        self._execute_operation(operation, project_id)
                        self.executed_operations.append(operation)
                        results['successful'] += 1

                        # Update progress
                        progress.update(task, advance=1)
                        if progress_callback:
                            progress_callback(operation.description, idx + 1, plan.total_operations)

                    except Exception as e:
                        results['failed'] += 1
                        results['errors'].append({
                            'operation': operation.description,
                            'error': str(e)
                        })
                        console.print(f"[red]✗[/red] {operation.description}: {str(e)}")

                        # Rollback on error
                        console.print("[yellow]Rolling back changes...[/yellow]")
                        self.rollback()
                        raise SyncExecutionError(f"Sync failed: {str(e)}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Sync interrupted by user. Rolling back...[/yellow]")
            self.rollback()
            results['status'] = 'cancelled'

        return results

    def _execute_operation(self, operation: SyncOperation, project_id: str):
        """
        Execute a single sync operation

        Args:
            operation: SyncOperation to execute
            project_id: Project ID

        Raises:
            Exception: If operation fails
        """
        if operation.entity_type == 'table':
            self._sync_table(operation, project_id)
        elif operation.entity_type == 'vector':
            self._sync_vector(operation, project_id)
        elif operation.entity_type == 'file':
            self._sync_file(operation, project_id)
        elif operation.entity_type == 'event':
            self._sync_event(operation, project_id)
        elif operation.entity_type == 'memory':
            self._sync_memory(operation, project_id)
        else:
            raise ValueError(f"Unknown entity type: {operation.entity_type}")

    def _sync_table(self, operation: SyncOperation, project_id: str):
        """Sync a table operation"""
        # TODO: Implement actual table sync
        pass

    def _sync_vector(self, operation: SyncOperation, project_id: str):
        """Sync a vector operation"""
        # TODO: Implement actual vector sync
        pass

    def _sync_file(self, operation: SyncOperation, project_id: str):
        """Sync a file operation"""
        # TODO: Implement actual file sync
        pass

    def _sync_event(self, operation: SyncOperation, project_id: str):
        """Sync an event operation"""
        # TODO: Implement actual event sync
        pass

    def _sync_memory(self, operation: SyncOperation, project_id: str):
        """Sync a memory operation"""
        # TODO: Implement actual memory sync
        pass

    def rollback(self):
        """
        Rollback all executed operations

        This reverses all operations that were successfully executed
        before the failure.
        """
        if not self.executed_operations:
            return

        console.print(f"[yellow]Rolling back {len(self.executed_operations)} operations...[/yellow]")

        # Reverse operations in reverse order
        for operation in reversed(self.executed_operations):
            try:
                self._rollback_operation(operation)
                console.print(f"[green]✓[/green] Rolled back: {operation.description}")
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to rollback {operation.description}: {str(e)}")

        self.executed_operations.clear()
        console.print("[yellow]Rollback complete[/yellow]")

    def _rollback_operation(self, operation: SyncOperation):
        """
        Rollback a single operation

        Args:
            operation: Operation to rollback
        """
        # TODO: Implement actual rollback logic
        # This would reverse the operation (e.g., delete → create, create → delete)
        pass

    def _dry_run(self, plan: SyncPlan) -> Dict[str, Any]:
        """
        Show what would be done without executing

        Args:
            plan: SyncPlan to preview

        Returns:
            Summary of what would be done
        """
        console.print("\n[bold cyan]🔍 Dry Run - No changes will be made[/bold cyan]\n")

        summary = plan.get_summary()
        console.print("[bold]Operations:[/bold]")
        console.print(f"  Total: {summary['total']}")
        console.print(f"  Create: {summary.get('create', 0)}")
        console.print(f"  Update: {summary.get('update', 0)}")
        console.print(f"  Delete: {summary.get('delete', 0)}")
        console.print(f"  Upsert: {summary.get('upsert', 0)}")

        console.print("\n[bold]Operations Detail:[/bold]")
        for op in plan.operations:
            icon = "+" if op.operation == "create" else "~" if op.operation == "update" else "-" if op.operation == "delete" else "↑"
            console.print(f"  {icon} {op.description}")

        return {
            'status': 'dry_run',
            'would_execute': plan.total_operations,
            'summary': summary
        }

    def push_to_cloud(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push data to cloud

        Args:
            project_id: Project ID
            data: Data to push

        Returns:
            API response

        Raises:
            SyncExecutionError: If push fails
        """
        if not self.cloud_api_key:
            raise SyncExecutionError("Cloud API key not configured")

        try:
            response = requests.post(
                f"{self.cloud_api_url}/v1/projects/{project_id}/database/import",
                headers={
                    'Authorization': f'Bearer {self.cloud_api_key}',
                    'Content-Type': 'application/json'
                },
                json=data,
                timeout=300  # 5 minutes for large uploads
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise SyncExecutionError(f"Failed to push to cloud: {str(e)}")

    def pull_from_cloud(self, project_id: str) -> Dict[str, Any]:
        """
        Pull data from cloud

        Args:
            project_id: Project ID

        Returns:
            Cloud data

        Raises:
            SyncExecutionError: If pull fails
        """
        if not self.cloud_api_key:
            raise SyncExecutionError("Cloud API key not configured")

        try:
            # Trigger export
            export_response = requests.post(
                f"{self.cloud_api_url}/v1/projects/{project_id}/database/export",
                headers={
                    'Authorization': f'Bearer {self.cloud_api_key}',
                    'Content-Type': 'application/json'
                },
                json={'format': 'json'},
                timeout=60
            )
            export_response.raise_for_status()
            export_id = export_response.json()['export_id']

            # Poll for completion (simplified - real implementation would poll)
            # TODO: Add polling logic here

            # Download export
            download_response = requests.get(
                f"{self.cloud_api_url}/v1/projects/{project_id}/database/exports/{export_id}/download",
                headers={'Authorization': f'Bearer {self.cloud_api_key}'},
                timeout=300
            )
            download_response.raise_for_status()
            return download_response.json()

        except requests.exceptions.RequestException as e:
            raise SyncExecutionError(f"Failed to pull from cloud: {str(e)}")
