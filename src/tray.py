"""wxPython system tray icon.

Shows the port the API is running on. Printer selection is handled entirely
through the API (`GET/POST /printers...`), so the tray only displays status and
lets the user quit the app.
"""
import webbrowser

import wx
import wx.adv

from src.config import TRAY_ICON, TRAY_TOOLTIP, FLASK_PORT

HEALTH_URL = f'http://localhost:{FLASK_PORT}/health'


def create_menu_item(menu, label, func, kind=wx.ITEM_NORMAL):
    item = wx.MenuItem(menu, -1, label, kind=kind)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item


class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame=None):
        super(TaskBarIcon, self).__init__()
        # Hidden anchor frame: on macOS the MainLoop exits immediately if there
        # is no top-level window to keep it running.
        self._frame = frame
        self.set_icon(TRAY_ICON)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        # Non-clickable status line showing where the API is running.
        status_item = create_menu_item(
            menu, f'Corriendo en http://localhost:{FLASK_PORT}', self.on_noop
        )
        status_item.Enable(False)

        menu.AppendSeparator()
        create_menu_item(menu, 'Ver estado', self.on_open_health)
        create_menu_item(menu, 'Salir', self.on_exit)
        return menu

    def set_icon(self, path):
        # The bundled app icon is full resolution (~1254px). The macOS menu bar
        # is ~22pt tall and does NOT scale the bitmap for us, so a giant image
        # renders blank/invisible. Scale it down to menu-bar/tray size first.
        img = wx.Image(path, wx.BITMAP_TYPE_PNG)
        size = 22
        img = img.Scale(size, size, wx.IMAGE_QUALITY_HIGH)
        icon = wx.Icon(wx.Bitmap(img))
        self.SetIcon(icon, f'{TRAY_TOOLTIP} — puerto {FLASK_PORT}')

    def on_left_down(self, event):
        self.open_health()

    def on_open_health(self, event):
        self.open_health()

    def open_health(self):
        """Open the API health endpoint in the default browser."""
        webbrowser.open(HEALTH_URL)

    def on_noop(self, event):
        pass

    def on_exit(self, event):
        wx.CallAfter(self.Destroy)
        # Closing the anchor frame ends the MainLoop and stops the process.
        if self._frame is not None:
            wx.CallAfter(self._frame.Close)


def start_tray():
    """Start the wxPython tray icon event loop (runs on the main thread)."""
    app = wx.App(False)
    # Created but never Show()n -> invisible window that keeps MainLoop alive.
    frame = wx.Frame(None, title=TRAY_TOOLTIP)
    TaskBarIcon(frame)
    app.MainLoop()
