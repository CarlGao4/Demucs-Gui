LICENSE = """Demucs-GUI 1.0
Copyright (C) 2022-2023  Carl Gao, Jize Guo, Rosario S.E.

This program is free software: you can redistribute it and/or modify \
it under the terms of the GNU General Public License as published by \
the Free Software Foundation, either version 3 of the License, or \
(at your option) any later version.

This program is distributed in the hope that it will be useful, \
but WITHOUT ANY WARRANTY; without even the implied warranty of \
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the \
GNU General Public License for more details.

You should have received a copy of the GNU General Public License \
along with this program.  If not, see <https://www.gnu.org/licenses/>."""

__version__ = "1.1a1"

import shared

if not shared.use_PyQt6:
    from PySide6 import QtGui
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QButtonGroup,
        QComboBox,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMenu,
        QMenuBar,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QRadioButton,
        QSlider,
        QSpinBox,
        QStatusBar,
        QStyleFactory,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
else:
    from PyQt6 import QtGui  # type: ignore
    from PyQt6.QtCore import Qt, QTimer  # type: ignore
    from PyQt6.QtCore import pyqtSignal as Signal  # type: ignore
    from PyQt6.QtWidgets import (  # type: ignore
        QAbstractItemView,
        QApplication,
        QButtonGroup,
        QComboBox,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMenu,
        QMenuBar,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QRadioButton,
        QSlider,
        QSpinBox,
        QStatusBar,
        QStyleFactory,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

import datetime
import logging
import logging.handlers
import os
import pathlib
import platform
import psutil
import random
import shlex
import sys
import threading
import time
import traceback
import webbrowser

import separator
from PySide6_modified import Action, ModifiedQLabel, ProgressDelegate


class StartingWindow(QMainWindow):
    finish_sgn = Signal(float)

    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.opacity = 0
        self.setWindowOpacity(self.opacity)
        self.setWindowTitle("Demucs GUI %s" % __version__)
        self.timer = QTimer()

        self.pic = QtGui.QPixmap("./icon/starting.png")
        size = self.pic.size()
        size.setHeight(int(size.height() * 0.7))
        size.setWidth(int(size.width() * 0.7))
        self.label = QLabel(self)
        self.label.setScaledContents(True)
        self.label.setGeometry(0, 0, size.width(), size.height())
        screensize = QApplication.primaryScreen().geometry()
        self.setGeometry(
            (screensize.width() - size.width()) // 2,
            (screensize.height() - size.height()) // 2,
            size.width(),
            size.height(),
        )
        self.setFixedSize(size.width(), size.height())
        self.setWindowIcon(QtGui.QIcon("./icon/icon.ico"))
        self.label.setPixmap(self.pic)

        fontpath = pathlib.Path("./fonts/Montserrat-Bold.ttf").resolve()
        self.status_font_id = QtGui.QFontDatabase.addApplicationFont(str(fontpath))
        families = QtGui.QFontDatabase.applicationFontFamilies(self.status_font_id)

        self.status = QLabel(self)
        self.status.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.status.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.status.setText("Starting...")
        self.status.setFont(QtGui.QFont(families[0], 11))
        self.status.setGeometry(386, 210, 250, 240)

        self.timer.singleShot(20, self.increaseOpacity)

        self.finish_sgn.connect(self.finish)

        self.start_time = time.perf_counter()
        separator.starter(self.status.setText, self.finish_sgn.emit)

    def increaseOpacity(self):
        if self.opacity >= 1:
            return
        self.opacity += 0.04
        self.setWindowOpacity(self.opacity)
        self.timer.singleShot(20, self.increaseOpacity)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        event.ignore()

    def finish(self, paused_time=0):
        self.end_time = time.perf_counter()
        global main_window
        main_window = MainWindow()
        main_window.show()
        self.hide()
        main_window.setStatusText.emit("Startup took %.3fs" % (self.end_time - self.start_time - paused_time))


class MainWindow(QMainWindow):
    showError = Signal(str, str)
    showInfo = Signal(str, str)
    showWarning = Signal(str, str)
    showParamSettings = Signal()
    setStatusText = Signal(str)

    _execInMainThreadSignal = Signal()
    _execInMainThreadFunc = None
    _execInMainThreadResult = None
    _execInMainThreadSuccess = False
    _execInMainThreadLock = threading.Lock()
    _execInMainThreadResultEvent = threading.Event()

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon("./icon/icon.ico"))
        self.setWindowTitle("Demucs GUI %s" % __version__)
        self.setStatusBar(QStatusBar())
        self.timer = QTimer()
        self.widget = QWidget()
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.widget)
        self.widget_layout = QVBoxLayout()
        self.widget_layout.addWidget(self.tab_widget)
        self.widget.setLayout(self.widget_layout)
        self.m = QMessageBox()
        self.showError.connect(self.showErrorFunc)
        self.showInfo.connect(self.showInfoFunc)
        self.showWarning.connect(self.showWarningFunc)
        self.showParamSettings.connect(self.showParamSettingsFunc)
        self.setStatusText.connect(self.setStatusTextFunc)
        self._execInMainThreadSignal.connect(self._exec_in_main_thread_executor)
        self.timer.singleShot(50, self.showModelSelector)

        self.menubar = QMenuBar()
        self.menu_about = QMenu("About")
        self.menu_about_about = Action(
            "About Demucs GUI", self, lambda: self.showInfoFunc("About Demucs GUI %s" % __version__, LICENSE)
        )
        self.menu_about_about.setMenuRole(Action.MenuRole.NoRole)
        self.menu_about_usage = Action(
            "Usage", self, lambda: webbrowser.open("https://github.com/CarlGao4/Demucs-Gui/blob/develop/usage.md")
        )
        self.menu_about_log = Action("Open log", self, self.open_log)
        self.menu_about.addActions([self.menu_about_about, self.menu_about_usage, self.menu_about_log])
        self.menubar.addAction(self.menu_about.menuAction())
        self.setMenuBar(self.menubar)

        shared.checkUpdate(lambda x: self.exec_in_main(lambda: self.validateUpdate(x)))

    def showModelSelector(self):
        self.model_selector = ModelSelector()
        self.tab_widget.addTab(self.model_selector, self.model_selector.widget_title)

    def showParamSettingsFunc(self):
        self.param_settings = SepParamSettings()
        self.save_options = SaveOptions()
        self.options_tab = QWidget()
        self.options_tab.setLayout(QVBoxLayout())
        self.options_tab.layout().addWidget(self.param_settings)
        self.options_tab.layout().addWidget(self.save_options)
        self.file_queue = FileQueue()
        self.separation_control = SeparationControl()
        self.tab_widget.addTab(self.options_tab, "Options")
        self.tab_widget.addTab(self.file_queue, self.file_queue.widget_title % self.file_queue.queue_length)
        self.widget_layout.addWidget(self.separation_control)

    def updateQueueLength(self):
        self.tab_widget.setTabText(
            self.tab_widget.indexOf(self.file_queue), self.file_queue.widget_title % self.file_queue.queue_length
        )

    def loadModel(self, model, repo):
        try:
            self.separator = separator.Separator(model, repo, self.setStatusText.emit)
        except:
            logging.error(
                "Failed to load model %s from %s:\n%s"
                % (model, ('"' + str(repo) + '"') if repo is not None else "remote repo", traceback.format_exc())
            )
            return False
        return True

    def closeEvent(self, event):
        if (
            (not hasattr(self, "separator"))
            or (not (self.separator.separating or self.save_options.saving))
            or (
                self.m.question(
                    self,
                    "Separation in progress",
                    "Separation is not finished, quit anyway?",
                    self.m.StandardButton.Yes,
                    self.m.StandardButton.Cancel,
                )
                == self.m.StandardButton.Yes
            )
        ):
            return super().closeEvent(event)
        else:
            event.ignore()

    def showErrorFunc(self, title, text):
        self.m.critical(self, title, text)

    def showInfoFunc(self, title, text):
        self.m.information(self, title, text)

    def showWarningFunc(self, title, text):
        self.m.warning(self, title, text)

    def setStatusTextFunc(self, text):
        self.statusBar().showMessage(text)

    def open_log(self):
        if sys.platform == "win32":
            os.startfile(str(shared.logfile))
        elif sys.platform == "darwin":
            os.system(shlex.join(["open", str(shared.logfile), "&"]))
        else:
            try:
                os.system(shlex.join(["xdg-open", str(shared.logfile), "&"]))
            except:
                if (
                    self.m.question(
                        self,
                        "Open log failed",
                        "Failed to open log file. Do you want to copy the path?",
                        self.m.StandardButton.Yes,
                        self.m.StandardButton.No,
                    )
                    == self.m.StandardButton.Yes
                ):
                    QApplication.clipboard().setText(str(shared.logfile))

    def exec_in_main(self, func):
        with self._execInMainThreadLock:
            self._execInMainThreadFunc = func
            self._execInMainThreadResultEvent.clear()
            self._execInMainThreadSignal.emit()
            self._execInMainThreadResultEvent.wait()
            if self._execInMainThreadSuccess:
                ret = self._execInMainThreadResult
                self._execInMainThreadResult = None
                self._execInMainThreadFunc = None
                return ret
            else:
                err = self._execInMainThreadResult
                self._execInMainThreadResult = None
                self._execInMainThreadFunc = None
                raise err

    def _exec_in_main_thread_executor(self):
        try:
            self._execInMainThreadResult = self._execInMainThreadFunc()
            self._execInMainThreadSuccess = True
        except Exception as e:
            self._execInMainThreadResult = e
            self._execInMainThreadSuccess = False
        self._execInMainThreadResultEvent.set()

    def validateUpdate(self, new_version):
        if new_version is None:
            return
        if new_version <= __version__:
            return
        if (
            self.m.question(
                self,
                "Update available",
                "A new version (%s) of Demucs GUI is available. Do you want to visit GitHub to download it?"
                % new_version,
                self.m.StandardButton.Yes,
                self.m.StandardButton.No,
            )
            == self.m.StandardButton.Yes
        ):
            webbrowser.open("https://github.com/CarlGao4/Demucs-Gui/releases")


class ModelSelector(QWidget):
    widget_title = "Select model"

    def __init__(self):
        super().__init__()

        self.advanced_settings = AdvancedModelSettings(self.refreshModels)

        self.select_label = QLabel()
        self.select_label.setText("Model:")
        self.select_label.setFixedWidth(80)

        self.select_combobox = QComboBox()
        self.select_combobox.setMinimumWidth(240)
        self.select_combobox.currentIndexChanged.connect(self.updateModelInfo)

        self.model_info = ModifiedQLabel()
        self.model_info.setMinimumHeight(160)
        self.model_info.setWordWrap(True)
        self.model_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.model_info.setMinimumWidth(300)

        self.refresh_button = QPushButton()
        self.refresh_button.setText("Refresh")
        self.refresh_button.setFixedWidth(80)
        self.refresh_button.clicked.connect(self.refreshModels)

        self.advanced_button = QPushButton()
        self.advanced_button.setText("Advanced")
        self.advanced_button.clicked.connect(self.advanced_settings.show)

        self.load_button = QPushButton()
        self.load_button.setText("Load")
        self.load_button.clicked.connect(self.loadModel)

        self.widget_layout = QGridLayout()
        self.widget_layout.addWidget(self.select_label, 0, 0)
        self.widget_layout.addWidget(self.select_combobox, 0, 1)
        self.widget_layout.addWidget(self.refresh_button, 0, 2)
        self.widget_layout.addWidget(self.model_info, 2, 0, 1, 3)

        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.advanced_button)
        self.button_layout.addWidget(self.load_button)
        self.widget_layout.addLayout(self.button_layout, 3, 0, 1, 3)

        self.setLayout(self.widget_layout)
        self.refreshModels()

    def updateModelInfo(self, index):
        self.model_info.setText(self.infos[index])

    def refreshModels(self):
        self.models, self.infos, self.repos = separator.autoListModels()
        self.setEnabled(False)
        self.select_combobox.clear()
        self.select_combobox.addItems(self.models)
        self.setEnabled(True)

    @shared.thread_wrapper(daemon=True)
    def loadModel(self):
        global main_window

        main_window.exec_in_main(lambda: self.setEnabled(False))
        main_window.exec_in_main(lambda: self.advanced_settings.setEnabled(False))

        model_name = self.models[main_window.exec_in_main(lambda: self.select_combobox.currentIndex())]
        model_repo = self.repos[main_window.exec_in_main(lambda: self.select_combobox.currentIndex())]
        logging.info(
            "Loading model %s from repo %s" % (model_name, model_repo if model_repo is not None else '"remote"')
        )
        main_window.setStatusText.emit("Loading model %s" % model_name)

        start_time = time.perf_counter()
        success = main_window.loadModel(model_name, model_repo)
        end_time = time.perf_counter()

        if not success:
            main_window.showError.emit(
                "Load model failed", "Failed to load model. Check log file for more information."
            )
            main_window.exec_in_main(lambda: self.setEnabled(True))
            main_window.exec_in_main(lambda: self.advanced_settings.setEnabled(True))
            return

        model_info = main_window.separator.modelInfo()
        main_window.exec_in_main(lambda: main_window.model_selector.model_info.setText(model_info))
        main_window.exec_in_main(lambda: self.model_info.setMinimumHeight(self.model_info.heightForWidth(400)))
        main_window.setStatusText.emit("Model loaded within %.4fs" % (end_time - start_time))
        main_window.showParamSettings.emit()
        logging.info("Model loaded within %.4fs" % (end_time - start_time))
        logging.info(model_info)


class AdvancedModelSettings(QDialog):
    def __init__(self, refresh_command):
        super().__init__()
        self.setWindowTitle("Advanced Model Settings")
        self.setWindowIcon(QtGui.QIcon("./icon/icon.ico"))
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)

        self.refresh_command = refresh_command

        self.info = QLabel()
        self.info.setText("Additional model path:\nWill search for models apart from the defaults.")

        self.path_list = QListWidget()
        self.path_list.setMinimumWidth(300)
        self.path_list.addItems(list(set(shared.GetSetting("custom_repo", []))))

        self.new_path = QLineEdit()
        self.new_path.setMinimumWidth(300)

        self.browse_button = QPushButton()
        self.browse_button.setText("Browse...")
        self.browse_button.clicked.connect(self.browseRepo)

        self.add_button = QPushButton()
        self.add_button.setText("Add")
        self.add_button.clicked.connect(self.addRepo)

        self.remove_button = QPushButton()
        self.remove_button.setText("Remove")
        self.remove_button.clicked.connect(self.removeRepo)

        self.dialog_layout = QVBoxLayout()
        self.dialog_layout.addWidget(self.info)
        self.dialog_layout.addWidget(self.path_list)
        self.dialog_layout.addWidget(self.new_path)
        self.dialog_layout.addWidget(self.browse_button)
        self.dialog_layout.addWidget(self.add_button)
        self.dialog_layout.addWidget(self.remove_button)

        self.setLayout(self.dialog_layout)

    def browseRepo(self):
        p = QFileDialog.getExistingDirectory(self, "Browse model repo")
        if p:
            self.new_path.setText(p)

    def addRepo(self):
        if not self.new_path.text().strip():
            self.new_path.clear()
            return
        shared.SetSetting(
            "custom_repo",
            list(set(shared.GetSetting("custom_repo", []) + [str(pathlib.Path(self.new_path.text()).resolve())])),
        )
        self.new_path.clear()
        self.path_list.clear()
        self.path_list.addItems(list(set(shared.GetSetting("custom_repo", []))))
        self.refresh_command()

    def removeRepo(self):
        if not self.path_list.selectedItems():
            return
        shared.SetSetting(
            "custom_repo", list(set(shared.GetSetting("custom_repo", [])) - {self.path_list.selectedItems()[0].text()})
        )
        self.path_list.clear()
        self.path_list.addItems(list(set(shared.GetSetting("custom_repo", []))))
        self.refresh_command()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


class SepParamSettings(QGroupBox):
    def __init__(self):
        global main_window

        super().__init__()
        self.setTitle("Separation parameters")

        self.device_label = QLabel()
        self.device_label.setText("Device:")
        self.device_label.setToolTip("Device on which to execute the computation")

        self.device_selector = QComboBox()
        for info, id_ in separator.getAvailableDevices():
            self.device_selector.addItem(info, userData=id_)
        self.device_selector.currentTextChanged.connect(lambda string: self.device_selector.setToolTip(str(string)))
        self.device_selector.setCurrentIndex(separator.default_device)
        self.device_selector.setMinimumWidth(200)

        self.segment_label = QLabel()
        self.segment_label.setText("Segment:")
        self.segment_label.setToolTip("Length of each segment")

        self.segment_spinbox = QDoubleSpinBox()
        self.segment_spinbox.setRange(0.1, float(main_window.separator.default_segment))
        self.segment_spinbox.setSingleStep(0.1)
        self.segment_spinbox.setValue(self.segment_spinbox.maximum())
        self.segment_spinbox.setSuffix("s")
        self.segment_spinbox.setDecimals(1)

        self.segment_slider = QSlider()
        self.segment_slider.setOrientation(Qt.Orientation.Horizontal)
        self.segment_slider.setRange(1, int(main_window.separator.default_segment * 10))
        self.segment_slider.setValue(self.segment_slider.maximum())
        self.segment_slider.setMaximumWidth(360)
        self.segment_slider.valueChanged.connect(lambda value: self.segment_spinbox.setValue(value / 10))
        self.segment_spinbox.valueChanged.connect(lambda value: self.segment_slider.setValue(int(value * 10)))

        self.overlap_label = QLabel()
        self.overlap_label.setText("Overlap:")
        self.overlap_label.setToolTip("The overlap between the splits")

        self.overlap_spinbox = QDoubleSpinBox()
        self.overlap_spinbox.setRange(0.0, 0.99)
        self.overlap_spinbox.setSingleStep(0.01)
        self.overlap_spinbox.setValue(0.25)
        self.overlap_spinbox.setDecimals(2)

        self.overlap_slider = QSlider()
        self.overlap_slider.setOrientation(Qt.Orientation.Horizontal)
        self.overlap_slider.setRange(0, 99)
        self.overlap_slider.setValue(25)
        self.overlap_slider.setMaximumWidth(360)
        self.overlap_slider.valueChanged.connect(lambda value: self.overlap_spinbox.setValue(value / 100))
        self.overlap_spinbox.valueChanged.connect(lambda value: self.overlap_slider.setValue(int(value * 100)))

        self.shifts_label = QLabel()
        self.shifts_label.setText("Shifts:")
        self.shifts_label.setToolTip(
            "Shift in time `wav` by a random amount between 0 and 0.5 sec"
            " and apply the oppositve shift to the output"
        )

        self.shifts_spinbox = QSpinBox()
        self.shifts_spinbox.setRange(0, 65535)
        self.shifts_spinbox.setSingleStep(1)
        self.shifts_spinbox.setValue(0)

        self.shifts_slider = QSlider()
        self.shifts_slider.setOrientation(Qt.Orientation.Horizontal)
        self.shifts_slider.setRange(0, 20)
        self.shifts_slider.setValue(0)
        self.shifts_slider.setMaximumWidth(360)
        self.shifts_slider.valueChanged.connect(lambda value: self.shifts_spinbox.setValue(value))
        self.shifts_spinbox.valueChanged.connect(lambda value: self.shifts_slider.setValue(value))

        self.default_button = QPushButton()
        self.default_button.setText("Restore defaults")
        self.default_button.clicked.connect(self.restoreDefaults)

        self.widget_layout = QGridLayout()
        self.widget_layout.addWidget(self.device_label, 0, 0)
        self.widget_layout.addWidget(self.device_selector, 0, 1, 1, 2)
        self.widget_layout.addWidget(self.segment_label, 1, 0)
        self.widget_layout.addWidget(self.segment_spinbox, 1, 1)
        self.widget_layout.addWidget(self.segment_slider, 1, 2)
        self.widget_layout.addWidget(self.overlap_label, 2, 0)
        self.widget_layout.addWidget(self.overlap_spinbox, 2, 1)
        self.widget_layout.addWidget(self.overlap_slider, 2, 2)
        self.widget_layout.addWidget(self.shifts_label, 3, 0)
        self.widget_layout.addWidget(self.shifts_spinbox, 3, 1)
        self.widget_layout.addWidget(self.shifts_slider, 3, 2)
        self.widget_layout.addWidget(self.default_button, 4, 0, 1, 3)

        self.setLayout(self.widget_layout)

    def restoreDefaults(self):
        self.device_selector.setCurrentIndex(separator.default_device)
        self.segment_spinbox.setValue(float(main_window.separator.default_segment))
        self.segment_slider.setValue(int(main_window.separator.default_segment * 10))
        self.overlap_spinbox.setValue(0.25)
        self.overlap_slider.setValue(25)
        self.shifts_spinbox.setValue(0)
        self.shifts_slider.setValue(0)


class SaveOptions(QGroupBox):
    def __init__(self):
        global main_window

        super().__init__()
        self.setTitle("Save options")

        self.location_label = QLabel()
        self.location_label.setText("Saved file location:")
        self.location_help = QPushButton()
        self.location_help.setText("Syntax help")
        self.location_help.clicked.connect(
            lambda: main_window.showInfo.emit("Save location syntax", shared.save_loc_syntax)
        )

        self.location_group = QButtonGroup()
        self.loc_relative_path_button = QRadioButton()
        self.loc_relative_path_button.setText("Relative path")
        self.loc_absolute_path_button = QRadioButton()
        self.loc_absolute_path_button.setText("Absolute path")
        self.location_group.addButton(self.loc_relative_path_button, 0)
        self.location_group.addButton(self.loc_absolute_path_button, 1)
        self.loc_relative_path_button.setChecked(True)
        self.loc_input = QLineEdit()
        self.loc_input.setText("separated/{model}/{track}/{stem}.{ext}")
        self.browse_button = QPushButton()
        self.browse_button.setText("Browse")
        self.browse_button.clicked.connect(self.browseLocation)
        self.browse_button.setEnabled(False)
        self.location_group.idToggled.connect(lambda Id, checked: self.browse_button.setEnabled(not Id ^ checked))

        self.clip_mode_label = QLabel()
        self.clip_mode_label.setText("Clip mode:")

        self.clip_mode = QComboBox()
        self.clip_mode.addItems(["rescale", "clamp", "none"])
        self.clip_mode.setCurrentIndex(0)

        self.file_format_label = QLabel()
        self.file_format_label.setText("File format:")

        self.file_format = QComboBox()
        self.file_format.addItems(["wav", "flac"])
        self.file_format.setCurrentIndex(1)

        self.sample_fmt_label = QLabel()
        self.sample_fmt_label.setText("Sample format:")

        self.sample_fmt = QComboBox()
        self.sample_fmt.addItem("int16", "PCM_16")
        self.sample_fmt.addItem("int24", "PCM_24")
        self.sample_fmt.addItem("float32", "FLOAT")
        self.sample_fmt.setCurrentIndex(0)

        self.widget_layout = QGridLayout()
        self.widget_layout.addWidget(self.location_label, 0, 0, 1, 2)
        self.widget_layout.addWidget(self.location_help, 0, 2)
        self.widget_layout.addWidget(self.loc_relative_path_button, 1, 1)
        self.widget_layout.addWidget(self.loc_absolute_path_button, 1, 2)
        self.widget_layout.addWidget(self.loc_input, 2, 1, 1, 2)
        self.widget_layout.addWidget(self.browse_button, 3, 1, 1, 2)
        self.widget_layout.addWidget(self.clip_mode_label, 4, 0, 1, 2)
        self.widget_layout.addWidget(self.clip_mode, 4, 2)
        self.widget_layout.addWidget(self.file_format_label, 5, 0, 1, 2)
        self.widget_layout.addWidget(self.file_format, 5, 2)
        self.widget_layout.addWidget(self.sample_fmt_label, 6, 0, 1, 2)
        self.widget_layout.addWidget(self.sample_fmt, 6, 2)

        self.setLayout(self.widget_layout)

        self.saving = 0

    def browseLocation(self):
        p = QFileDialog.getExistingDirectory(self, "Browse saved file location")
        if p:
            self.loc_input.setText(p)

    @shared.thread_wrapper(daemon=True)
    def save(self, file, tensor, save_func, item, finishCallback):
        self.saving += 1
        finishCallback(shared.FileStatus.Writing, item)
        for stem, stem_data in tensor.items():
            file_path_str = self.loc_input.text().format(
                track=file.stem,
                trackext=file.name,
                stem=stem,
                ext=self.file_format.currentText(),
                model=main_window.model_selector.select_combobox.currentText(),
            )
            if self.location_group.checkedId() == 0:
                file_path = file.parent / file_path_str
            else:
                file_path = pathlib.Path(file_path_str)
            if self.clip_mode.currentText() == "rescale":
                data = stem_data / stem_data.abs().max() * 0.999
            elif self.clip_mode.currentText() == "clamp":
                data = stem_data.clamp(-0.999, 0.999)
            else:
                data = stem_data
            file_path.parent.mkdir(parents=True, exist_ok=True)
            save_func(file_path, data, self.sample_fmt.currentData())
        self.saving -= 1
        finishCallback(shared.FileStatus.Finished, item)


class FileQueue(QWidget):
    widget_title = "File queue (%d)"

    def __init__(self):
        global main_window

        super().__init__()

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setMinimumWidth(280)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.verticalScrollBar().setSingleStep(8)
        self.table.horizontalScrollBar().setSingleStep(8)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setMinimumSectionSize(80)
        font = self.table.font()
        font.setPointSize(int(font.pointSize() * 0.9))
        self.table.setFont(font)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.table.setHorizontalHeaderLabels(["File", "Status"])
        self.table.setColumnWidth(1, 80)
        self.table.horizontalHeaderItem(0).setToolTip("Click here to toggle file name/full path")

        self.table.setAcceptDrops(True)
        self.table.dropEvent = self.table_dropEvent
        self.table.dragEnterEvent = self.table_dragEnterEvent
        self.table.dragMoveEvent = self.table_dragMoveEvent

        self.show_full_path = False
        self.table.horizontalHeaderItem(0).setToolTip("Toggle full path/file name")
        self.table.horizontalHeaderItem(1).setToolTip("Toggle animation")
        self.table.horizontalHeader().sectionClicked.connect(self.tableHeaderClicked)

        self.add_folder_button = QPushButton()
        self.add_folder_button.setText("Add folder")
        self.add_folder_button.clicked.connect(
            lambda: self.addFiles([QFileDialog.getExistingDirectory(main_window, "Add a folder to queue")])
        )

        self.add_files_button = QPushButton()
        self.add_files_button.setText("Add files")
        self.add_files_button.clicked.connect(
            lambda: self.addFiles(
                QFileDialog.getOpenFileNames(main_window, "Add files to queue", filter=separator.audio.format_filter)[0]
            )
        )

        self.remove_files_button = QPushButton()
        self.remove_files_button.setText("Remove")
        self.remove_files_button.clicked.connect(self.removeFiles)
        self.table.keyReleaseEvent = self.table_keyReleaseEvent

        self.pause_button = QPushButton()
        self.pause_button.setText("Pause")
        self.pause_button.clicked.connect(self.pause)

        self.resume_button = QPushButton()
        self.resume_button.setText("Resume")
        self.resume_button.clicked.connect(self.resume)

        self.move_top_button = QPushButton()
        self.move_top_button.setText("Move top")
        self.move_top_button.clicked.connect(self.moveTop)

        self.widget_layout = QGridLayout()
        self.widget_layout.addWidget(self.table, 0, 0, 1, 3)
        self.widget_layout.addWidget(self.add_folder_button, 1, 0)
        self.widget_layout.addWidget(self.add_files_button, 1, 1)
        self.widget_layout.addWidget(self.remove_files_button, 1, 2)
        self.widget_layout.addWidget(self.pause_button, 2, 0)
        self.widget_layout.addWidget(self.resume_button, 2, 1)
        self.widget_layout.addWidget(self.move_top_button, 2, 2)

        self.setLayout(self.widget_layout)

        self.repaint_timer = QTimer()
        self.repaint_timer.timeout.connect(self.paint_table_progress)
        self.toggleAnimation(True)

        self.queue_length = 0

    def table_dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def table_dragMoveEvent(self, event):
        pass

    def table_dropEvent(self, event):
        self.addFiles([i.toLocalFile() for i in event.mimeData().urls()])

    def table_keyReleaseEvent(self, event):
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.removeFiles()

    def paint_table_progress(self):
        """Force refresh progress bar"""
        begin = self.table.rowAt(0)
        end = self.table.rowAt(self.table.height())
        if begin == -1:
            begin = 0
        if end == -1:
            end = self.table.rowCount() - 1
        for i in range(begin, end + 1):
            item = self.table.item(i, 1)
            if item is not None:
                item.setData(Qt.ItemDataRole.UserRole + 0x100, random.random())

    def addFiles(self, files):
        files = map(pathlib.Path, (i for i in files if len(i)))
        for file in files:
            if file.is_dir():
                for dirpath, dirnames, filenames in os.walk(file):
                    dirpath_path = pathlib.Path(dirpath)
                    self.addFiles([str(dirpath_path / filename) for filename in filenames])
            else:
                row = self.table.rowCount()
                self.table.insertRow(row)
                if self.show_full_path:
                    self.table.setItem(row, 0, QTableWidgetItem(str(file)))
                else:
                    self.table.setItem(row, 0, QTableWidgetItem(file.name))
                delegate = ProgressDelegate()
                self.table.setItemDelegateForColumn(1, delegate)
                self.table.setItem(row, 1, QTableWidgetItem())
                self.table.item(row, 0).setToolTip(str(file))
                self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file)
                self.table.item(row, 1).setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Queued])
                self.table.item(row, 1).setData(ProgressDelegate.ProgressRole, 0)
                self.table.item(row, 1).setData(ProgressDelegate.TextRole, "Queued")
                self.queue_length += 1
                main_window.updateQueueLength()

    def tableHeaderClicked(self, index):
        if index == 0:
            self.togglePathName()
        elif index == 1:
            self.toggleAnimation()

    def toggleAnimation(self, first=False):
        animation = shared.GetSetting("file_list_animation", False)
        if not first:
            animation = not animation
            shared.SetSetting("file_list_animation", animation)
        if animation:
            self.repaint_timer.start(40)
        else:
            self.repaint_timer.stop()

    def togglePathName(self):
        self.show_full_path = not self.show_full_path
        if self.show_full_path:
            for i in range(self.table.rowCount()):
                item = self.table.item(i, 0)
                item.setText(str(item.data(Qt.ItemDataRole.UserRole)))
        else:
            for i in range(self.table.rowCount()):
                item = self.table.item(i, 0)
                item.setText(item.data(Qt.ItemDataRole.UserRole).name)

    def removeFiles(self):
        indexes = sorted(list(set(i.row() for i in self.table.selectedIndexes())), reverse=True)
        for i in indexes:
            if self.table.item(i, 1).data(Qt.ItemDataRole.UserRole)[0] not in [
                shared.FileStatus.Paused,
                shared.FileStatus.Queued,
                shared.FileStatus.Finished,
                shared.FileStatus.Cancelled,
                shared.FileStatus.Failed,
            ]:
                continue
            self.table.removeRow(i)
            self.queue_length -= 1
            main_window.updateQueueLength()

    def pause(self):
        indexes = list(set(i.row() for i in self.table.selectedIndexes()))
        for i in indexes:
            if self.table.item(i, 1).data(Qt.ItemDataRole.UserRole)[0] == shared.FileStatus.Queued:
                self.table.item(i, 1).setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Paused])
                self.table.item(i, 1).setData(ProgressDelegate.TextRole, "Paused")

    def resume(self):
        indexes = list(set(i.row() for i in self.table.selectedIndexes()))
        for i in indexes:
            if self.table.item(i, 1).data(Qt.ItemDataRole.UserRole)[0] in [
                shared.FileStatus.Paused,
                shared.FileStatus.Cancelled,
            ]:
                self.table.item(i, 1).setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Queued])
                self.table.item(i, 1).setData(ProgressDelegate.TextRole, "Queued")

    def moveTop(self):
        indexes = sorted(list(set(i.row() for i in self.table.selectedIndexes())))
        for i, index in enumerate(indexes):
            if self.table.item(index, 1).data(Qt.ItemDataRole.UserRole)[0] not in [
                shared.FileStatus.Paused,
                shared.FileStatus.Queued,
            ]:
                continue
            self.table.insertRow(i)
            for j in range(self.table.columnCount()):
                self.table.setItem(i, j, self.table.item(index + 1, j).clone())
            self.table.removeRow(index + 1)

    def getFirstQueued(self):
        self.setEnabled(False)
        for i in range(self.table.rowCount()):
            if self.table.item(i, 1).data(Qt.ItemDataRole.UserRole)[0] == shared.FileStatus.Queued:
                self.setEnabled(True)
                return i
        self.setEnabled(True)
        return None


class SeparationControl(QWidget):
    startSeparateSignal = Signal()
    currentFinishedSignal = Signal(int, QTableWidgetItem)
    setModelProgressSignal = Signal(float)
    setAudioProgressSignal = Signal(float, QTableWidgetItem)
    setStatusSignal = Signal(int, QTableWidgetItem)

    def __init__(self):
        super().__init__()

        self.stop_now = False

        self.start_button = QPushButton()
        self.start_button.setText("Start separation")
        self.start_button.clicked.connect(self.startSeparation)

        self.stop_button = QPushButton()
        self.stop_button.setText("Stop current audio")
        self.stop_button.clicked.connect(self.stopCurrent)

        self.current_model_label = QLabel()
        self.current_model_label.setText("Current model:")

        self.current_audio_label = QLabel()
        self.current_audio_label.setText("Current audio:")

        self.current_model_progressbar = QProgressBar()
        self.current_model_progressbar.setMaximum(65536)
        self.current_model_progressbar.setValue(0)
        self.current_model_progressbar.setMinimumWidth(400)

        self.current_audio_progressbar = QProgressBar()
        self.current_audio_progressbar.setMaximum(65536)
        self.current_audio_progressbar.setValue(0)
        self.current_audio_progressbar.setMinimumWidth(400)

        self.widget_layout = QGridLayout()
        self.widget_layout.addWidget(self.start_button, 0, 0)
        self.widget_layout.addWidget(self.stop_button, 1, 0)
        self.widget_layout.addWidget(self.current_model_label, 0, 1)
        self.widget_layout.addWidget(self.current_audio_label, 1, 1)
        self.widget_layout.addWidget(self.current_model_progressbar, 0, 2)
        self.widget_layout.addWidget(self.current_audio_progressbar, 1, 2)

        self.setLayout(self.widget_layout)

        self.startSeparateSignal.connect(self.startSeparation)
        self.currentFinishedSignal.connect(self.currentFinished)
        self.setModelProgressSignal.connect(self.setModelProgressEmit)
        self.setAudioProgressSignal.connect(self.setAudioProgressEmit)
        self.setStatusSignal.connect(self.setStatusForItem)

    def setModelProgressEmit(self, value):
        self.current_model_progressbar.setValue(int(value * 65536))

    def setAudioProgressEmit(self, value, item: QTableWidgetItem):
        self.current_audio_progressbar.setValue(int(value * 65536))
        item.setData(ProgressDelegate.ProgressRole, value)
        item.setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Separating, value])
        item.setData(ProgressDelegate.TextRole, "")

    def setModelProgress(self, value):
        if self.stop_now:
            self.stop_now = False
            raise KeyboardInterrupt
        self.setModelProgressSignal.emit(value)

    def setAudioProgress(self, value, item: QTableWidgetItem):
        if self.stop_now:
            self.stop_now = False
            raise KeyboardInterrupt
        self.setAudioProgressSignal.emit(value, item)

    def setStatusForItem(self, status, item: QTableWidgetItem):
        item.setData(Qt.ItemDataRole.UserRole, [status])
        if status == shared.FileStatus.Reading:
            item.setData(ProgressDelegate.TextRole, "Reading")
        elif status == shared.FileStatus.Writing:
            item.setData(ProgressDelegate.TextRole, "Writing")

    def currentFinished(self, status, item: QTableWidgetItem):
        if status == shared.FileStatus.Finished:
            item.setData(ProgressDelegate.TextRole, "Finished")
            item.setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Finished])
            main_window.setStatusText.emit(
                "Separation finished: %s" % main_window.file_queue.table.item(item.row(), 0).text()
            )
        elif status == shared.FileStatus.Failed:
            item.setData(ProgressDelegate.TextRole, "Failed")
            item.setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Failed])
            item.setData(ProgressDelegate.ProgressRole, 0)
        elif status == shared.FileStatus.Cancelled:
            item.setData(ProgressDelegate.TextRole, "Cancelled")
            item.setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Cancelled])
            item.setData(ProgressDelegate.ProgressRole, 0)
        elif status == shared.FileStatus.Writing:
            item.setData(ProgressDelegate.TextRole, "Writing")
            item.setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Writing])
        if self.stop_now:
            self.stop_now = False
        if status not in [shared.FileStatus.Writing]:
            main_window.file_queue.queue_length -= 1
            main_window.updateQueueLength()
        if status != shared.FileStatus.Finished:
            self.start_button.setEnabled(True)
            self.startSeparateSignal.emit()

    def startSeparation(self):
        global main_window
        if "{stem}" not in main_window.save_options.loc_input.text():
            main_window.showWarning.emit("Warning", '"{stem}" not included in save location. May cause overwrite.')
        self.start_button.setEnabled(False)
        index = main_window.file_queue.getFirstQueued()
        if (index := main_window.file_queue.getFirstQueued()) is None:
            self.start_button.setEnabled(True)
            main_window.setStatusText.emit("No more file to separate")
            separator.empty_cuda_cache()
            return
        file = main_window.file_queue.table.item(index, 0).data(Qt.ItemDataRole.UserRole)
        item = main_window.file_queue.table.item(index, 1)
        item.setData(Qt.ItemDataRole.UserRole, [shared.FileStatus.Separating])
        item.setData(ProgressDelegate.ProgressRole, 0)
        item.setData(ProgressDelegate.TextRole, "")
        main_window.separator.startSeparate(
            file,
            item,
            main_window.param_settings.segment_spinbox.value(),
            main_window.param_settings.overlap_spinbox.value(),
            main_window.param_settings.shifts_spinbox.value(),
            main_window.param_settings.device_selector.currentData(),
            main_window.save_options.save,
            self.setModelProgress,
            self.setAudioProgress,
            self.setStatusSignal.emit,
            self.currentFinishedSignal.emit,
        )

    def stopCurrent(self):
        if self.start_button.isEnabled():
            return
        self.stop_now = True


if __name__ == "__main__":
    try:
        shared.InitializeFolder()
        log_filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_demucs_gui_log.log")
        if shared.debug:
            log = sys.stderr
        else:
            log = open(str(shared.logfile / log_filename), mode="at")
            sys.stderr = log
        handler = logging.StreamHandler(log)
        try:
            assert sys.platform == "darwin" or sys.platform == "linux"
            syslog_handler = logging.handlers.SysLogHandler()
            logging.basicConfig(
                handlers=[handler, syslog_handler],
                format="%(asctime)s (%(filename)s) (Line %(lineno)d) [%(levelname)s] : %(message)s",
                level=logging.DEBUG,
            )
        except:
            logging.basicConfig(
                handlers=[handler],
                format="%(asctime)s (%(filename)s) (Line %(lineno)d) [%(levelname)s] : %(message)s",
                level=logging.DEBUG,
            )
    except:
        print(traceback.format_exc())
        app = QApplication([])
        msgbox = QMessageBox()
        msgbox.setIcon(QMessageBox.Icon.Critical)
        msgbox.setText("Failed to initialize log file. ")
        msgbox.setWindowTitle("Demucs GUI start failed")
        msgbox.exec()
        raise SystemExit(1)

    logging.info("Python version: %s" % sys.version)
    logging.info("Demucs GUI version: %s" % __version__)
    logging.info("System: %s" % platform.platform())
    logging.info("Architecture: %s" % platform.architecture()[0])
    logging.info("CPU: %s" % platform.processor())
    logging.info("CPU count: %d" % psutil.cpu_count())
    logging.info(
        "System memory: %d (%s)" % (psutil.virtual_memory().total, shared.HSize(psutil.virtual_memory().total))
    )
    logging.info(
        "System free memory: %d (%s)" % (psutil.virtual_memory().free, shared.HSize(psutil.virtual_memory().free))
    )
    logging.info("System swap memory: %d (%s)" % (psutil.swap_memory().total, shared.HSize(psutil.swap_memory().total)))

    app = QApplication([])
    starting_window = StartingWindow()
    starting_window.show()
    logging.debug("Supported styles: %s" % ", ".join(QStyleFactory.keys()))
    style_setting = shared.GetSetting("style", app.style().objectName())
    if style_setting.lower() in [i.lower() for i in QStyleFactory.keys()]:
        app.setStyle(QStyleFactory.create(style_setting))
    logging.debug("Current style: %s" % app.style().objectName())

    app.exec()
