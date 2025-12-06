## Notifier

<img align="left" style="float: left; padding-right: 20px" src="https://i.imgur.com/dPgfW1G.png"> A viewport notification system for Maya that displays colored border warnings around your viewports. Multiple notifications stack as nested borders (like Russian nesting dolls), with each subsequent notification appearing inside the previous one.

Perfect for animators who need visual alerts when important states change, like AutoKey being disabled by tools such as StudioLibrary.

---

## Features

- **Stacking notifications** - Multiple notifications nest inside each other
- **Custom notification types** - Register your own notifications with custom text and colors
- **Per-viewport display** - Each 3D viewport gets its own notification stack
- **Persistent settings** - Colors and preferences are saved between sessions
- **Options UI** - Configure notifications through a visual dialog
- **No ghost widgets** - Clean implementation that won't conflict with other viewport tools

---

## Installation

Place `notifier.py` in your Maya scripts folder:

```
~/maya/scripts/notifier.py
```

---

## Quick Start

Create shelf buttons with the following Python code:

**Activate:**
```python
import notifier
notifier.activate()
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

## API Reference

### Core Functions

#### `activate()`
Start the notification system. Sets up monitoring for state changes (e.g., AutoKey).

```python
import notifier
notifier.activate()
```

#### `deactivate()`
Stop the notification system and remove all notifications.

```python
notifier.deactivate()
```

#### `is_active()`
Check if the notification system is currently active.

```python
if notifier.is_active():
    print("Notifier is running")
```

---

### Notification Management

#### `register(type_id, text, color, enabled=True)`
Register a new notification type. Call this before using `show()`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `type_id` | str | Unique identifier for this notification |
| `text` | str | Message displayed in the notification label |
| `color` | tuple | RGB color, e.g., `(255, 20, 60)` |
| `enabled` | bool | Whether this notification is enabled (default: True) |

```python
# Register custom notification types
notifier.register("undo", text="Undo is OFF", color=(255, 165, 0))
notifier.register("saving", text="Scene Saving...", color=(255, 200, 0))
notifier.register("reference", text="Unloaded References", color=(100, 150, 255))
```

#### `show(type_id)`
Display a notification on all viewports. The notification must be registered first.

```python
notifier.show("saving")
```

#### `hide(type_id)`
Remove a notification from all viewports.

```python
notifier.hide("saving")
```

---

### Options UI

#### `show_options()`
Open the configuration dialog to customize notifications.

```python
notifier.show_options()
```

The dialog allows you to:
- Enable/disable notification types
- Change notification messages
- Pick custom colors

---

### Convenience Functions

#### `notify_saving(show_notification=True)`
Quick toggle for a "Scene Saving..." notification.

```python
# Before saving
notifier.notify_saving(True)

# After saving
notifier.notify_saving(False)
```

#### `notify_undo_off(show_notification=True)`
Quick toggle for an "Undo is OFF" notification.

```python
notifier.notify_undo_off(True)   # Show
notifier.notify_undo_off(False)  # Hide
```

---

## Example: Custom Pipeline Integration

```python
import notifier

# Register your studio's notification types at startup
notifier.register("autokey", text="AutoKey is OFF", color=(255, 20, 60))
notifier.register("undo", text="Undo Disabled", color=(255, 165, 0))
notifier.register("saving", text="Saving Scene...", color=(255, 200, 0))
notifier.register("publishing", text="Publishing...", color=(100, 200, 255))

# Activate the system
notifier.activate()

# In your save callback:
def on_save_start():
    notifier.show("saving")

def on_save_end():
    notifier.hide("saving")

# In your publish tool:
def publish_asset():
    notifier.show("publishing")
    try:
        # ... publish logic ...
        pass
    finally:
        notifier.hide("publishing")
```

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

## License

MIT License - See LICENSE.md for details.
