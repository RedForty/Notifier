## Notifier

<img align="left" style="float: left; padding-right: 20px" src="https://i.imgur.com/dPgfW1G.png"> A viewport notification system for Maya that displays colored border warnings around your viewports. Multiple notifications stack as nested borders (like Russian nesting dolls), with each subsequent notification appearing inside the previous one.

Perfect for animators who need visual alerts when important states change, like AutoKey being disabled by tools such as StudioLibrary.

---

## Features

- **Stacking notifications** - Multiple notifications nest inside each other
- **Automatic state monitoring** - AutoKey, Scene Save, Undo state, and more
- **Custom notification types** - Register your own notifications with custom text and colors
- **Per-viewport display** - Each 3D viewport gets its own notification stack
- **Persistent settings** - Colors and preferences are saved between sessions
- **Options UI** - Configure monitors and notifications through a visual dialog

---

## Installation

Place the `notifier` folder in your Maya scripts folder:

```
~/maya/scripts/notifier/
    ├── __init__.py
    ├── core.py
    ├── monitors.py
    └── ui.py
```

---

## Quick Start

Create shelf buttons with the following Python code:

**Activate (with default AutoKey monitor):**
```python
import notifier
notifier.activate()
```

**Activate with multiple monitors:**
```python
import notifier
notifier.activate(monitor_ids=[
    "autokey_monitor",
    "scene_save_monitor",
    "undo_monitor"
])
```

**Deactivate:**
```python
import notifier
notifier.deactivate()
```

**Open Options:**
```python
import notifier
notifier.show_options()
```

---

## Available Monitors

| Monitor ID | Description |
|------------|-------------|
| `autokey_monitor` | Shows notification when AutoKey is disabled |
| `scene_save_monitor` | Shows notification while scene is being saved |
| `undo_monitor` | Shows notification when Undo queue is disabled |
| `new_scene_monitor` | Shows notification when scene has unsaved changes |

---

## API Reference

### Activation

#### `activate(monitor_ids=None)`
Start the notification system with specified monitors.

```python
# Default - just AutoKey monitoring
notifier.activate()

# Multiple monitors
notifier.activate(monitor_ids=["autokey_monitor", "scene_save_monitor"])
```

#### `deactivate()`
Stop the notification system and remove all notifications.

#### `is_active()`
Check if the notification system is currently active.

---

### Monitor Management

#### `install_monitor(monitor_id)`
Install a specific state monitor.

```python
notifier.install_monitor("scene_save_monitor")
```

#### `uninstall_monitor(monitor_id)`
Uninstall a specific state monitor.

```python
notifier.uninstall_monitor("scene_save_monitor")
```

#### `get_available_monitors()`
Get a list of all available monitor IDs.

#### `get_installed_monitors()`
Get a list of currently installed monitor IDs.

---

### Manual Notification Control

#### `register(type_id, text, color, enabled=True)`
Register a custom notification type.

```python
notifier.register("custom", text="Custom Alert", color=(100, 200, 255))
```

#### `show(type_id)`
Manually display a notification.

```python
notifier.show("saving")
```

#### `hide(type_id)`
Manually hide a notification.

```python
notifier.hide("saving")
```

---

### Options UI

#### `show_options()`
Open the configuration dialog.

The dialog has two tabs:
- **Monitors** - Enable/disable automatic state monitoring
- **Appearance** - Customize colors and messages for each notification type

---

## Architecture

```
notifier/
├── __init__.py   # Public API
├── core.py       # Notification display engine
├── monitors.py   # Maya state monitors
└── ui.py         # Options dialog
```

**Separation of concerns:**
- `core.py` handles all the Qt widget display logic - no Maya monitoring
- `monitors.py` handles Maya callbacks - no display logic
- `ui.py` provides the configuration interface
- `__init__.py` ties everything together with a clean API

---

## How Stacking Works

When multiple notifications are active, they nest like Russian dolls:

```
┌─────────────────────────────────────────┐  ← Notification 1 (outermost)
│          [AutoKey is OFF]               │
│ ┌─────────────────────────────────────┐ │  ← Notification 2
│ │        [Undo Disabled]              │ │
│ │ ┌─────────────────────────────────┐ │ │  ← Notification 3 (innermost)
│ │ │      [Scene Saving...]          │ │ │
│ │ │                                 │ │ │
│ │ │       Viewport Content          │ │ │
│ │ │                                 │ │ │
│ │ └─────────────────────────────────┘ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

When a notification is hidden, inner notifications automatically collapse outward to fill the gap.

---

## Creating Custom Monitors

You can create your own monitors by subclassing `BaseMonitor`:

```python
from notifier.monitors import BaseMonitor

class MyCustomMonitor(BaseMonitor):
    MONITOR_ID = "my_monitor"
    NOTIFICATION_ID = "my_notification"
    DEFAULT_TEXT = "Something happened!"
    DEFAULT_COLOR = (255, 100, 100)

    def _install_callbacks(self):
        # Set up your Maya callbacks here
        pass

    def _check_initial_state(self):
        # Check state when monitor is first installed
        pass
```

---

## License

MIT License - See LICENSE.md for details.
