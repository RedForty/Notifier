# -*- coding: utf-8 -*-
"""
Notifier UI - Options dialog for configuring notifications and monitors.
"""

from __future__ import print_function, division

import maya.api.OpenMaya as api
from Qt import QtCore, QtGui, QtWidgets

from . import monitors


class OptionsDialog(QtWidgets.QDialog):
    """Configuration dialog for notification and monitor settings."""

    WINDOW_TITLE = "Notifier Options"
    WINDOW_OBJECT_NAME = "notifier_options_dialog"

    def __init__(self, notifier_api, parent=None):
        """
        Initialize the options dialog.

        Args:
            notifier_api: The notifier module/API
            parent (QWidget): Optional parent widget
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
        self._notification_widgets = {}

        self.setObjectName(self.WINDOW_OBJECT_NAME)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)

        # Create tab widget
        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        # Monitors tab
        monitors_tab = self._build_monitors_tab()
        tabs.addTab(monitors_tab, "Monitors")

        # Notifications tab
        notifications_tab = self._build_notifications_tab()
        tabs.addTab(notifications_tab, "Appearance")

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

    def _build_monitors_tab(self):
        """Build the monitors configuration tab."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Header
        header = QtWidgets.QLabel("Enable or disable state monitors:")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        desc = QtWidgets.QLabel(
            "Monitors watch Maya states and automatically show/hide notifications."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Monitor list
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)

        # Add each available monitor
        monitor_info = {
            "autokey_monitor": {
                "title": "AutoKey Monitor",
                "description": "Shows notification when AutoKey is disabled"
            },
            "scene_save_monitor": {
                "title": "Scene Save Monitor",
                "description": "Shows notification while scene is being saved"
            },
            "undo_monitor": {
                "title": "Undo Monitor",
                "description": "Shows notification when Undo queue is disabled"
            },
            "new_scene_monitor": {
                "title": "Unsaved Changes Monitor",
                "description": "Shows notification when scene has unsaved changes"
            },
        }

        for monitor_id in monitors.get_all_monitor_ids():
            info = monitor_info.get(monitor_id, {})
            title = info.get("title", monitor_id.replace("_", " ").title())
            description = info.get("description", "")

            group = QtWidgets.QGroupBox(title)
            group_layout = QtWidgets.QVBoxLayout(group)

            # Enabled checkbox
            enabled_cb = QtWidgets.QCheckBox("Enabled")
            is_installed = self._api.is_monitor_installed(monitor_id)
            enabled_cb.setChecked(is_installed)
            group_layout.addWidget(enabled_cb)

            # Description
            if description:
                desc_label = QtWidgets.QLabel(description)
                desc_label.setStyleSheet("color: gray; font-size: 11px;")
                desc_label.setWordWrap(True)
                group_layout.addWidget(desc_label)

            scroll_layout.addWidget(group)
            self._monitor_widgets[monitor_id] = {
                "enabled": enabled_cb
            }

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        return widget

    def _build_notifications_tab(self):
        """Build the notifications appearance tab."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Header
        header = QtWidgets.QLabel("Customize notification appearance:")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        # Notification type list
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        scroll_widget = QtWidgets.QWidget()
        self._notifications_layout = QtWidgets.QVBoxLayout(scroll_widget)
        self._notifications_layout.setSpacing(10)

        for type_id in self._config_store.get_all_types():
            self._add_notification_widget(type_id)

        self._notifications_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        return widget

    def _add_notification_widget(self, type_id):
        """Add a configuration widget for a notification type."""
        config = self._config_store.get(type_id)
        if not config:
            return

        group = QtWidgets.QGroupBox(type_id.replace("_", " ").title())
        group_layout = QtWidgets.QFormLayout(group)

        # Enabled checkbox
        enabled_cb = QtWidgets.QCheckBox()
        enabled_cb.setChecked(config["enabled"])
        group_layout.addRow("Show notification:", enabled_cb)

        # Text field
        text_edit = QtWidgets.QLineEdit()
        text_edit.setText(config["text"])
        group_layout.addRow("Message:", text_edit)

        # Color picker
        color_layout = QtWidgets.QHBoxLayout()

        color_btn = QtWidgets.QPushButton()
        color_btn.setFixedSize(60, 24)
        r, g, b = config["color"]
        color_btn.setStyleSheet("background: rgb({}, {}, {});".format(r, g, b))
        color_btn.clicked.connect(lambda checked, tid=type_id: self._pick_color(tid))
        color_layout.addWidget(color_btn)

        # Preview swatch
        preview_label = QtWidgets.QLabel("  Preview")
        preview_label.setStyleSheet(
            "background: rgb({}, {}, {}); color: white; font-weight: bold; "
            "padding: 2px 8px;".format(r, g, b)
        )
        color_layout.addWidget(preview_label)
        color_layout.addStretch()

        group_layout.addRow("Color:", color_layout)

        self._notifications_layout.addWidget(group)
        self._notification_widgets[type_id] = {
            "enabled": enabled_cb,
            "text": text_edit,
            "color_btn": color_btn,
            "preview": preview_label,
            "color": config["color"]
        }

    def _pick_color(self, type_id):
        """Open color picker for a notification type."""
        widgets = self._notification_widgets.get(type_id)
        if not widgets:
            return

        current = widgets["color"]
        initial = QtGui.QColor(current[0], current[1], current[2])

        color = QtWidgets.QColorDialog.getColor(initial, self, "Select Color")
        if color.isValid():
            new_color = (color.red(), color.green(), color.blue())
            widgets["color"] = new_color
            r, g, b = new_color
            widgets["color_btn"].setStyleSheet(
                "background: rgb({}, {}, {});".format(r, g, b)
            )
            widgets["preview"].setStyleSheet(
                "background: rgb({}, {}, {}); color: white; font-weight: bold; "
                "padding: 2px 8px;".format(r, g, b)
            )

    def _on_apply(self):
        """Apply all changes."""
        # Apply monitor changes
        for monitor_id, widgets in self._monitor_widgets.items():
            should_be_enabled = widgets["enabled"].isChecked()
            is_enabled = self._api.is_monitor_installed(monitor_id)

            if should_be_enabled and not is_enabled:
                self._api.install_monitor(monitor_id)
            elif not should_be_enabled and is_enabled:
                self._api.uninstall_monitor(monitor_id)

        # Apply notification appearance changes
        for type_id, widgets in self._notification_widgets.items():
            self._config_store.set_enabled(type_id, widgets["enabled"].isChecked())
            self._config_store.set_text(type_id, widgets["text"].text())
            self._config_store.set_color(type_id, widgets["color"])

        # Refresh all active notifications
        self._api.refresh_all()

        api.MGlobal.displayInfo("Notifier: Settings applied.")
