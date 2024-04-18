import logging
import sys
from PyQt6 import QtWidgets, QtCore, QtGui

from NanoVNASaver import Defaults
from .Controls.SweepControl import SweepControl
from .Hardware.Hardware import Interface
from .Hardware.VNA import VNA
from .Touchstone import Touchstone
from .Charts.Chart import Chart
from .Charts import LogMagChart

logger = logging.getLogger(__name__)

class Communicate(QtCore.QObject):
    data_available = QtCore.pyqtSignal()

class NanoVNASaver(QtWidgets.QWidget):
    scaleFactor = 1

    def __init__(self):
        super().__init__()
        self.communicate = Communicate()
        if getattr(sys, "frozen", False):
            self.icon = QtGui.QIcon(f"{sys._MEIPASS}/icon_48x48.png")
        else:
            self.icon = QtGui.QIcon("icon_48x48.png")
        self.setWindowIcon(self.icon)
        self.settings = Defaults.AppSettings(
            QtCore.QSettings.Format.IniFormat,
            QtCore.QSettings.Scope.UserScope,
            "NanoVNASaver",
            "NanoVNASaver",
        )
        Defaults.cfg = Defaults.restore(self.settings)
        self.sweep_control = SweepControl(self)
        self.interface = Interface("serial", "None")
        self.vna = VNA(self.interface)
        self.data = Touchstone()
        self.threadpool = QtCore.QThreadPool()
        self.worker = SweepWorker(self)

        # Set up chart for viewing
        self.chart = LogMagChart("LogMag")
        self.chart_layout = QtWidgets.QVBoxLayout()
        self.chart_layout.addWidget(self.chart)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.sweep_control)
        layout.addLayout(self.chart_layout)
        self.setLayout(layout)

        self.worker.signals.updated.connect(self.dataUpdated)
        self.worker.signals.finished.connect(self.sweepFinished)
        self.worker.signals.sweepError.connect(self.showSweepError)

    def sweep_start(self):
        if not self.vna.connected():
            return
        self.threadpool.start(self.worker)

    def dataUpdated(self):
        with self.dataLock:
            s11 = self.data.s11[:]
            s21 = self.data.s21[:]

        self.chart.setData(s11)

    def sweepFinished(self):
        pass

    def showSweepError(self):
        pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = NanoVNASaver()
    window.show()
    sys.exit(app.exec())