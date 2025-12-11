# -*- coding: utf-8 -*-
"""
Notifier UI - Options dialog for configuring notifications and monitors.
"""

from __future__ import print_function, division

import maya.api.OpenMaya as api
from Qt import QtCore, QtGui, QtWidgets

from . import monitors


# Monitor metadata for display purposes
MONITOR_INFO = {
    "autokey_monitor": {
        "title": "AutoKey Monitor",
        "description": "Shows notification when AutoKey is disabled",
        "notification_id": "autokey",
    },
    "scene_save_monitor": {
        "title": "Scene Save Monitor",
        "description": "Shows notification while scene is being saved",
        "notification_id": "saving",
    },
    "undo_monitor": {
        "title": "Undo Monitor",
        "description": "Shows notification when Undo queue is disabled",
        "notification_id": "undo",
    },
    "new_scene_monitor": {
        "title": "Unsaved Changes Monitor",
        "description": "Shows notification when scene has unsaved changes",
        "notification_id": "unsaved",
    },
}


class OptionsDialog(QtWidgets.QDialog):
    """Configuration dialog for notification and monitor settings."""

    WINDOW_TITLE = "Notifier Options"
    WINDOW_OBJECT_NAME = "notifier_options_dialog"

    def __init__(self, notifier_api, parent=None):
        """
        Initialize the options dialog.

        Args:
            notifier_api: The notifier module/API
            parent (QWidget): Optional parent widget (should be Maya main window)
        """
        # Delete existing window if it exists
        existing = None
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if widget.objectName() == self.WINDOW_OBJECT_NAME:
                existing = widget
                break
        if existing:
            existing.close()
            existing.deleteLater()

        super(OptionsDialog, self).__init__(parent)

        self._api = notifier_api
        self._config_store = notifier_api.get_config()
        self._monitor_widgets = {}
        self._preview_notification_id = None
        self._preview_original_color = None

        self.setObjectName(self.WINDOW_OBJECT_NAME)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumWidth(400)
        self.setMinimumHeight(450)

        # Standard flags for a dialog parented to Maya - stays above parent automatically
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint
        )

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)

        # Header
        header = QtWidgets.QLabel("Configure Notification Monitors")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        desc = QtWidgets.QLabel(
            "Enable monitors to automatically show notifications when Maya states change. "
            "Customize the appearance of each notification below."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Scrollable monitor list
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        scroll_widget = QtWidgets.QWidget()
        self._monitors_layout = QtWidgets.QVBoxLayout(scroll_widget)
        self._monitors_layout.setSpacing(12)

        # Add each available monitor with its notification settings
        for monitor_id in monitors.get_all_monitor_ids():
            self._add_monitor_widget(monitor_id)

        self._monitors_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Separator
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        apply_btn = QtWidgets.QPushButton("Apply")
        apply_btn.clicked.connect(self._on_apply)
        button_layout.addWidget(apply_btn)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _add_monitor_widget(self, monitor_id):
        """Add a configuration widget for a monitor and its notification."""
        info = MONITOR_INFO.get(monitor_id, {})
        title = info.get("title", monitor_id.replace("_", " ").title())
        description = info.get("description", "")
        notification_id = info.get("notification_id", monitor_id.replace("_monitor", ""))

        # Get notification config if it exists
        config = self._config_store.get(notification_id)

        group = QtWidgets.QGroupBox(title)
        group_layout = QtWidgets.QVBoxLayout(group)

        # Top row: Enabled checkbox and description
        top_layout = QtWidgets.QHBoxLayout()

        enabled_cb = QtWidgets.QCheckBox("Enabled")
        is_installed = self._api.is_monitor_installed(monitor_id)
        enabled_cb.setChecked(is_installed)
        top_layout.addWidget(enabled_cb)

        if description:
            desc_label = QtWidgets.QLabel("- " + description)
            desc_label.setStyleSheet("color: gray;")
            top_layout.addWidget(desc_label)

        top_layout.addStretch()
        group_layout.addLayout(top_layout)

        # Notification settings (message and color)
        settings_layout = QtWidgets.QHBoxLayout()
        settings_layout.setContentsMargins(20, 5, 0, 0)  # Indent

        # Message field
        settings_layout.addWidget(QtWidgets.QLabel("Message:"))
        text_edit = QtWidgets.QLineEdit()
        text_edit.setFixedWidth(150)
        if config:
            text_edit.setText(config["text"])
        else:
            # Use default from monitor class
            monitor_class = monitors.get_monitor_class(monitor_id)
            if monitor_class:
                text_edit.setText(monitor_class.DEFAULT_TEXT)
        settings_layout.addWidget(text_edit)

        settings_layout.addSpacing(20)

        # Color picker
        settings_layout.addWidget(QtWidgets.QLabel("Color:"))
        color_btn = QtWidgets.QPushButton()
        color_btn.setFixedSize(60, 24)

        if config:
            r, g, b = config["color"]
        else:
            # Use default from monitor class
            monitor_class = monitors.get_monitor_class(monitor_id)
            if monitor_class:
                r, g, b = monitor_class.DEFAULT_COLOR
            else:
                r, g, b = 255, 100, 100

        color_btn.setStyleSheet("background: rgb({}, {}, {});".format(r, g, b))

        color_btn.clicked.connect(
            lambda checked=False, mid=monitor_id: self._pick_color(mid)
        )
        settings_layout.addWidget(color_btn)

        settings_layout.addStretch()
        group_layout.addLayout(settings_layout)

        self._monitors_layout.addWidget(group)
        self._monitor_widgets[monitor_id] = {
            "enabled": enabled_cb,
            "text": text_edit,
            "color_btn": color_btn,
            "color": (r, g, b),
            "notification_id": notification_id,
        }

    def _pick_color(self, monitor_id):
        """Open color picker with live preview in viewport."""
        widgets = self._monitor_widgets.get(monitor_id)
        if not widgets:
            return

        notification_id = widgets["notification_id"]
        current_color = widgets["color"]
        self._preview_original_color = current_color

        # Ensure notification is registered so we can show it
        self._api.register(
            notification_id,
            text=widgets["text"].text(),
            color=current_color,
            enabled=True
        )

        # Show the notification as a preview
        self._preview_notification_id = notification_id
        self._api.show(notification_id)

        # Create color dialog with live preview
        color_dialog = QtWidgets.QColorDialog(self)
        color_dialog.setCurrentColor(
            QtGui.QColor(current_color[0], current_color[1], current_color[2])
        )
        color_dialog.setOption(QtWidgets.QColorDialog.NoButtons, False)

        # Connect to live color changes
        color_dialog.currentColorChanged.connect(
            lambda color, mid=monitor_id: self._on_preview_color_changed(mid, color)
        )

        # Show dialog and handle result
        result = color_dialog.exec_()

        if result == QtWidgets.QDialog.Accepted:
            # User accepted - keep the new color
            color = color_dialog.currentColor()
            new_color = (color.red(), color.green(), color.blue())
            widgets["color"] = new_color
            r, g, b = new_color
            widgets["color_btn"].setStyleSheet(
                "background: rgb({}, {}, {});".format(r, g, b)
            )
        else:
            # User cancelled - restore original color
            self._update_preview_color(notification_id, self._preview_original_color)

        # Hide the preview notification
        self._api.hide(notification_id)
        self._preview_notification_id = None
        self._preview_original_color = None

    def _on_preview_color_changed(self, monitor_id, color):
        """Update the notification preview with the new color in real-time."""
        if not color.isValid():
            return

        widgets = self._monitor_widgets.get(monitor_id)
        if not widgets:
            return

        notification_id = widgets["notification_id"]
        new_color = (color.red(), color.green(), color.blue())

        # Update the color in real-time
        self._update_preview_color(notification_id, new_color)

    def _update_preview_color(self, notification_id, color):
        """
        Directly update the notification color without triggering saved prefs reload.
        This allows real-time preview while picking colors.
        """
        # Get the config dict and update color directly
        config = self._config_store.get(notification_id)
        if config:
            # Update the config dict directly (bypasses _load_saved_prefs)
            config["color"] = color

            # Refresh all notifications to show the change
            self._api.refresh_all()

    def _on_apply(self):
        """Apply all changes."""
        for monitor_id, widgets in self._monitor_widgets.items():
            should_be_enabled = widgets["enabled"].isChecked()
            is_enabled = self._api.is_monitor_installed(monitor_id)
            notification_id = widgets["notification_id"]

            # Ensure notification type is registered with current settings
            self._api.register(
                notification_id,
                text=widgets["text"].text(),
                color=widgets["color"],
                enabled=True  # Notification itself is always enabled; monitor controls visibility
            )

            # Save to Maya optionVars for persistence
            self._config_store.set_text(notification_id, widgets["text"].text())
            self._config_store.set_color(notification_id, widgets["color"])

            # Install or uninstall monitor
            if should_be_enabled and not is_enabled:
                self._api.install_monitor(monitor_id)
            elif not should_be_enabled and is_enabled:
                self._api.uninstall_monitor(monitor_id)

        # Refresh all active notifications to show new colors/text
        self._api.refresh_all()

        api.MGlobal.displayInfo("Notifier: Settings applied.")
