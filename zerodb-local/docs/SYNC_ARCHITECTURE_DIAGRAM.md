# ZeroDB Local - Sync Architecture

## Complete Sync Infrastructure (Epic 4)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER/CLIENT APPLICATION                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   FastAPI Router      │
                    │  (5 API Endpoints)    │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│  POST /plan    │    │ POST /execute   │    │  GET /status    │
│                │    │                 │    │                 │
│ Generate sync  │    │ Execute sync    │    │ Get current     │
│ plan with      │    │ with automatic  │    │ sync state      │
│ estimates      │    │ rollback        │    │                 │
└───────┬────────┘    └────────┬────────┘    └────────┬────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │                     │
                    │  SYNC ORCHESTRATOR  │
                    │   (Story #434)      │
                    │                     │
                    │ Core Coordinator    │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
│ Sync State     │   │  CDC Service    │   │ Schema Diff     │
│ Service        │   │  (Story #430)   │   │ Service         │
│ (Story #429)   │   │                 │   │ (Story #431)    │
│                │   │ - Get changes   │   │                 │
│ - Watermarks   │   │ - Mark synced   │   │ - Compare       │
│ - Last sync    │   │ - Change log    │   │   schemas       │
│ - Strategy     │   │                 │   │ - Breaking      │
│                │   │                 │   │   changes       │
└───────┬────────┘   └────────┬────────┘   └────────┬────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   PostgreSQL DB     │
                    │                     │
                    │ - sync_state table  │
                    │ - change_log table  │
                    │ - user tables       │
                    │ - vectors metadata  │
                    └─────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                        SYNC EXECUTION FLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

PUSH SYNC (Local → Cloud):

1. PLAN PHASE
   ┌─────────────────────────────────────────────────┐
   │ Orchestrator.plan_sync(direction="push")        │
   │                                                 │
   │ ┌─────────────────────────────────────────┐   │
   │ │ 1. Get last_sync_at from SyncState      │   │
   │ │ 2. Get unsynced changes from CDC        │   │
   │ │ 3. Compare schemas (local vs cloud)     │   │
   │ │ 4. Detect conflicts                     │   │
   │ │ 5. Generate sync steps                  │   │
   │ │ 6. Calculate estimates                  │   │
   │ │ 7. Generate warnings                    │   │
   │ └─────────────────────────────────────────┘   │
   │                                                 │
   │ Returns: SyncPlan                               │
   │ {                                               │
   │   steps: [                                      │
   │     1. Schema Validation                        │
   │     2. Export Creation                          │
   │     3. Data Upload                              │
   │     4. Update Watermarks                        │
   │     5. Mark Changes Synced                      │
   │   ],                                            │
   │   estimated_duration: 15s,                      │
   │   requires_approval: false                      │
   │ }                                               │
   └─────────────────────────────────────────────────┘

2. EXECUTION PHASE
   ┌─────────────────────────────────────────────────┐
   │ Orchestrator.execute_sync(plan, approved=true)  │
   │                                                 │
   │ ┌─────────────────────────────────────────┐   │
   │ │ 0. Create snapshot (for rollback)       │   │
   │ │    snapshot_id = uuid4()                │   │
   │ └─────────────────────────────────────────┘   │
   │                                                 │
   │ ┌─────────────────────────────────────────┐   │
   │ │ Step 1: SCHEMA_VALIDATION               │   │
   │ │   - Compare local vs cloud schemas      │   │
   │ │   - Check breaking changes              │   │
   │ │   ✅ Success (2.0s)                      │   │
   │ └─────────────────────────────────────────┘   │
   │                                                 │
   │ ┌─────────────────────────────────────────┐   │
   │ │ Step 2: EXPORT_CREATION                 │   │
   │ │   - Collect all unsynced data           │   │
   │ │   - Create JSON bundle                  │   │
   │ │   - Compress with gzip                  │   │
   │ │   ✅ Success (5.0s, 500 records)         │   │
   │ └─────────────────────────────────────────┘   │
   │                                                 │
   │ ┌─────────────────────────────────────────┐   │
   │ │ Step 3: DATA_UPLOAD                     │   │
   │ │   - Upload bundle to cloud API          │   │
   │ │   - Verify upload integrity             │   │
   │ │   ✅ Success (10.0s, 5MB)                │   │
   │ └─────────────────────────────────────────┘   │
   │                                                 │
   │ ┌─────────────────────────────────────────┐   │
   │ │ Step 4: UPDATE_WATERMARKS               │   │
   │ │   - Update sync_state.last_sync_at      │   │
   │ │   - Update watermark.last_id            │   │
   │ │   ✅ Success (1.0s)                      │   │
   │ └─────────────────────────────────────────┘   │
   │                                                 │
   │ ┌─────────────────────────────────────────┐   │
   │ │ Step 5: MARK_SYNCED                     │   │
   │ │   - Update change_log.synced = true     │   │
   │ │   - Set synced_at timestamp             │   │
   │ │   ✅ Success (1.0s)                      │   │
   │ └─────────────────────────────────────────┘   │
   │                                                 │
   │ Returns: SyncResult                             │
   │ {                                               │
   │   status: "completed",                          │
   │   duration: 19.0s,                              │
   │   records_synced: 500,                          │
   │   rollback_available: true,                     │
   │   snapshot_id: "..."                            │
   │ }                                               │
   └─────────────────────────────────────────────────┘

PULL SYNC (Cloud → Local):

1. PLAN PHASE
   ┌─────────────────────────────────────────────────┐
   │ Orchestrator.plan_sync(direction="pull")        │
   │                                                 │
   │ ┌─────────────────────────────────────────┐   │
   │ │ 1. Get cloud schema from CloudAPI       │   │
   │ │ 2. Compare with local schema            │   │
   │ │ 3. Get cloud changes since last sync    │   │
   │ │ 4. Generate sync steps                  │   │
   │ └─────────────────────────────────────────┘   │
   │                                                 │
   │ Returns: SyncPlan                               │
   │ {                                               │
   │   steps: [                                      │
   │     1. Schema Validation                        │
   │     2. Data Download                            │
   │     3. Import Data                              │
   │     4. Update Watermarks                        │
   │   ]                                             │
   │ }                                               │
   └─────────────────────────────────────────────────┘

2. EXECUTION PHASE
   ┌─────────────────────────────────────────────────┐
   │ Orchestrator.execute_sync(plan)                 │
   │                                                 │
   │ 0. Create snapshot                              │
   │ 1. Schema Validation ✅                         │
   │ 2. Download bundle from cloud ✅                │
   │ 3. Import to local PostgreSQL/Qdrant ✅         │
   │ 4. Update watermarks ✅                         │
   │                                                 │
   │ Returns: SyncResult (completed)                 │
   └─────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                        ERROR HANDLING & ROLLBACK                        │
└─────────────────────────────────────────────────────────────────────────┘

AUTOMATIC ROLLBACK (on step failure):

   ┌─────────────────────────────────────────────────┐
   │ Step 3: DATA_UPLOAD                             │
   │   ❌ FAILED: Network timeout                    │
   └─────────────────┬───────────────────────────────┘
                     │
                     ▼
   ┌─────────────────────────────────────────────────┐
   │ Orchestrator detects failure                    │
   │   - Stop execution                              │
   │   - Log error                                   │
   │   - Trigger rollback                            │
   └─────────────────┬───────────────────────────────┘
                     │
                     ▼
   ┌─────────────────────────────────────────────────┐
   │ Rollback to snapshot                            │
   │   1. Restore database state                     │
   │   2. Revert watermarks                          │
   │   3. Mark changes as unsynced                   │
   │   ✅ Rollback complete                          │
   └─────────────────┬───────────────────────────────┘
                     │
                     ▼
   ┌─────────────────────────────────────────────────┐
   │ Returns: SyncResult                             │
   │ {                                               │
   │   status: "failed",                             │
   │   failed_steps: 1,                              │
   │   errors: ["Network timeout"],                  │
   │   rollback_available: false  # already rolled   │
   │ }                                               │
   └─────────────────────────────────────────────────┘

MANUAL ROLLBACK (user request):

   ┌─────────────────────────────────────────────────┐
   │ POST /sync/rollback/{sync_id}                   │
   └─────────────────┬───────────────────────────────┘
                     │
                     ▼
   ┌─────────────────────────────────────────────────┐
   │ Orchestrator.rollback_sync(sync_id)             │
   │   1. Get sync record                            │
   │   2. Find snapshot_id                           │
   │   3. Restore snapshot                           │
   │   4. Revert all changes                         │
   └─────────────────┬───────────────────────────────┘
                     │
                     ▼
   ┌─────────────────────────────────────────────────┐
   │ Returns: RollbackResult                         │
   │ {                                               │
   │   success: true,                                │
   │   restored_state: {...}                         │
   │ }                                               │
   └─────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW DIAGRAMS                              │
└─────────────────────────────────────────────────────────────────────────┘

ENTITY COUNT CALCULATION:

   User Request (plan_sync)
        │
        ▼
   Orchestrator._count_entities_to_sync()
        │
        ├──> For each EntityType:
        │    │
        │    ├──> SyncStateService.get_sync_state()
        │    │    Returns: last_sync_at = 2025-12-29T10:00:00Z
        │    │
        │    ├──> CDCService.get_unsynced_changes(since=last_sync_at)
        │    │    Returns: [
        │    │      {entity_type: "tables", operation: "CREATE"},
        │    │      {entity_type: "tables", operation: "UPDATE"},
        │    │      ...
        │    │    ]
        │    │
        │    └──> Count changes by entity type
        │
        └──> Returns: EntityCount {
               tables: 5,
               table_rows: 500,
               vectors: 100,
               memory: 50,
               events: 20,
               files: 10
             }

SCHEMA CHANGE DETECTION:

   Orchestrator._analyze_schema_changes()
        │
        ├──> SchemaDiffService.get_local_schema()
        │    Returns: {
        │      tables: {
        │        "users": {columns: [...], indexes: [...]}
        │      },
        │      vector_collections: {...},
        │      buckets: {...}
        │    }
        │
        ├──> CloudAPIClient.get_cloud_schema()  [TODO: Story #433]
        │    Returns: {cloud schema}
        │
        └──> SchemaDiffService.compare_schemas()
             Returns: SchemaChangeInfo {
               has_changes: true,
               is_breaking: false,
               changes: [
                 "Added column 'email' to users table",
                 "Created index on users.email"
               ],
               migration_required: false
             }

CONFLICT DETECTION:

   Orchestrator._detect_conflicts()
        │
        ├──> Get local changes with timestamps
        │    CDCService.get_unsynced_changes()
        │
        ├──> Get cloud changes with timestamps  [TODO: Story #433]
        │    CloudAPIClient.get_changes_since(last_sync)
        │
        └──> Compare timestamps for same entities
             If both modified same entity:
               Returns: ConflictInfo {
                 has_conflicts: true,
                 conflict_count: 3,
                 conflicts: [
                   {
                     entity_id: "abc123",
                     local_timestamp: "2025-12-29T10:05:00Z",
                     cloud_timestamp: "2025-12-29T10:03:00Z",
                     recommended_resolution: "newest_wins"
                   }
                 ]
               }


┌─────────────────────────────────────────────────────────────────────────┐
│                    INTEGRATION WITH OTHER STORIES                       │
└─────────────────────────────────────────────────────────────────────────┘

Story #429 - Sync State Service:
   ┌─────────────────────────────────────┐
   │ SyncStateService                    │
   │                                     │
   │ ✅ get_sync_state(project, entity)  │ ← Orchestrator reads
   │ ✅ update_sync_state(watermark)     │ ← Orchestrator updates
   │ ✅ get_or_create_sync_state()       │ ← Orchestrator initializes
   └─────────────────────────────────────┘

Story #430 - CDC Service:
   ┌─────────────────────────────────────┐
   │ CDCService                          │
   │                                     │
   │ ✅ get_unsynced_changes()           │ ← Orchestrator reads
   │ ✅ mark_changes_synced()            │ ← Orchestrator marks
   │ ✅ get_changes_since(timestamp)     │ ← Orchestrator filters
   └─────────────────────────────────────┘

Story #431 - Schema Diff Service:
   ┌─────────────────────────────────────┐
   │ SchemaDiffService                   │
   │                                     │
   │ ✅ get_local_schema()               │ ← Orchestrator reads
   │ ✅ compare_schemas()                │ ← Orchestrator compares
   │ ✅ detect_breaking_changes()        │ ← Orchestrator validates
   └─────────────────────────────────────┘

Story #432 - Export Service [TODO]:
   ┌─────────────────────────────────────┐
   │ ExportService                       │
   │                                     │
   │ ⏳ create_full_export()             │ ← Orchestrator creates
   │ ⏳ create_incremental_export()      │ ← Orchestrator creates
   │ ⏳ create_selective_export()        │ ← Orchestrator creates
   └─────────────────────────────────────┘

Story #433 - Cloud API Client [TODO]:
   ┌─────────────────────────────────────┐
   │ CloudAPIClient                      │
   │                                     │
   │ ⏳ upload_bundle()                  │ ← Orchestrator uploads
   │ ⏳ download_bundle()                │ ← Orchestrator downloads
   │ ⏳ get_cloud_schema()               │ ← Orchestrator compares
   │ ⏳ get_cloud_changes()              │ ← Orchestrator conflicts
   └─────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                         DECISION TREE                                   │
└─────────────────────────────────────────────────────────────────────────┘

Should sync require approval?

   START
     │
     ├─> Has breaking schema changes? ──YES──┐
     │                                        │
     ├─> Has conflicts? ──────────────YES────┤
     │                                        │
     └─> Data size > 100MB? ─────────YES─────┤
                                              │
                                              ▼
                                        REQUIRES_APPROVAL = true
                                              │
                                              ▼
                                        User must pass approved=true
                                              │
                                              ▼
                                        Execution proceeds

   If ALL NO:
     │
     ▼
   REQUIRES_APPROVAL = false
     │
     ▼
   Execution proceeds immediately


┌─────────────────────────────────────────────────────────────────────────┐
│                      PERFORMANCE CHARACTERISTICS                        │
└─────────────────────────────────────────────────────────────────────────┘

Plan Generation Time:
   - 0-100 changes:    0.5-1.0 seconds
   - 100-1000 changes: 1.0-2.0 seconds
   - 1000+ changes:    2.0-5.0 seconds

Execution Time (depends on network and data):
   - Small (<1MB):     5-10 seconds
   - Medium (1-10MB):  10-30 seconds
   - Large (>10MB):    30+ seconds (warns user)

Memory Usage:
   - Plan generation:  ~10MB
   - Execution:        ~50MB + data size
   - Rollback:         ~20MB

Database Impact:
   - Read queries:     Low (indexed on project_id, entity_type)
   - Write queries:    Medium (bulk updates to change_log)
   - Locks:            Row-level only (no table locks)
