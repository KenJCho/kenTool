"""Minimal GUI smoke test — captures any exceptions from the event loop."""
import sys, traceback, os

os.chdir(r"c:\01_coding\kenTool")
sys.path.insert(0, r"c:\01_coding\kenTool")

def excepthook(exc_type, exc_value, exc_tb):
    print("UNCAUGHT EXCEPTION:")
    traceback.print_exception(exc_type, exc_value, exc_tb)
sys.excepthook = excepthook

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import matplotlib
matplotlib.use("Qt5Agg")

app = QApplication.instance() or QApplication(sys.argv)

try:
    import sdof_gui
    print("sdof_gui imported, _QT =", sdof_gui._QT)
    win = sdof_gui.MainWindow()
    print("MainWindow created")
    win.show()
    print("win.show() called")
    QTimer.singleShot(3000, app.quit)
    ret = app.exec_()
    print("exec_ returned:", ret)
except Exception:
    traceback.print_exc()
