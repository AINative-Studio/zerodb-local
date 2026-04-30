"""
Sync Executor - Executes sync plans with progress tracking and rollback support
"""
from typing import Dict, List, Any, Optional, Callable
import requests
import time
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
        self.last_sync_id: Optional[str] = None

    def execute_plan(
        self,
        plan: SyncPlan,
        project_id: str,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute a sync plan via API

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

        try:
            # First, generate a plan via API to get plan_id
            console.print("[cyan]Generating sync plan via API...[/cyan]")
            plan_response = self._generate_api_plan(project_id, plan.direction)
            plan_id = plan_response.get('plan_id')

            if not plan_id:
                raise SyncExecutionError("Failed to generate sync plan: No plan_id returned")

            # Execute the plan via API
            console.print(f"[cyan]Executing sync plan {plan_id}...[/cyan]")

            headers = {}
            if self.cloud_api_key:
                headers['Authorization'] = f'Bearer {self.cloud_api_key}'

            response = requests.post(
                f"{self.local_api_url}/v1/projects/{project_id}/sync/execute",
                json={
                    "plan_id": plan_id,
                    "approved": True,
                    "conflict_resolutions": {}
                },
                headers=headers,
                timeout=300
            )
            response.raise_for_status()

            result = response.json()
            sync_id = result.get('sync_id')

            # Store sync_id for potential rollback
            self.last_sync_id = sync_id

            # If sync_id is returned and not in dry_run, poll for status
            if sync_id and not dry_run:
                console.print(f"[cyan]Sync started with ID: {sync_id}[/cyan]")
                console.print("[cyan]Polling for status updates...[/cyan]")

                with Progress() as progress:
                    task = progress.add_task(
                        "[cyan]Syncing...",
                        total=100
                    )

                    # Poll until complete
                    final_status = self._poll_sync_status(
                        project_id,
                        sync_id,
                        progress,
                        task
                    )

                    # Update result with any final status info if available
                    if final_status and final_status.get("state") != "interrupted":
                        # Keep the original result but note polling completed
                        console.print("[green]Status polling completed[/green]")

            # Show summary based on API response
            total_steps = result.get('total_steps', 0)
            successful = result.get('successful_steps', 0)
            failed = result.get('failed_steps', 0)

            if progress_callback and total_steps > 0:
                for i in range(successful):
                    progress_callback(f"Step {i+1}/{total_steps}", i+1, total_steps)

            # Transform API response to CLI format
            return {
                'status': 'success' if result.get('status') == 'completed' else result.get('status', 'failed'),
                'total_operations': result.get('records_synced', 0),
                'successful': successful,
                'failed': failed,
                'errors': result.get('errors', []),
                'sync_id': result.get('sync_id'),
                'duration_seconds': result.get('duration_seconds'),
                'bytes_transferred': result.get('bytes_transferred', 0)
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Sync execution failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get('detail', str(e))
                    error_msg = f"Sync execution failed: {error_detail}"
                except:
                    pass
            raise SyncExecutionError(error_msg)
        except Exception as e:
            raise SyncExecutionError(f"Unexpected error during sync: {str(e)}")

    def _generate_api_plan(self, project_id: str, direction: str) -> Dict[str, Any]:
        """
        Generate sync plan via API

        Args:
            project_id: Project ID
            direction: Sync direction (push/pull/bidirectional)

        Returns:
            API plan response

        Raises:
            SyncExecutionError: If plan generation fails
        """
        headers = {}
        if self.cloud_api_key:
            headers['Authorization'] = f'Bearer {self.cloud_api_key}'

        try:
            response = requests.post(
                f"{self.local_api_url}/v1/projects/{project_id}/sync/plan",
                json={
                    "direction": direction,
                    "entity_types": None,  # Sync all types
                    "conflict_strategy": "newest_wins",
                    "include_schema": True
                },
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to generate sync plan: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get('detail', str(e))
                    error_msg = f"Failed to generate sync plan: {error_detail}"
                except:
                    pass
            raise SyncExecutionError(error_msg)

    def _poll_sync_status(
        self,
        project_id: str,
        sync_id: str,
        progress: Progress,
        task_id: TaskID
    ) -> Dict[str, Any]:
        """
        Poll sync status until complete

        Args:
            project_id: Project UUID
            sync_id: Sync operation UUID
            progress: Rich progress bar instance
            task_id: Progress task ID

        Returns:
            Final sync status
        """
        poll_interval = 2  # Poll every 2 seconds
        last_percentage = 0

        while True:
            try:
                headers = {}
                if self.cloud_api_key:
                    headers['Authorization'] = f'Bearer {self.cloud_api_key}'

                response = requests.get(
                    f"{self.local_api_url}/v1/projects/{project_id}/sync/status",
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                status = response.json()

                # Calculate progress based on available data
                # Since the general status endpoint may not have detailed progress,
                # we'll use a simple completed/total calculation
                if status.get("sync_in_progress"):
                    # Sync still running - update progress incrementally
                    last_percentage = min(last_percentage + 5, 95)  # Cap at 95% until complete
                    progress.update(
                        task_id,
                        completed=last_percentage,
                        description=f"[cyan]Syncing... ({last_percentage}%)[/cyan]"
                    )
                else:
                    # Sync completed
                    progress.update(
                        task_id,
                        completed=100,
                        description="[green]Sync complete[/green]"
                    )
                    return status

                time.sleep(poll_interval)

            except requests.exceptions.RequestException as e:
                console.print(f"[yellow]Warning: Status polling failed: {str(e)}[/yellow]")
                # Continue without status updates - don't fail the sync
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                console.print("\n[yellow]Polling interrupted by user[/yellow]")
                return {"state": "interrupted"}

    def rollback(self, sync_id: Optional[str] = None, project_id: Optional[str] = None):
        """
        Rollback sync via API

        Args:
            sync_id: Sync ID to rollback (uses last sync if not provided)
            project_id: Project ID (required)

        Raises:
            SyncExecutionError: If rollback fails
        """
        # Use provided sync_id or last executed sync
        rollback_sync_id = sync_id or getattr(self, 'last_sync_id', None)

        if not rollback_sync_id:
            console.print("[yellow]No sync to rollback[/yellow]")
            return

        if not project_id:
            raise SyncExecutionError("project_id required for rollback")

        try:
            console.print(f"[yellow]Rolling back sync {rollback_sync_id}...[/yellow]")

            headers = {}
            if self.cloud_api_key:
                headers['Authorization'] = f'Bearer {self.cloud_api_key}'

            response = requests.post(
                f"{self.local_api_url}/v1/projects/{project_id}/sync/rollback/{rollback_sync_id}",
                headers=headers,
                timeout=300
            )
            response.raise_for_status()

            result = response.json()

            if result.get('success'):
                console.print(f"[green]✓[/green] Rollback successful")
                console.print(f"[green]Restored snapshot: {result.get('snapshot_id')}[/green]")
            else:
                errors = result.get('errors', [])
                console.print(f"[red]✗[/red] Rollback failed: {', '.join(errors)}")
                raise SyncExecutionError(f"Rollback failed: {', '.join(errors)}")

        except requests.exceptions.RequestException as e:
            error_msg = f"Rollback failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get('detail', str(e))
                    error_msg = f"Rollback failed: {error_detail}"
                except:
                    pass
            console.print(f"[red]{error_msg}[/red]")
            raise SyncExecutionError(error_msg)

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
