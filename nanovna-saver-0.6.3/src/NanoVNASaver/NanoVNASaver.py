#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import contextlib
import sys 
import asyncio
import logging
import sys
import threading
import time
import serial 
import math
#import adafruit_gps
import requests
import webbrowser
from time import strftime, localtime

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QObject, QTimer 
from PyQt6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtGui import QColor, QPixmap

from NanoVNASaver import Defaults
from .Windows import (
#     # AboutWindow,
#     # AnalysisWindow,
#     # CalibrationWindow,
#     # DeviceSettingsWindow,
#     #DisplaySettingsWindow,
    SweepSettingsWindow,
#     TDRWindow,
#     FilesWindow,
)
#from .Controls.MarkerControl import MarkerControl
from .Controls.SweepControl import SweepControl
from .Controls.SerialControl import SerialControl
from .Formatting import format_frequency, format_vswr, format_gain
from .Hardware.Hardware import Interface
from .Hardware.VNA import VNA
from .RFTools import corr_att_data
from .Charts.Chart import Chart
from .Charts import (
    CapacitanceChart,
    CombinedLogMagChart,
    GroupDelayChart,
    InductanceChart,
    LogMagChart,
    PhaseChart,
    MagnitudeChart,
    MagnitudeZChart,
    MagnitudeZShuntChart,
    MagnitudeZSeriesChart,
    QualityFactorChart,
    VSWRChart,
    PermeabilityChart,
    PolarChart,
    RealImaginaryMuChart,
    RealImaginaryZChart,
    RealImaginaryZShuntChart,
    RealImaginaryZSeriesChart,
    SmithChart,
    SParameterChart,
    TDRChart,
)
from .Calibration import Calibration
from .Marker.Widget import Marker
from .Marker.Delta import DeltaMarker
from .SweepWorker import SweepWorker
from .Settings.Bands import BandsModel
from .Settings.Sweep import Sweep
from .Touchstone import Touchstone
from .About import version


##########################################
# GPS Module 
##########################################

# Global variables to store lat and lng
latest_latitude = None
latest_longitude = None

scan_count = 0
scan_data = {
    'Number': [],
    'Evaluation': [],
    'Latitude': [],
    'Longitude': []
}

# Constantly read GPS data
# async def gps_worker():
#     global latest_latitude, latest_longitude
#     # Function that writes GPS data to gps_data.txt
#     # Create a serial connection for the GPS connection using default speed
#     uart = serial.Serial("/dev/serial0", baudrate=9600, timeout=3000)

#     # Create a GPS module instance.
#     gps = adafruit_gps.GPS(uart, debug=False)
#     # Use UART/pyserial

#     gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
#     gps.send_command(b"PMTK220,1000")

#     # Main loop runs forever printing the location, etc. every second.
#     last_print = time.monotonic()
#     while True:
#         # Make sure to call gps.update() every loop iteration and at least twice
#         # as fast as data comes from the GPS unit (usually every second).
#         # This returns a bool that's true if it parsed new data (you can ignore it
#         # though if you don't care and instead look at the has_fix property).
#         gps.update()
#         # Every second save current location details to global variables if there's a fix.
#         current = time.monotonic()
#         if current - last_print >= 1.0:
#             last_print = current
#             if gps.has_fix:
#                 latest_latitude = gps.latitude
#                 latest_longitude = gps.longitude
#                 print("=" * 40)  # Print a separator line.
#                 print("Fix timestamp: {}/{}/{} {:02}:{:02}:{:02}".format(
#                     gps.timestamp_utc.tm_mon,  # Grab parts of the time from the
#                     gps.timestamp_utc.tm_mday,  # struct_time object that holds
#                     gps.timestamp_utc.tm_year,  # the fix time.  Note you might
#                     gps.timestamp_utc.tm_hour,  # not get all data like year, day,
#                     gps.timestamp_utc.tm_min,  # month!
#                     gps.timestamp_utc.tm_sec,
#                 ))
#                 print("Latitude: {0:.6f} degrees".format(gps.latitude))
#                 print("Longitude: {0:.6f} degrees".format(gps.longitude))
#                 print("Precise Latitude: {:.0f}.{:04.4f} degrees".format(
#                     gps.latitude_degrees, gps.latitude_minutes
#                 ))
#                 print("Precise Longitude: {:.0f}.{:04.4f} degrees".format(
#                     gps.longitude_degrees, gps.longitude_minutes
#                 ))
#             else:
#                 print("Waiting for fix...")
#         await asyncio.sleep(1)


logger = logging.getLogger(__name__)

###########################################
# Export Map data to web browser 
###########################################

def export_data_to_map():
        #step 1, login and return the session ID

        def login(email, password):
            print("attempting login....")
            url = "https://maps.co/api/userLogIn"
            data = {
                "userEmail": email,
                "userPassword": password
            }

            try:
                response = requests.post(url, json=data)
                print("response content:", response.content)
                response_json = response.json()
                
                if response_json.get("success") == 1:
                    session_id = response_json["USER"]["sessionID"]
                    print("Login successful. Session ID:", session_id)
                    return session_id
                else:
                    print("Login failed:", response_json.get("message"))
                    return None
            except Exception as e:
                print("An error occurred during login:", e)
                return None

        session_id = login("aaronearl7@gmail.com", "ae030456")
        print("Session ID:", session_id)


        #step 2, function to get the layers 

        def get_layers(session_id):
            print("Getting list of layers....")
            url = "https://maps.co/api/userGetLayers"
            headers = {
                "Cookie": f"sessionID={session_id}"
            }

            try:
                response = requests.get(url, headers=headers)
                print("response content:", response.content)
                response_json = response.json()
                
                if response_json.get("success") == 1:
                    layers = response_json.get("Layers", {})
                    print("List of layers:", layers)
                    return layers
                else:
                    print("Failed to get list of layers:", response_json.get("message"))
                    return None
            except Exception as e:
                print("An error occurred while getting list of layers:", e)
                return None

        session_id = "65e20dc1411db070603766ige33a641"
        layers = get_layers(session_id)


        #step 3, Manually add locations to layer 

        def add_location_to_layer(session_id, layer_id, layer_name, latitude, longitude):
            print("Adding location to layer....")
            url = "https://maps.co/api/layerLocationAdd"
            data = {
                "layerID": layer_id,
                "layerName": layer_name,
                "lat": latitude,
                "lng": longitude
            }
            headers = {
                "Cookie": f"sessionID={session_id}"
            }

            try:
                response = requests.post(url, json=data, headers=headers)
                print("Response content:", response.content)
                response_json = response.json()

                if response_json.get("success") == 1:
                    print("Location added successfully to layer.")
                else:
                    print("Failed to add location to layer:", response_json.get("message"))
            except Exception as e:
                print("An error occurred while adding location to layer:", e)

        #Usage  - Set to continuously read the data from the data table 

        session_id = "65e20dc1411db070603766ige33a641"
        layer_id = "65e2139f6e47e308984963abz393654"
        layer_name = "rasp_pi gps test v.1"

        #Map the same data displayed to the data table 
        for index in range(len(scan_data['Number'])):
            latitude = scan_data['Latitude'][index]
            longitude = scan_data['Longitude'][index]

        #Call the function to add data to map layer 
        add_location_to_layer(session_id, layer_id, layer_name, latitude, longitude)


        url = "https://maps.co/gis/"
        webbrowser.open(url) 


class Communicate(QObject):
    data_available = QtCore.pyqtSignal()


class NanoVNASaver(QWidget):
    version = version
    scaleFactor = 1

    def __init__(self):
        super().__init__()
        self.communicate = Communicate()
        self.s21att = 0.0
        if getattr(sys, "frozen", False):
            logger.debug("Running from pyinstaller bundle")
            self.icon = QtGui.QIcon(
                f"{sys._MEIPASS}/icon_48x48.png"
            )  # pylint: disable=no-member
        else:
            self.icon = QtGui.QIcon("icon_48x48.png")
        self.setWindowIcon(self.icon)
        self.settings = Defaults.AppSettings(
            QtCore.QSettings.Format.IniFormat,
            QtCore.QSettings.Scope.UserScope,
            "NanoVNASaver",
            "NanoVNASaver",
        )
        logger.info("Settings from: %s", self.settings.fileName())
        #Defaults.cfg = Defaults.restore(self.settings)
        self.threadpool = QtCore.QThreadPool()
        self.sweep = Sweep()
        self.worker = SweepWorker(self)

        self.worker.signals.updated.connect(self.dataUpdated)
        self.worker.signals.finished.connect(self.sweepFinished)
        self.worker.signals.sweepError.connect(self.showSweepError)

        self.markers = []
        self.marker_ref = False

        self.marker_column = QtWidgets.QVBoxLayout()
        self.marker_frame = QtWidgets.QFrame()
        self.marker_column.setContentsMargins(0, 0, 0, 0)
        self.marker_frame.setLayout(self.marker_column)

        self.sweep_control = SweepControl(self)
        #self.marker_control = MarkerControl(self)
        self.serial_control = SerialControl(self)

        self.bands = BandsModel()

        self.interface = Interface("serial", "None")
        self.vna = VNA(self.interface)

        self.dataLock = threading.Lock()
        self.data = Touchstone()
        self.ref_data = Touchstone()

        self.sweepSource = ""
        self.referenceSource = ""

        self.calibration = Calibration()

        logger.debug("Building user interface")

        self.baseTitle = f"Corn Stalk Integration Device "
        self.updateTitle()
        layout = QtWidgets.QBoxLayout(
            QtWidgets.QBoxLayout.Direction.LeftToRight
        )

        scrollarea = QtWidgets.QScrollArea()
        outer = QtWidgets.QVBoxLayout()
        outer.addWidget(scrollarea)
        self.setLayout(outer)
        scrollarea.setWidgetResizable(True)
        self.resize(
            Defaults.cfg.gui.window_width, Defaults.cfg.gui.window_height
        )
        scrollarea.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )
        widget = QWidget()
        widget.setLayout(layout)
        scrollarea.setWidget(widget)

        self.charts = {
            "s21": {
                "log_mag": LogMagChart("S21 Gain"),
            },
            "combined": {
                "log_mag": CombinedLogMagChart("S11 & S21 LogMag"),
            },
        }
        self.tdr_chart = TDRChart("TDR")
        self.tdr_mainwindow_chart = TDRChart("TDR")

        #List of all the S21 charts, for selecting
        self.s21charts = list(self.charts["s21"].values())

        # List of all charts that use both S11 and S21
        self.combinedCharts = list(self.charts["combined"].values())

        # List of all charts that can be selected for display
        self.selectable_charts = (
            self.s21charts
        )

        # List of all charts that subscribe to updates (including duplicates!)
        self.subscribing_charts = []
        self.subscribing_charts.extend(self.selectable_charts)
        self.subscribing_charts.append(self.tdr_chart)

        self.charts_layout = QtWidgets.QGridLayout()


        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, self.close)

        ###############################################################
        #  Create main layout
        ###############################################################

        left_column = QtWidgets.QVBoxLayout()
        right_column = QtWidgets.QVBoxLayout()
        #right_column.addLayout(self.charts_layout)
        # self.marker_frame.setHidden(Defaults.cfg.gui.markers_hidden)
        chart_widget = QWidget()
        chart_widget.setLayout(right_column)
        self.splitter = QtWidgets.QSplitter()
        self.splitter.addWidget(self.marker_frame)
        self.splitter.addWidget(chart_widget)

        self.splitter.restoreState(Defaults.cfg.gui.splitter_sizes)

        layout.addLayout(left_column)
        layout.addWidget(self.splitter, 1)

        ###############################################################
        #  Windows
        ###############################################################

        self.windows = {
            "sweep_settings": SweepSettingsWindow(self),
            # "setup": DisplaySettingsWindow(self),
        }


        ##############################
        #image
        ##############################
        image_label = QLabel()
        image_path = r"C:\Users\aaron\OneDrive\Documents\TTO Work\CornStalk Software with NanoVNA\nanovna-saver-0.6.3\src\NanoVNASaver\channels4_profile.jpg"
        image = QPixmap(image_path)
        width = 100
        height = 100
        image = image.scaled(width, height)

        # Load the image file (replace 'path_to_your_image.png' with the actual path to your image file)
        image_label.setPixmap(image)

        # Add the image label to the layout
        left_column.addWidget(image_label)

        # Add a spacer item to create some space between the image and the other widgets
        left_column.addSpacerItem(
           QtWidgets.QSpacerItem(
               1,
               1,
               QtWidgets.QSizePolicy.Policy.Fixed,
               QtWidgets.QSizePolicy.Policy.Expanding,
           )
        )

        ###############################################################
        #  Sweep control
        ###############################################################

        left_column.addWidget(self.sweep_control)

        ###############################################################
        #  Spacer
        ###############################################################

        left_column.addSpacerItem(
            QtWidgets.QSpacerItem(
                1,
                1,
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )
        )

        ###############################################################
        #  Serial control
        ###############################################################

        left_column.addWidget(self.serial_control)

        ###############################################################
        #  Statistics/analysis
        ###############################################################

        s11_control_box = QtWidgets.QGroupBox()
        s11_control_box.setTitle("S11")
        s11_control_layout = QtWidgets.QFormLayout()
        s11_control_layout.setVerticalSpacing(0)
        #s11_control_box.setLayout(s11_control_layout)

        self.s11_min_swr_label = QtWidgets.QLabel()
        s11_control_layout.addRow("Min VSWR:", self.s11_min_swr_label)
        self.s11_min_rl_label = QtWidgets.QLabel()
        s11_control_layout.addRow("Return loss:", self.s11_min_rl_label)

        # self.marker_column.addWidget(s11_control_box)

        s21_control_box = QtWidgets.QGroupBox()
        s21_control_box.setTitle("S21")
        s21_control_layout = QtWidgets.QFormLayout()
        s21_control_layout.setVerticalSpacing(0)
        s21_control_box.setLayout(s21_control_layout)

        self.s21_min_gain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Min gain:", self.s21_min_gain_label)

        self.s21_max_gain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Max gain:", self.s21_max_gain_label)

        self.marker_column.addWidget(s21_control_box)


        ###############################################################
        # GPS labels 
        ###############################################################

        # self.latitude_label = QLabel("Latitude:")
        # self.longitude_label = QLabel("Longitude:")
        # right_column.addWidget(self.latitude_label)
        # right_column.addWidget(self.longitude_label)

        ###############################################################
        #   Data Table 
        ###############################################################

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(['Scan Number', 'Evaluation', 'Latitude', 'Longitude'])
        self.marker_column.addWidget(self.data_table)

        #Initialize data
        self.scan_data = {
            'Number': [],
            'Evaluation': [],
            'Latitude': [],
            'Longitude': []
        }
        self.scan_count = 0

        ###############################################################
        # Buttons 
        ###############################################################

        self.export_button = QPushButton("Export Data to Map")
        self.export_button.clicked.connect(export_data_to_map)

        self.marker_column.addWidget(self.export_button)

    def auto_connect(self):  # connect if there is exactly one detected serial device
        if self.serial_control.inp_port.count() == 1:
            self.serial_control.connect_device()

    def _sweep_control(self, start: bool = True) -> None:
        self.sweep_control.progress_bar.setValue(0 if start else 100)
        self.sweep_control.btn_start.setDisabled(start)
        self.sweep_control.btn_stop.setDisabled(not start)
        self.sweep_control.toggle_settings(start)

    def sweep_start(self):
        # Run the device data update
        if not self.vna.connected():
            return
        self.worker.stopped = False

        self._sweep_control(start=True)

        for m in self.markers:
            m.resetLabels()
        # self.s11_min_rl_label.setText("")
        # self.s11_min_swr_label.setText("")
        self.s21_min_gain_label.setText("")
        self.s21_max_gain_label.setText("")
        #self.tdr_result_label.setText("")

        self.settings.setValue("Segments", self.sweep_control.get_segments())

        logger.debug("Starting worker thread")
        self.threadpool.start(self.worker)
        self.scan_count += 1

    def sweep_stop(self):
        self.worker.stopped = True

    def saveData(self, data, data21, source=None):
        with self.dataLock:
            self.data.s11 = data
            self.data.s21 = data21
            if self.s21att > 0:
                self.data.s21 = corr_att_data(self.data.s21, self.s21att)
        if source is not None:
            self.sweepSource = source
        else:
            time = strftime('%Y-%m-%d %H:%M:%S', localtime())
            name = self.sweep.properties.name or 'nanovna'
            self.sweepSource = f'{name}_{time}'    

    # def markerUpdated(self, marker: Marker):
    #     with self.dataLock:
    #         marker.findLocation(self.data.s11)
    #         marker.resetLabels()
    #         marker.updateLabels(self.data.s11, self.data.s21)
    #         for c in self.subscribing_charts:
    #             c.update()
    #     if not self.delta_marker_layout.isHidden():
    #         m1 = self.markers[0]
    #         m2 = None
    #         if self.marker_ref:
    #             if self.ref_data:
    #                 m2 = Marker("Reference")
    #                 m2.location = self.markers[0].location
    #                 m2.resetLabels()
    #                 m2.updateLabels(self.ref_data.s11, self.ref_data.s21)
    #             else:
    #                 logger.warning("No reference data for marker")

    #         elif Marker.count() >= 2:
    #             m2 = self.markers[1]

    #         if m2 is None:
    #             logger.error("No data for delta, missing marker or reference")
    #         else:
    #             self.delta_marker.set_markers(m1, m2)
    #             self.delta_marker.resetLabels()
    #             with contextlib.suppress(IndexError):
    #                 self.delta_marker.updateLabels()


    def dataUpdated(self):
        with self.dataLock:
            s11 = self.data.s11[:]
            s21 = self.data.s21[:]

        for m in self.markers:
            m.resetLabels()
            m.updateLabels(s11, s21)

        # for c in self.s11charts:
        #     c.setData(s11)

        for c in self.s21charts:
            c.setData(s21)

        for c in self.combinedCharts:
            c.setCombinedData(s11, s21)

        self.sweep_control.progress_bar.setValue(int(self.worker.percentage))
        # self.windows["tdr"].updateTDR()

        if s11:
            min_vswr = min(s11, key=lambda data: data.vswr)
            self.s11_min_swr_label.setText(
                f"{format_vswr(min_vswr.vswr)} @"
                f" {format_frequency(min_vswr.freq)}"
            )
            self.s11_min_rl_label.setText(format_gain(min_vswr.gain))
        else:
            self.s11_min_swr_label.setText("")
            self.s11_min_rl_label.setText("")

        if s21:
            min_gain = min(s21, key=lambda data: data.gain)
            max_gain = max(s21, key=lambda data: data.gain)
            self.s21_min_gain_label.setText(
                f"{format_gain(min_gain.gain)}"
                f" @ {format_frequency(min_gain.freq)}"
            )
            self.s21_max_gain_label.setText(
                f"{format_gain(max_gain.gain)}"
                f" @ {format_frequency(max_gain.freq)}"
            )
        else:
            self.s21_min_gain_label.setText("")
            self.s21_max_gain_label.setText("")

        self.updateTitle()
        self.communicate.data_available.emit()
        # self.update_logged_data_table(s21)


    def sweepFinished(self):
        self._sweep_control(start=False)

        for marker in self.markers:
            marker.frequencyInput.textEdited.emit(marker.frequencyInput.text())
        
        with self.dataLock:
            s11 = self.data.s11[:]
            s21 = self.data.s21[:]

        min_gain = min(s21, key=lambda data: data.gain)
        max_gain = max(s21, key=lambda data: data.gain)
        self.log(min_gain, max_gain)

    def setReference(self, s11=None, s21=None, source=None):
        if not s11:
            with self.dataLock:
                s11 = self.data.s11[:]
                s21 = self.data.s21[:]

        self.ref_data.s11 = s11
        for c in self.s11charts:
            c.setReference(s11)

        self.ref_data.s21 = s21
        for c in self.s21charts:
            c.setReference(s21)

        for c in self.combinedCharts:
            c.setCombinedReference(s11, s21)

        self.btnResetReference.setDisabled(False)

        self.referenceSource = source or self.sweepSource
        self.updateTitle()

    def updateTitle(self):
        insert = "("
        if self.sweepSource != "":
            insert += (
                f"Sweep: {self.sweepSource} @ {len(self.data.s11)} points"
                f"{', ' if self.referenceSource else ''}"
            )
        if self.referenceSource != "":
            insert += (
                f"Reference: {self.referenceSource} @"
                f" {len(self.ref_data.s11)} points"
            )
        insert += ")"
        title = f"{self.baseTitle} {insert or ''}"
        self.setWindowTitle(title)

    def resetReference(self):
        self.ref_data = Touchstone()
        self.referenceSource = ""
        self.updateTitle()
        for c in self.subscribing_charts:
            c.resetReference()
        self.btnResetReference.setDisabled(True)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(800, 450)

    def display_window(self, name):
        self.windows[name].show()
        QtWidgets.QApplication.setActiveWindow(self.windows[name])

    def showError(self, text):
        QtWidgets.QMessageBox.warning(self, "Error", text)

    def showSweepError(self):
        self.showError(self.worker.error_message)
        with contextlib.suppress(IOError):
            self.vna.flushSerialBuffers()  # Remove any left-over data
            self.vna.reconnect()  # try reconnection
        self.sweepFinished()


    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.worker.stopped = True
        for marker in self.markers:
            marker.update_settings()
        self.settings.sync()
        self.bands.saveSettings()
        self.threadpool.waitForDone(2500)

        # Defaults.cfg.chart.marker_count = Marker.count()
        Defaults.cfg.gui.window_width = self.width()
        Defaults.cfg.gui.window_height = self.height()
        Defaults.cfg.gui.splitter_sizes = self.splitter.saveState()
        Defaults.store(self.settings, Defaults.cfg)

        a0.accept()
        sys.exit()

    def changeFont(self, font: QtGui.QFont) -> None:
        qf_new = QtGui.QFontMetricsF(font)
        normal_font = QtGui.QFont(font)
        normal_font.setPointSize(8)
        qf_normal = QtGui.QFontMetricsF(normal_font)
        # Characters we would normally display
        standard_string = "0.123456789 0.123456789 MHz \N{OHM SIGN}"
        new_width = qf_new.horizontalAdvance(standard_string)
        old_width = qf_normal.horizontalAdvance(standard_string)
        self.scaleFactor = new_width / old_width
        logger.debug(
            "New font width: %f, normal font: %f, factor: %f",
            new_width,
            old_width,
            self.scaleFactor,
        )
        # TODO: Update all the fixed widths to account for the scaling
        for m in self.markers:
            m.get_data_layout().setFont(font)
            m.setScale(self.scaleFactor)

    def update_sweep_title(self):
        for c in self.subscribing_charts:
            c.setSweepTitle(self.sweep.properties.name)




    #######################
    # Data table functions 
    #######################

      #Data evaluation and log to table 

    def evaluate(self, min_gain, max_gain): 
        min_gain_value = min_gain.gain
        max_gain_value = max_gain.gain
        data_average = abs(min_gain_value + max_gain_value) / 2
        if data_average < 50: 
            evaluation = "Water detected"
            color = QColor("green")
        else: 
            evaluation = "No water detected"
            color = QColor("red")

        color_item = QTableWidgetItem(evaluation) 
        color_item.setForeground(color)       
        return color_item 
    

    def log(self, min_gain, max_gain): 
        material_evaluation = self.evaluate(min_gain, max_gain)
        new_scan = {
            'Number': self.scan_count,
            'Evaluation': material_evaluation,  # You need to implement `evaluate()` function
            'Latitude': latest_latitude,    # Make sure `latest_latitude` and `latest_longitude` are accessible
            'Longitude': latest_longitude
        }
        for key, value in new_scan.items():
            self.scan_data[key].append(value)
        self.display_table()
    
    def display_table(self):
       self.data_table.setRowCount(len(self.scan_data['Number']))
       for index in range(len(self.scan_data['Number'])):
            scan_number = self.scan_data['Number'][index]
            evaluation = self.scan_data['Evaluation'][index]
            latitude = self.scan_data['Latitude'][index]
            longitude = self.scan_data['Longitude'][index]
            if latitude is not None and longitude is not None:
                latitude_str = "{:.6f}".format(latitude)
                longitude_str = "{:.6f}".format(longitude)
            else: 
                latitude_str = "N/A"
                longitude_str = "N/A"  

            self.data_table.setItem(index, 0, QTableWidgetItem(str(scan_number)))
            self.data_table.setItem(index, 1, QTableWidgetItem(evaluation))
            self.data_table.setItem(index, 2, QTableWidgetItem(latitude_str))
            self.data_table.setItem(index, 3, QTableWidgetItem(longitude_str))
    
    #gather data from the table 
    def gather_data_to_export():
       data_to_export = []
       for index in range(len(scan_data['Number'])):
           latitude = scan_data['Latitude'][index]
           longitude = scan_data['Longitude'][index]
           data_to_export.append((latitude, longitude))
       export_data_to_map(data_to_export)   

    # def start_gps_worker(self):
    #     asyncio.run(gps_worker())



     
    


       