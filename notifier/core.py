# -*- coding: utf-8 -*-
"""
Notifier Core - The notification display engine.

This module contains the core classes for displaying and managing
viewport notifications. It has no Maya-specific monitoring logic;
that belongs in the monitors module.
"""

from __future__ import print_function, division

from maya import cmds
import maya.api.OpenMayaUI as apiui
import maya.OpenMayaUI as omui
from Qt import QtCore, QtWidgets, QtCompat


# =============================================================================
# Configuration Storage
# =============================================================================

class NotificationConfig(object):
    """
    Stores notification type definitions and user preferences.
    Uses Maya optionVars for persistence.
    """

    _PREFIX = "notifier_"

    def __init__(self):
        self._types = {}

    def register(self, type_id, text, color, enabled=True):
        """
        Register a notification type.

        Args:
            type_id (str): Unique identifier for this notification type
            text (str): Display text for the notification label
            color (tuple): RGB color tuple, e.g., (255, 20, 60)
            enabled (bool): Whether this notification type is enabled
        """
        self._types[type_id] = {
            "text": text,
            "color": color,
            "enabled": enabled
        }
        self._load_saved_prefs(type_id)

    def _load_saved_prefs(self, type_id):
        """Load saved preferences from Maya optionVars."""
        color_var = "{}color_{}".format(self._PREFIX, type_id)
        text_var = "{}text_{}".format(self._PREFIX, type_id)
        enabled_var = "{}enabled_{}".format(self._PREFIX, type_id)

        if cmds.optionVar(exists=color_var):
            saved_color = cmds.optionVar(query=color_var)
            if saved_color:
                rgb = [int(c) for c in saved_color.split(",")]
                self._types[type_id]["color"] = tuple(rgb)

        if cmds.optionVar(exists=text_var):
            self._types[type_id]["text"] = cmds.optionVar(query=text_var)

        if cmds.optionVar(exists=enabled_var):
            self._types[type_id]["enabled"] = bool(cmds.optionVar(query=enabled_var))

    def save_prefs(self, type_id):
        """Save preferences to Maya optionVars."""
        if type_id not in self._types:
            return

        config = self._types[type_id]
        color_str = ",".join(str(c) for c in config["color"])

        cmds.optionVar(stringValue=("{}color_{}".format(self._PREFIX, type_id), color_str))
        cmds.optionVar(stringValue=("{}text_{}".format(self._PREFIX, type_id), config["text"]))
        cmds.optionVar(intValue=("{}enabled_{}".format(self._PREFIX, type_id), int(config["enabled"])))

    def get(self, type_id):
        """Get configuration for a notification type."""
        return self._types.get(type_id)

    def set_color(self, type_id, color):
        """Set the color for a notification type."""
        if type_id in self._types:
            self._types[type_id]["color"] = color
            self.save_prefs(type_id)

    def set_text(self, type_id, text):
        """Set the text for a notification type."""
        if type_id in self._types:
            self._types[type_id]["text"] = text
            self.save_prefs(type_id)

    def set_enabled(self, type_id, enabled):
        """Set whether a notification type is enabled."""
        if type_id in self._types:
            self._types[type_id]["enabled"] = enabled
            self.save_prefs(type_id)

    def is_enabled(self, type_id):
        """Check if a notification type is enabled."""
        config = self._types.get(type_id)
        return config["enabled"] if config else False

    def get_all_types(self):
        """Get all registered notification type IDs."""
        return list(self._types.keys())


# =============================================================================
# Notification Layer (Single Border Ring)
# =============================================================================

class NotificationLayer(QtCore.QObject):
    """
    Represents a single notification border ring around a viewport.

    Uses QObject instead of QWidget to avoid the "ghost widget" issue
    where an invisible widget would render as a square in the viewport.
    """

    BORDER_THICKNESS = 6
    LABEL_WIDTH = 120
    LABEL_HEIGHT = 16
    OBJECT_NAME_PREFIX = "notifier_layer_"

    def __init__(self, parent_widget, type_id, config, depth=0):
        """
        Initialize a notification layer.

        Args:
            parent_widget (QWidget): The viewport widget to attach to
            type_id (str): The notification type identifier
            config (dict): Configuration dict with 'text' and 'color' keys
            depth (int): Stack depth (0 = outermost, 1 = next inner, etc.)
        """
        super(NotificationLayer, self).__init__()

        self._parent = parent_widget
        self._type_id = type_id
        self._config = config
        self._depth = depth
        self._buttons = {}
        self._label = None
        self._refresh_filter = None
        self._installed = False

    @property
    def type_id(self):
        """Get the notification type ID."""
        return self._type_id

    @property
    def depth(self):
        """Get the current stack depth."""
        return self._depth

    @depth.setter
    def depth(self, value):
        """Set the stack depth and refresh geometry."""
        self._depth = value
        if self._installed:
            self._refresh_geometry()

    def _create_style(self):
        """Create the stylesheet for this notification's color."""
        r, g, b = self._config["color"]
        return """
            background: rgb({}, {}, {});
            border: 0px;
            text-align: center;
            color: white;
            font-weight: bold;
        """.format(r, g, b)

    def _calculate_margin(self):
        """
        Calculate the margin offset based on depth.

        Each layer is offset by the label height to create the nesting effect.
        The label height naturally provides spacing for the borders.
        """
        return self._depth * self.LABEL_HEIGHT

    def install(self):
        """Install the notification buttons on the viewport."""
        if self._installed:
            return

        style = self._create_style()
        unique_suffix = "{}_{}".format(self._type_id, id(self))

        # Create border buttons (North, East, South, West)
        for direction in ["North", "East", "South", "West"]:
            btn = QtWidgets.QPushButton(self._parent)
            btn.setObjectName("{}{}_{}".format(
                self.OBJECT_NAME_PREFIX, direction, unique_suffix
            ))
            btn.setStyleSheet(style)
            btn.setFocusPolicy(QtCore.Qt.NoFocus)
            btn.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            btn.show()
            self._buttons[direction] = btn

        # Create label
        self._label = QtWidgets.QPushButton(self._parent)
        self._label.setObjectName("{}Label_{}".format(
            self.OBJECT_NAME_PREFIX, unique_suffix
        ))
        self._label.setStyleSheet(style)
        self._label.setText(self._config["text"])
        self._label.setFocusPolicy(QtCore.Qt.NoFocus)
        self._label.show()

        # Install event filter for resize handling
        self._refresh_filter = _ResizeFilter(self)
        self._parent.installEventFilter(self._refresh_filter)

        self._installed = True
        self._refresh_geometry()

    def uninstall(self):
        """Remove all notification widgets from the viewport."""
        if not self._installed:
            return

        # Remove event filter first
        if self._refresh_filter and self._parent:
            try:
                self._parent.removeEventFilter(self._refresh_filter)
            except RuntimeError:
                pass  # Parent widget was already deleted
        self._refresh_filter = None

        # Clean up buttons
        for direction, btn in self._buttons.items():
            try:
                btn.close()
                btn.deleteLater()
            except RuntimeError:
                pass  # Widget was already deleted
        self._buttons.clear()

        # Clean up label
        if self._label:
            try:
                self._label.close()
                self._label.deleteLater()
            except RuntimeError:
                pass
            self._label = None

        self._installed = False

    def _refresh_geometry(self):
        """Recalculate and apply geometry for all widgets."""
        if not self._installed or not self._parent:
            return

        try:
            width = self._parent.frameSize().width()
            height = self._parent.frameSize().height()
        except RuntimeError:
            return  # Parent was deleted

        margin = self._calculate_margin()
        thickness = self.BORDER_THICKNESS

        # North border (top edge)
        self._buttons["North"].setGeometry(
            margin,
            margin,
            width - (2 * margin),
            thickness
        )

        # East border (right edge)
        self._buttons["East"].setGeometry(
            width - margin - thickness,
            margin,
            thickness,
            height - (2 * margin)
        )

        # South border (bottom edge)
        self._buttons["South"].setGeometry(
            margin,
            height - margin - thickness,
            width - (2 * margin),
            thickness
        )

        # West border (left edge)
        self._buttons["West"].setGeometry(
            margin,
            margin,
            thickness,
            height - (2 * margin)
        )

        # Label (centered at top of this layer's area)
        label_x = (width // 2) - (self.LABEL_WIDTH // 2)
        label_y = margin
        self._label.setGeometry(
            label_x,
            label_y,
            self.LABEL_WIDTH,
            self.LABEL_HEIGHT
        )

        # Ensure widgets are visible and on top
        for btn in self._buttons.values():
            btn.raise_()
        self._label.raise_()

    def update_config(self, config):
        """Update the configuration and refresh appearance."""
        self._config = config
        if self._installed:
            style = self._create_style()
            for btn in self._buttons.values():
                btn.setStyleSheet(style)
            self._label.setStyleSheet(style)
            self._label.setText(config["text"])


class _ResizeFilter(QtCore.QObject):
    """Event filter to handle viewport resize events."""

    def __init__(self, notification_layer):
        super(_ResizeFilter, self).__init__()
        self._layer = notification_layer

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Resize:
            self._layer._refresh_geometry()
        return super(_ResizeFilter, self).eventFilter(obj, event)


# =============================================================================
# Notification Manager (Per-Viewport Stack)
# =============================================================================

class NotificationManager(QtCore.QObject):
    """
    Manages the stack of notifications for a single viewport.

    Handles adding, removing, and reordering notification layers
    to create the nested "Russian doll" effect.
    """

    def __init__(self, panel_name, viewport_widget, config_store):
        """
        Initialize the notification manager.

        Args:
            panel_name (str): Maya panel name (e.g., "modelPanel4")
            viewport_widget (QWidget): The wrapped Qt viewport widget
            config_store (NotificationConfig): Global configuration storage
        """
        super(NotificationManager, self).__init__()

        self._panel_name = panel_name
        self._viewport = viewport_widget
        self._config_store = config_store
        self._layers = []  # Ordered list of NotificationLayer objects
        self._type_to_layer = {}  # Map type_id -> NotificationLayer

    @property
    def panel_name(self):
        return self._panel_name

    def show_notification(self, type_id):
        """
        Show a notification of the given type.

        If the notification is already visible, this does nothing.
        New notifications are added as the innermost layer.

        Args:
            type_id (str): The notification type to show

        Returns:
            bool: True if notification was shown, False otherwise
        """
        # Check if already showing
        if type_id in self._type_to_layer:
            return False

        # Get configuration
        config = self._config_store.get(type_id)
        if not config:
            print("Notifier: Unknown notification type '{}'".format(type_id))
            return False

        if not config["enabled"]:
            return False

        # Create new layer at the next depth
        depth = len(self._layers)
        layer = NotificationLayer(self._viewport, type_id, config, depth)
        layer.install()

        self._layers.append(layer)
        self._type_to_layer[type_id] = layer

        return True

    def hide_notification(self, type_id):
        """
        Hide a notification of the given type.

        Layers inside the removed notification will collapse outward
        to fill the gap.

        Args:
            type_id (str): The notification type to hide

        Returns:
            bool: True if notification was hidden, False otherwise
        """
        if type_id not in self._type_to_layer:
            return False

        layer = self._type_to_layer.pop(type_id)
        removed_depth = layer.depth
        layer.uninstall()

        # Remove from ordered list
        self._layers.remove(layer)

        # Collapse inner layers outward
        for remaining_layer in self._layers[removed_depth:]:
            remaining_layer.depth -= 1

        return True

    def is_showing(self, type_id):
        """Check if a notification type is currently displayed."""
        return type_id in self._type_to_layer

    def refresh_all(self):
        """Refresh all notification layers (e.g., after config change)."""
        for layer in self._layers:
            config = self._config_store.get(layer.type_id)
            if config:
                layer.update_config(config)

    def clear_all(self):
        """Remove all notifications from this viewport."""
        for layer in self._layers:
            layer.uninstall()
        self._layers.clear()
        self._type_to_layer.clear()

    def cleanup(self):
        """Full cleanup when deactivating."""
        self.clear_all()


# =============================================================================
# Viewport Utilities
# =============================================================================

def get_viewport_widget(panel_name):
    """
    Get the Qt widget for a Maya model panel.

    Args:
        panel_name (str): Maya panel name

    Returns:
        QWidget or None: The wrapped viewport widget
    """
    try:
        m3d_view = apiui.M3dView.getM3dViewFromModelPanel(panel_name)
        widget = QtCompat.wrapInstance(int(m3d_view.widget()), QtWidgets.QWidget)
        return widget
    except Exception as e:
        print("Notifier: Could not get viewport for '{}': {}".format(panel_name, e))
        return None


def get_maya_main_window():
    """
    Get Maya's main window as a Qt widget.

    Returns:
        QWidget or None: Maya's main window widget
    """
    try:
        main_window_ptr = omui.MQtUtil.mainWindow()
        return QtCompat.wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    except Exception:
        return None
