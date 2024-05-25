# Demucs-GUI
# Copyright (C) 2022-2024  Demucs-GUI developers
# See https://github.com/CarlGao4/Demucs-Gui for more information

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import shared

if not shared.use_PyQt6:
    from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRegularExpression, QSize, Qt
    from PySide6.QtGui import QAction, QFontMetrics, QPainter, QRegularExpressionValidator, QTextOption
    from PySide6.QtWidgets import (
        QApplication,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
        QSizePolicy,
        QSpinBox,
        QStyle,
        QStyleFactory,
        QStyledItemDelegate,
        QStyleOption,
        QStyleOptionProgressBar,
        QStyleOptionViewItem,
    )
    from qt_table_checkbox.side6_table_checkbox import (
        NotImplementedWarning,
        QTableWidgetWithCheckBox as QTableWidgetWithCheckBox,
    )
else:
    from PyQt6.QtCore import QModelIndex, QPersistentModelIndex, QRegularExpression, QSize, Qt  # type: ignore
    from PyQt6.QtGui import QAction, QFontMetrics, QPainter, QRegularExpressionValidator, QTextOption  # type: ignore
    from PyQt6.QtWidgets import (  # type: ignore
        QApplication,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
        QSizePolicy,
        QSpinBox,
        QStyle,
        QStyleFactory,
        QStyledItemDelegate,
        QStyleOption,
        QStyleOptionProgressBar,
        QStyleOptionViewItem,
    )
    from qt_table_checkbox.qt6_table_checkbox import (  # type: ignore
        NotImplementedWarning,
        QTableWidgetWithCheckBox as QTableWidgetWithCheckBox,
    )

from typing import Callable, Union

import math
import sys
import warnings


warnings.filterwarnings("ignore", category=NotImplementedWarning)


# Modified so that text can be wrapped everywhere
class TextWrappedQLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.textalignment = Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWrapAnywhere
        self.isTextLabel = True
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self._minimum_height = 0

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)

        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

        self.style().drawItemText(painter, self.rect(), self.textalignment, self.palette(), True, self.text())

    def setMinimumHeight(self, height):
        self._minimum_height = height

    def heightForWidth(self, width):
        metrics = QFontMetrics(self.font())

        return metrics.boundingRect(0, 0, width, 0, self.textalignment, self.text()).height()

    def sizeHint(self):
        return QSize(self.width(), max(self._minimum_height, self.heightForWidth(self.width())))

    def minimumSizeHint(self):
        return QSize(0, 0)

    def resizeEvent(self, event):
        self.updateGeometry()


class ExpandingQPlainTextEdit(QPlainTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))

    def sizeHint(self):
        metrics = QFontMetrics(self.document().defaultFont())
        rect = metrics.boundingRect(
            0,
            0,
            0,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWrapAnywhere,
            "\n".join(["M"] * math.ceil(self.document().size().height())),
        )
        total_height = int(
            rect.height()
            + self.contentsMargins().top()
            + self.contentsMargins().bottom()
            + self.viewport().contentsMargins().top()
            + self.viewport().contentsMargins().bottom()
            + 2 * self.frameWidth()
            + 2 * self.document().documentMargin()
        )
        if self.horizontalScrollBar().isVisible():
            total_height += self.horizontalScrollBar().height()
        return QSize(self.width(), total_height)

    def minimumSizeHint(self):
        return QSize(0, self.sizeHint().height())

    def resizeEvent(self, event):
        self.updateGeometry()
        return super().resizeEvent(event)

    def text(self):
        return self.toPlainText()


class DelegateCombiner(QStyledItemDelegate):
    """So that we can use multiple delegates in the same QTableView. Will also count editors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._delegates = []
        self._editors = 0

    def addDelegate(
        self, delegate: QStyledItemDelegate, condition: Callable[[Union[QModelIndex, QPersistentModelIndex]], bool]
    ):
        self._delegates.append((delegate, condition))

    @property
    def editors(self):
        return self._editors

    # Distribute QStyledItemDelegate methods to the delegates

    def createEditor(self, parent, option, index):
        self._editors += 1
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.createEditor(parent, option, index)
        return super().createEditor(parent, option, index)

    def editorEvent(self, event, model, option, index):
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.editorEvent(event, model, option, index)
        return super().editorEvent(event, model, option, index)

    def initStyleOption(self, option, index):
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.initStyleOption(option, index)
        return super().initStyleOption(option, index)

    def paint(self, painter, option, index):
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.paint(painter, option, index)
        return super().paint(painter, option, index)

    def setEditorData(self, editor, index):
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.setEditorData(editor, index)
        return super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.setModelData(editor, model, index)
        return super().setModelData(editor, model, index)

    def sizeHint(self, option, index):
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.sizeHint(option, index)
        return super().sizeHint(option, index)

    def updateEditorGeometry(self, editor, option, index):
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.updateEditorGeometry(editor, option, index)
        return super().updateEditorGeometry(editor, option, index)

    # Distribute QAbstractItemDelegate methods to the delegates

    def destroyEditor(self, editor, index):
        self._editors -= 1
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.destroyEditor(editor, index)
        return super().destroyEditor(editor, index)

    def helpEvent(self, event, view, option, index):
        for delegate, condition in self._delegates:
            if condition(index):
                return delegate.helpEvent(event, view, option, index)
        return super().helpEvent(event, view, option, index)


class ProgressDelegate(QStyledItemDelegate):
    ProgressRole = Qt.ItemDataRole.UserRole + 0x1000
    TextRole = Qt.ItemDataRole.UserRole + 0x1001

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Union[QModelIndex, QPersistentModelIndex]):
        progress = int(index.data(self.ProgressRole) * 10000)
        opt = QStyleOptionProgressBar()
        opt.rect = option.rect  # type: ignore
        opt.minimum = 0  # type: ignore
        opt.maximum = 10000  # type: ignore
        opt.progress = progress  # type: ignore
        opt.textAlignment = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter  # type: ignore
        if t := index.data(self.TextRole):
            opt.text = t  # type: ignore
        else:
            opt.text = "%.1f%%" % (progress / 100)  # type: ignore
        opt.textVisible = True  # type: ignore
        if sys.platform == "darwin" and ((fusion := QStyleFactory.create("Fusion")) is not None):
            fusion.drawControl(QStyle.ControlElement.CE_ProgressBar, opt, painter)
        else:
            QApplication.style().drawControl(QStyle.ControlElement.CE_ProgressBar, opt, painter)


# Modified from https://doc.qt.io/qtforpython-6/examples/example_widgets_itemviews_spinboxdelegate.html
class PercentSpinBoxDelegate(QStyledItemDelegate):
    """A delegate that allows the user to change integer values from the model
    using a spin box widget."""

    def __init__(self, parent=None, minimum=0, maximum=100, step=1):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step

    def createEditor(self, parent, option, index):
        editor = QSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        editor.setSingleStep(self.step)
        editor.setSuffix("%")
        return editor

    def setEditorData(self, editor: QSpinBox, index):  # type: ignore[override]
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        value = int(value[:-2])
        editor.setValue(value)

    def setModelData(self, editor: QSpinBox, model, index):  # type: ignore[override]
        editor.interpretText()
        value = editor.value()
        model.setData(index, str(value) + "%\u3000", Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor: QSpinBox, option, index):  # type: ignore[override]
        editor.setGeometry(option.rect)


class FileNameDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        PathRe = QRegularExpression(r"^[^\\/:*?\"<>|]+$")
        validator = QRegularExpressionValidator(PathRe)
        editor.setValidator(validator)
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor: QLineEdit, index):  # type: ignore[override]
        value = str(index.model().data(index, Qt.ItemDataRole.EditRole))
        editor.setText(value)

    def setModelData(self, editor: QLineEdit, model, index):  # type: ignore[override]
        value = editor.text()
        model.setData(index, value, Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor: QLineEdit, option, index):  # type: ignore[override]
        editor.setGeometry(option.rect)


class DoNothingDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None

    def setEditorData(self, editor, index):  # type: ignore[override]
        pass

    def setModelData(self, editor, model, index):  # type: ignore[override]
        pass

    def updateEditorGeometry(self, editor, option, index):  # type: ignore[override]
        pass


# A simpler QAction that can be created with a callback
class Action(QAction):
    def __init__(self, text, parent=None, callback=None):
        super().__init__(text, parent)
        self.triggered.connect(callback)
