from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QCursor

from config import get_font

class HoverLabel(QLabel):
    clicked = pyqtSignal()
    doubleClicked = pyqtSignal(object)
    
    def __init__(self, text, default_color, hover_color, font_size=16, is_bold=False, parent=None, target="default"):
        super().__init__(text, parent)
        self.default_color = default_color
        self.hover_color = hover_color
        font = get_font(font_size, target=target)
        if is_bold:
            font.setBold(True)
        self.setFont(font)
        self.setStyleSheet(f"color: {default_color}; background: transparent;")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
    def enterEvent(self, event):
        self.setStyleSheet(f"color: {self.hover_color}; background: transparent;")
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setStyleSheet(f"color: {self.default_color}; background: transparent;")
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() != Qt.KeyboardModifier.ControlModifier:
                self.clicked.emit()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(event)
        super().mouseDoubleClickEvent(event)
