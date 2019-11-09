# Imports -------------------------------------------------------------------- #

from maya import cmds, mel
import maya.api.OpenMaya as api
import maya.api.OpenMayaUI as apiui
from Qt import QtCore, QtGui, QtWidgets, QtCompat, __binding__

if "PyQt" in __binding__:
    import sip
elif "PySide" == __binding__:
    import shiboken as shiboken  # Do Pyside
elif "PySide2" == __binding__:
    import shiboken2 as shiboken # You're on Maya 2018, aren't you?

#------------------------------------------------------------------------------#
# GLOBALS
#------------------------------------------------------------------------------#

_Notifications = {}
_AutokeyScriptJob = []

#------------------------------------------------------------------------------#
# Class
#------------------------------------------------------------------------------#

# class Notification(MayaQWidgetBaseMixin, QtWidgets.QLabel): # Old method
class Notification(QtWidgets.QWidget):
    """ Will draw a border around any widget you give it """
    def __init__(self, parent):
        super(Notification, self).__init__(parent)
        #QtWidgets.QLabel.__init__(self)
        self.setParent(parent)
        self._parent = parent
        self.debug = False
        self.border_thickness = 6
        self.button_width = 100
        self.button_height = 16
        self.buttonText = "Autokey is OFF"
        self.callbacks = None # Will use this for the button press one day
        self.labels  = {'Label': None}
        self.buttons = {'North': None,
                        'East' : None,
                        'South': None,
                        'West' : None}
        self.button_style = """
                            background: rgb(255, 20, 60);
                            border: 0px;
                            text-align: center;
                            color: white;
                            font-weight: bold;
                            """
        self.refresh_filter = RefreshFilter(self) # How QT handles events

    def _install_buttons(self):
        for btn in self.buttons:
            self.buttons[btn] = QtWidgets.QPushButton(self._parent)
            self.buttons[btn].setStyleSheet(self.button_style)
            self.buttons[btn].show()
        for lbl in self.labels:
            self.labels[lbl] = QtWidgets.QPushButton(self._parent)
            self.labels[lbl].setStyleSheet(self.button_style)
            self.labels[lbl].setText(self.buttonText)
            self.labels[lbl].show()
        self._refresh_buttons()

    def _uninstall_buttons(self):
        # I get key errors every time this runs. Is this being triggered
        # every time a button is deleted?
        for btn in self.buttons:
            try:
                self.buttons[btn].close()
                self.buttons[btn].deleteLater()
            except:
                pass
        for lbl in self.labels:
            try:
                self.labels[lbl].close()
                self.labels[lbl].deleteLater()
            except:
                pass
        # self.buttons = {} # Do I need this?

    def _refresh_buttons(self):
        self.buttons['North'].setGeometry(0,
                                          0,
                                          self._parent.frameSize().width(),
                                          self.border_thickness)
        self.buttons['East'].setGeometry( self._parent.frameSize().width() - \
                                          self.border_thickness,
                                          0,
                                          self.border_thickness,
                                          self._parent.frameSize().height())
        self.buttons['South'].setGeometry(0,
                                          self._parent.frameSize().height() - \
                                          self.border_thickness,
                                          self._parent.frameSize().width(),
                                          self.border_thickness)
        self.buttons['West'].setGeometry( 0,
                                          0,
                                          self.border_thickness,
                                          self._parent.frameSize().height())
        self.labels['Label'].setGeometry( self._parent.frameSize().width()/2 - \
                                          self.button_width/2,
                                          0,
                                          self.button_width,
                                          self.button_height)

    def activate(self):
        self._install_buttons()
        self._parent.installEventFilter(self.refresh_filter)

    def closeEvent(self, event):
        self._uninstall_buttons()
        self._parent.removeEventFilter(self.refresh_filter)


class RefreshFilter(QtCore.QObject):
    """
    This class is the callback for refreshing the QT geometry
    """
    def __init__(self, parent):
        super(RefreshFilter, self).__init__()
        self._parent = parent

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Resize:
            self._parent._refresh_buttons()
        return QtCore.QObject.eventFilter(self, obj, event)

#------------------------------------------------------------------------------#
# Executions
#------------------------------------------------------------------------------#

def activate():
    global _AutokeyScriptJob
    if _AutokeyScriptJob:
        print "Notifier already running!"
        return
    _ScriptJobOFF = cmds.scriptJob(ct=["autoKeyframeState", _notificationsOFF])
    _AutokeyScriptJob.append(_ScriptJobOFF)
    _ScriptJobON  = cmds.scriptJob(cf=["autoKeyframeState", _notificationsON])
    _AutokeyScriptJob.append(_ScriptJobON)
    api.MGlobal.displayWarning("AutoKey notifications enabled!")

def deactivate():
    global _AutokeyScriptJob
    try: # Remove the current notifications
        _notificationsOFF()
    except:
        print "No running scriptjobs detected."
    try:
        for job in _AutokeyScriptJob:
            try:
                cmds.scriptJob(kill=job)
            except:
                print "Could not kill %s." % job
    except:
        print "Could not kill scriptJobs."
    _AutokeyScriptJob = []
    api.MGlobal.displayWarning("AutoKey notifications disabled!")

#------------------------------------------------------------------------------#
# Functions
#------------------------------------------------------------------------------#

def _notificationsON(overrideText = None):
    # if cmds.autoKeyframe(state=True, query=True): # Just checking...
    #     print "AutoKey is on. No notifications needed."
    #     return

    global _Notifications
    if _Notifications:
        return  # Bounce if they are already on

    # Get the panels
    panels = cmds.getPanel(type='modelPanel')
    for panel in panels:
        try:
            # Get the m3dview
            apiPanel = apiui.M3dView.getM3dViewFromModelPanel(panel)
            # Wrap it
            try:
                widget = QtCompat.wrapInstance(apiPanel.widget(), QtWidgets.QWidget)
            except:
                print "Something went wrong with the wrapper."
                pass
            # Instance a dknotification on it
            notification = Notification(widget)

            if overrideText:
                notification.buttonText = overrideText
            # Show it
            notification.activate()

            # Store it
            _Notifications[panel] = [apiPanel, notification]
        except:
            print "%s does not have an M3dView." % panel
            pass

def _notificationsOFF():
    # if cmds.autoKeyframe(state=False, query=True): # Just checking...
    #     print "AutoKey is off. Leaving notifications on."
    #     return

    global _Notifications
    # print "Disabling notifications..."
    # Delete the notes
    for panel in _Notifications.keys():
        try:
            _Notifications[panel][1].close()
            _Notifications[panel][1].deleteLater()
            del _Notifications[panel]
            # print "%s disabled" % panel
        except:
            del _Notifications[panel]
            print "%s no longer exists."
            pass
    # print "Notifications off!"

# EoF
