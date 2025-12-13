# -*- coding: utf-8 -*-
"""
Notifier Monitors - Maya state monitors that trigger notifications.

Each monitor class watches a specific Maya state (AutoKey, Undo, Scene Save, etc.)
and triggers the appropriate notification when that state changes.
"""

from __future__ import print_function, division

from maya import cmds
import maya.api.OpenMaya as om


class BaseMonitor(object):
    """
    Base class for all state monitors.

    Subclasses must implement:
        - MONITOR_ID: Unique identifier for this monitor
        - NOTIFICATION_ID: The notification type to trigger
        - DEFAULT_TEXT: Default notification message
        - DEFAULT_COLOR: Default RGB color tuple
        - _install_callbacks(): Set up Maya callbacks
        - _uninstall_callbacks(): Remove Maya callbacks
    """

    MONITOR_ID = None
    NOTIFICATION_ID = None
    DEFAULT_TEXT = ""
    DEFAULT_COLOR = (255, 255, 255)

    def __init__(self, notifier_api):
        """
        Initialize the monitor.

        Args:
            notifier_api: The notifier module/API for showing/hiding notifications
        """
        self._api = notifier_api
        self._installed = False
        self._callbacks = []
        self._script_jobs = []

    @property
    def is_installed(self):
        """Check if the monitor is currently installed."""
        return self._installed

    def install(self):
        """Install the monitor callbacks."""
        if self._installed:
            return

        # Ensure the notification type is registered
        if not self._api.get_config().get(self.NOTIFICATION_ID):
            self._api.register(
                self.NOTIFICATION_ID,
                text=self.DEFAULT_TEXT,
                color=self.DEFAULT_COLOR
            )

        self._install_callbacks()
        self._installed = True
        self._check_initial_state()

    def uninstall(self):
        """Uninstall the monitor callbacks and hide any active notification."""
        if not self._installed:
            return

        self._uninstall_callbacks()
        self._api.hide(self.NOTIFICATION_ID)
        self._installed = False

    def _install_callbacks(self):
        """Install Maya callbacks. Override in subclasses."""
        raise NotImplementedError

    def _uninstall_callbacks(self):
        """Uninstall Maya callbacks."""
        # Remove OpenMaya callbacks
        for callback_id in self._callbacks:
            try:
                om.MMessage.removeCallback(callback_id)
            except Exception as e:
                print("Notifier: Could not remove callback: {}".format(e))
        self._callbacks = []

        # Remove scriptJobs
        for job_id in self._script_jobs:
            try:
                if cmds.scriptJob(exists=job_id):
                    cmds.scriptJob(kill=job_id)
            except Exception as e:
                print("Notifier: Could not kill scriptJob {}: {}".format(job_id, e))
        self._script_jobs = []

    def _check_initial_state(self):
        """Check the initial state and show/hide notification accordingly."""
        pass

    def _show(self):
        """Show the notification."""
        self._api.show(self.NOTIFICATION_ID)

    def _hide(self):
        """Hide the notification."""
        self._api.hide(self.NOTIFICATION_ID)


# =============================================================================
# AutoKey Monitor
# =============================================================================

class AutoKeyMonitor(BaseMonitor):
    """
    Monitors the AutoKey state and shows a notification when AutoKey is OFF.
    """

    MONITOR_ID = "autokey_monitor"
    NOTIFICATION_ID = "autokey"
    DEFAULT_TEXT = "AutoKey is OFF"
    DEFAULT_COLOR = (255, 20, 60)  # Crimson red

    def _install_callbacks(self):
        """Install scriptJobs for autokey state changes."""
        # conditionTrue: fires when autokey turns ON -> hide notification
        job_on = cmds.scriptJob(
            conditionTrue=["autoKeyframeState", self._on_autokey_on]
        )
        self._script_jobs.append(job_on)

        # conditionFalse: fires when autokey turns OFF -> show notification
        job_off = cmds.scriptJob(
            conditionFalse=["autoKeyframeState", self._on_autokey_off]
        )
        self._script_jobs.append(job_off)

    def _check_initial_state(self):
        """Check current autokey state."""
        is_on = cmds.autoKeyframe(query=True, state=True)
        if not is_on:
            self._show()

    def _on_autokey_on(self):
        """Called when autokey is turned ON."""
        self._hide()

    def _on_autokey_off(self):
        """Called when autokey is turned OFF."""
        self._show()


# =============================================================================
# Scene Save Monitor
# =============================================================================

class SceneSaveMonitor(BaseMonitor):
    """
    Monitors scene save events and shows a notification while saving.
    """

    MONITOR_ID = "scene_save_monitor"
    NOTIFICATION_ID = "saving"
    DEFAULT_TEXT = "Scene Saving..."
    DEFAULT_COLOR = (255, 200, 0)  # Golden yellow

    def _install_callbacks(self):
        """Install OpenMaya callbacks for scene save events."""
        # Before save - show notification
        cb_before = om.MSceneMessage.addCallback(
            om.MSceneMessage.kBeforeSave,
            self._on_before_save
        )
        self._callbacks.append(cb_before)

        # After save - hide notification
        cb_after = om.MSceneMessage.addCallback(
            om.MSceneMessage.kAfterSave,
            self._on_after_save
        )
        self._callbacks.append(cb_after)

        # Save failed - also hide notification
        cb_failed = om.MSceneMessage.addCallback(
            om.MSceneMessage.kMayaExiting,
            self._on_after_save
        )
        self._callbacks.append(cb_failed)

    def _on_before_save(self, *args):
        """Called before scene save begins."""
        self._show()

    def _on_after_save(self, *args):
        """Called after scene save completes."""
        self._hide()


# =============================================================================
# Undo Monitor
# =============================================================================

class UndoMonitor(BaseMonitor):
    """
    Monitors the undo queue state and shows a notification when undo is disabled.
    """

    MONITOR_ID = "undo_monitor"
    NOTIFICATION_ID = "undo"
    DEFAULT_TEXT = "Undo is OFF"
    DEFAULT_COLOR = (255, 165, 0)  # Orange

    def _install_callbacks(self):
        """Install scriptJob to monitor undo state changes."""
        # Use an event that fires when undo state might change
        # We'll check undo state on various events
        job = cmds.scriptJob(
            event=["SceneOpened", self._check_undo_state]
        )
        self._script_jobs.append(job)

        job2 = cmds.scriptJob(
            event=["NewSceneOpened", self._check_undo_state]
        )
        self._script_jobs.append(job2)

        # Also install a callback for undo queue flush
        cb = om.MEventMessage.addEventCallback("undoSupressed", self._on_undo_changed)
        self._callbacks.append(cb)

    def _check_initial_state(self):
        """Check current undo state."""
        self._check_undo_state()

    def _check_undo_state(self, *args):
        """Check if undo is currently enabled."""
        is_enabled = cmds.undoInfo(query=True, state=True)
        if not is_enabled:
            self._show()
        else:
            self._hide()

    def _on_undo_changed(self, *args):
        """Called when undo state changes."""
        self._check_undo_state()


# =============================================================================
# New Scene Monitor
# =============================================================================

class NewSceneMonitor(BaseMonitor):
    """
    Monitors for unsaved changes and shows a notification.
    """

    MONITOR_ID = "new_scene_monitor"
    NOTIFICATION_ID = "unsaved"
    DEFAULT_TEXT = "Unsaved Changes"
    DEFAULT_COLOR = (255, 100, 100)  # Light red

    def _install_callbacks(self):
        """Install callbacks for scene modification tracking."""
        # After any modification
        cb = om.MSceneMessage.addCallback(
            om.MSceneMessage.kSceneUpdate,
            self._on_scene_modified
        )
        self._callbacks.append(cb)

        # After save - hide notification
        cb_save = om.MSceneMessage.addCallback(
            om.MSceneMessage.kAfterSave,
            self._on_scene_saved
        )
        self._callbacks.append(cb_save)

        # New scene - hide notification
        cb_new = om.MSceneMessage.addCallback(
            om.MSceneMessage.kAfterNew,
            self._on_scene_saved
        )
        self._callbacks.append(cb_new)

        # Open scene - hide notification
        cb_open = om.MSceneMessage.addCallback(
            om.MSceneMessage.kAfterOpen,
            self._on_scene_saved
        )
        self._callbacks.append(cb_open)

    def _check_initial_state(self):
        """Check if scene has unsaved changes."""
        if cmds.file(query=True, modified=True):
            self._show()

    def _on_scene_modified(self, *args):
        """Called when scene is modified."""
        if cmds.file(query=True, modified=True):
            self._show()

    def _on_scene_saved(self, *args):
        """Called when scene is saved or reset."""
        self._hide()


# =============================================================================
# Monitor Registry
# =============================================================================

# All available monitor classes
AVAILABLE_MONITORS = {
    AutoKeyMonitor.MONITOR_ID: AutoKeyMonitor,
    SceneSaveMonitor.MONITOR_ID: SceneSaveMonitor,
    UndoMonitor.MONITOR_ID: UndoMonitor,
    NewSceneMonitor.MONITOR_ID: NewSceneMonitor,
}


def get_monitor_class(monitor_id):
    """
    Get a monitor class by its ID.

    Args:
        monitor_id (str): The monitor identifier

    Returns:
        class: The monitor class, or None if not found
    """
    return AVAILABLE_MONITORS.get(monitor_id)


def get_all_monitor_ids():
    """
    Get all available monitor IDs.

    Returns:
        list: List of monitor ID strings
    """
    return list(AVAILABLE_MONITORS.keys())
