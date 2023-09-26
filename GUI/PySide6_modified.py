# Demucs-GUI
# Copyright (C) 2022-2023  Carl Gao, Jize Guo, Rosario S.E.

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

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QStyle,
    QStyledItemDelegate,
    QStyleOption,
    QStyleOptionProgressBar,
    QStyleOptionViewItem,
)

from typing import Union


class ModifiedQLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.textalignment = Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWrapAnywhere
        self.isTextLabel = True
        self.align = None

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)

        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

        self.style().drawItemText(painter, self.rect(), self.textalignment, self.palette(), True, self.text())


class ProgressDelegate(QStyledItemDelegate):
    ProgressRole = Qt.ItemDataRole.UserRole + 0x1000
    TextRole = Qt.ItemDataRole.UserRole + 0x1001

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Union[QModelIndex, QPersistentModelIndex]):
        progress = int(index.data(self.ProgressRole) * 1000)
        opt = QStyleOptionProgressBar()
        opt.rect = option.rect  # type: ignore
        opt.minimum = 0  # type: ignore
        opt.maximum = 1000  # type: ignore
        opt.progress = progress  # type: ignore
        opt.textAlignment = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter  # type: ignore
        if t := index.data(self.TextRole):
            opt.text = t  # type: ignore
        else:
            opt.text = "%.1f%%" % (progress / 10)  # type: ignore
        opt.textVisible = True  # type: ignore
        QApplication.style().drawControl(QStyle.ControlElement.CE_ProgressBar, opt, painter)
