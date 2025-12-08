# -*- coding: utf-8 -*-
"""
Notifier - A viewport notification system for Maya

Displays colored border notifications around Maya viewports to alert users
about important states like AutoKey being disabled, Undo being off, etc.

Multiple notifications stack as nested borders (like Russian nesting dolls),
with each subsequent notification appearing inside the previous one.

Usage:
    import notifier

    # Activate with default monitors (AutoKey)
    notifier.activate()

    # Or activate specific monitors
    notifier.activate(monitors=["autokey_monitor", "scene_save_monitor"])

    # Manually show/hide notifications
    notifier.show("saving")
    notifier.hide("saving")

    # Open the options UI
    notifier.show_options()

    # Deactivate
    notifier.deactivate()
"""

from __future__ import print_function, division

from maya import cmds
import maya.api.OpenMaya as api

from .core import (
    NotificationConfig,
    NotificationManager,
    NotificationLayer,
    get_viewport_widget,
    get_maya_main_window,
)
from . import monitors as _monitors_module


# =============================================================================
# Global State
# =============================================================================

_config = NotificationConfig()
_managers = {}  # panel_name -> NotificationManager
_monitors = {}  # monitor_id -> monitor instance
_active = False


# =============================================================================
# Internal Functions
# =============================================================================

def _ensure_managers():
    """Ensure a NotificationManager exists for each model panel."""
    global _managers

    panels = cmds.getPanel(type="modelPanel") or []

    # Create managers for new panels
    for panel in panels:
        if panel not in _managers:
            widget = get_viewport_widget(panel)
            if widget:
                _managers[panel] = NotificationManager(panel, widget, _config)

    # Remove managers for panels that no longer exist
    stale_panels = [p for p in _managers if p not in panels]
    for panel in stale_panels:
        _managers[panel].cleanup()
        del _managers[panel]


# =============================================================================
# Public API - Configuration
# =============================================================================

def register(type_id, text, color, enabled=True):
    """
    Register a new notification type.

    Args:
        type_id (str): Unique identifier for this notification type
        text (str): Display text for the notification label
        color (tuple): RGB color tuple, e.g., (255, 20, 60)
        enabled (bool): Whether this notification type is enabled by default

    Example:
        notifier.register("undo", text="Undo is OFF", color=(255, 165, 0))
    """
    _config.register(type_id, text, color, enabled)


def get_config():
    """
    Get the notification configuration store.

    Returns:
        NotificationConfig: The configuration store
    """
    return _config


# =============================================================================
# Public API - Activation
# =============================================================================

def activate(monitor_ids=None):
    """
    Activate the notification system.

    Args:
        monitor_ids (list, optional): List of monitor IDs to install.
            If None, installs only the AutoKey monitor by default.
            Use get_available_monitors() to see all options.

    Example:
        # Default - just AutoKey monitoring
        notifier.activate()

        # Multiple monitors
        notifier.activate(monitors=["autokey_monitor", "scene_save_monitor"])
    """
    global _active

    if _active:
        print("Notifier: Already active.")
        return

    _ensure_managers()

    # Default to autokey monitor only
    if monitor_ids is None:
        monitor_ids = ["autokey_monitor"]

    # Install requested monitors
    for monitor_id in monitor_ids:
        install_monitor(monitor_id)

    _active = True
    api.MGlobal.displayInfo("Notifier: Activated.")


def deactivate():
    """
    Deactivate the notification system.

    This removes all notifications, uninstalls all monitors, and cleans up.
    """
    global _active, _managers, _monitors

    # Uninstall all monitors
    for monitor_id in list(_monitors.keys()):
        uninstall_monitor(monitor_id)

    # Clean up all managers
    for manager in _managers.values():
        manager.cleanup()
    _managers.clear()

    _active = False
    api.MGlobal.displayInfo("Notifier: Deactivated.")


def is_active():
    """
    Check if the notification system is active.

    Returns:
        bool: True if active, False otherwise
    """
    return _active


# =============================================================================
# Public API - Monitor Management
# =============================================================================

def install_monitor(monitor_id):
    """
    Install a state monitor.

    Args:
        monitor_id (str): The monitor identifier

    Returns:
        bool: True if installed, False if already installed or not found
    """
    global _monitors

    if monitor_id in _monitors:
        return False

    monitor_class = _monitors_module.get_monitor_class(monitor_id)
    if not monitor_class:
        print("Notifier: Unknown monitor '{}'".format(monitor_id))
        return False

    # Import this module to pass as the API
    import notifier
    monitor = monitor_class(notifier)
    monitor.install()
    _monitors[monitor_id] = monitor

    return True


def uninstall_monitor(monitor_id):
    """
    Uninstall a state monitor.

    Args:
        monitor_id (str): The monitor identifier

    Returns:
        bool: True if uninstalled, False if not found
    """
    global _monitors

    if monitor_id not in _monitors:
        return False

    monitor = _monitors.pop(monitor_id)
    monitor.uninstall()

    return True


def is_monitor_installed(monitor_id):
    """
    Check if a monitor is currently installed.

    Args:
        monitor_id (str): The monitor identifier

    Returns:
        bool: True if installed, False otherwise
    """
    return monitor_id in _monitors


def get_available_monitors():
    """
    Get a list of all available monitor IDs.

    Returns:
        list: List of monitor ID strings
    """
    return _monitors_module.get_all_monitor_ids()


def get_installed_monitors():
    """
    Get a list of currently installed monitor IDs.

    Returns:
        list: List of installed monitor ID strings
    """
    return list(_monitors.keys())


# =============================================================================
# Public API - Notification Display
# =============================================================================

def show(type_id):
    """
    Manually show a notification on all viewports.

    Args:
        type_id (str): The notification type to show

    Example:
        notifier.show("saving")
    """
    _ensure_managers()

    for manager in _managers.values():
        manager.show_notification(type_id)


def hide(type_id):
    """
    Manually hide a notification from all viewports.

    Args:
        type_id (str): The notification type to hide

    Example:
        notifier.hide("saving")
    """
    for manager in _managers.values():
        manager.hide_notification(type_id)


def refresh_all():
    """Refresh all active notification displays (e.g., after config change)."""
    for manager in _managers.values():
        manager.refresh_all()


# =============================================================================
# Public API - Options UI
# =============================================================================

def show_options():
    """
    Show the options dialog for configuring notifications and monitors.
    """
    from .ui import OptionsDialog
    import notifier

    _ensure_managers()

    parent = get_maya_main_window()
    dialog = OptionsDialog(notifier, parent)
    dialog.show()


# =============================================================================
# Convenience Functions
# =============================================================================

def notify_saving(show_notification=True):
    """
    Show or hide the 'scene saving' notification.

    Args:
        show_notification (bool): True to show, False to hide
    """
    if not _config.get("saving"):
        register("saving", text="Scene Saving...", color=(255, 200, 0))

    if show_notification:
        show("saving")
    else:
        hide("saving")


def notify_undo_off(show_notification=True):
    """
    Show or hide the 'undo disabled' notification.

    Args:
        show_notification (bool): True to show, False to hide
    """
    if not _config.get("undo"):
        register("undo", text="Undo is OFF", color=(255, 165, 0))

    if show_notification:
        show("undo")
    else:
        hide("undo")
