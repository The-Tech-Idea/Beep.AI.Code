# Singleton Services Refactoring - Summary

## Overview
All Beep services are now managed as singletons through a central `AppService` registry. This ensures services are not recreated on each access and provides a single source of truth for service instances.

## Changes Made

### 1. Created Central Registry (`beep/app_service.py`)
- **AppService** class that owns all singletons
- Lazy initialization of services (created on first access)
- Keyed singleton support for services that need different instances per configuration (e.g., WatcherService per root path)
- `get_app_service()` global accessor
- `reset()` and `reset_registry()` methods for testing

### 2. Registered Services
The following services are now managed as singletons:

| Service | Type | Access Pattern |
|---------|------|----------------|
| CodeAnalysisService | Simple singleton | `app.code_analysis` |
| BookmarkManager | Simple singleton | `app.bookmarks` |
| TaskManager | Simple singleton | `app.tasks` |
| PermissionManager | Simple singleton | `app.permissions` |
| HookConfig | Simple singleton | `app.hooks` |
| WatcherService | Keyed singleton | `app.watcher(root_path)` |
| SessionManager | Factory (per-session) | `app.session_manager(config, client)` |

### 3. Updated Call Sites
Replaced direct instantiation with AppService access:
- `beep/agent/graph_runner.py` - PermissionManager
- `beep/chat/commands/model.py` - PermissionManager
- `beep/chat/commands/productivity.py` - BookmarkManager
- `beep/chat/session_runtime_state.py` - TaskManager, WatcherService
- `beep/commands/watch.py` - WatcherService

### 4. Fixed Bugs Found
- **TaskManager** (`beep/tasks/manager.py:79`): Fixed NameError where `e` was used instead of `exc`

### 5. Added Tests
Created `tests/test_app_service.py` with 10 tests covering:
- AppService singleton behavior
- Each managed service returns same instance
- Watcher keyed singleton (same root = same instance, different roots = different instances)
- Reset functionality

### 6. Updated Existing Tests
- `tests/test_chat_session_commands.py`: Updated monkeypatch targets to also patch `beep.app_service.*` since imports now flow through AppService

## Usage Example

```python
from beep.app_service import get_app_service

app = get_app_service()

# Access singleton services
app.code_analysis.analyze_project("/path/to/project")
app.bookmarks.add("myfile", Path("/path"))
app.permissions.evaluate_permission("shell", {}, workspace)

# Access keyed singleton (one per root path)
watcher = app.watcher("/workspace/path")

# Create session manager (not globally singleton - per session)
session_mgr = app.session_manager(config, client)
```

## Architecture Benefits
1. **Single source of truth**: All services owned in one place
2. **Lazy initialization**: Services created only when first accessed
3. **Testability**: Easy to reset registry between tests
4. **No scattered singleton code**: Individual service modules are clean classes
5. **Consistent pattern**: All services follow same lifecycle management

## Files Modified
- `beep/app_service.py` (new)
- `beep/utils/singleton.py` (new)
- `beep/codeanalysis/service.py`
- `beep/watcher/service.py`
- `beep/bookmarks/manager.py`
- `beep/tasks/manager.py`
- `beep/agent/graph_runner.py`
- `beep/chat/commands/model.py`
- `beep/chat/commands/productivity.py`
- `beep/chat/session_runtime_state.py`
- `beep/commands/watch.py`
- `tests/test_app_service.py` (new)
- `tests/test_chat_session_commands.py`
