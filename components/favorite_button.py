from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, QEvent, QTimer, QMimeData
from PyQt6.QtGui import QFont, QCursor, QDrag

from config import get_font, COLORS, hex_to_rgba, save_data

class FavoriteButton(QWidget):
    def __init__(self, fav_data, app_ref, category_name=None, item_index=-1):
        super().__init__()
        self.fav_data = fav_data
        self.app_ref = app_ref
        self.category_name = category_name
        self.item_index = item_index
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 8, 15, 8)
        
        self.lbl = QLabel("⭐ " + fav_data["name"])
        self.lbl.setFont(get_font(11, target="sidebar"))
        self.lbl.setStyleSheet(f"color: {COLORS['text_main']}; background: transparent;")
        layout.addWidget(self.lbl)
        
        self.btn_del = QPushButton("×")
        self.btn_del.setFixedSize(20, 20)
        self.btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_del.setStyleSheet("color: transparent; background: transparent; border: none;")
        self.btn_del.clicked.connect(self.remove_fav)
        layout.addWidget(self.btn_del)
        
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.installEventFilter(self)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, 'drag_start_pos'):
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime = QMimeData()
        cat = self.category_name if self.category_name else "我的最愛"
        mime.setText(f"CAT_ITEM:{cat}:{self.item_index}")
        drag.setMimeData(mime)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        drag.exec(Qt.DropAction.MoveAction)
        
    def eventFilter(self, obj, event):
        if obj == self:
            if event.type() == QEvent.Type.Enter:
                self.setStyleSheet(f"background-color: {hex_to_rgba(COLORS['bg_active'], 0.4)};")
                self.btn_del.setStyleSheet(f"color: {COLORS['divider_strong']}; background: transparent;")
            elif event.type() == QEvent.Type.Leave:
                self.setStyleSheet("background-color: transparent;")
                self.btn_del.setStyleSheet("color: transparent; background: transparent;")
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.activate_fav()
        return super().eventFilter(obj, event)
        
    def activate_fav(self):
        fav_type = self.fav_data["type"]
        if fav_type == "project":
            if self.fav_data["target"] in self.app_ref.projects:
                self.app_ref.load_project(self.fav_data["target"])
        elif fav_type == "task":
            proj_name = self.fav_data["project"]
            if proj_name in self.app_ref.projects:
                self.app_ref.load_project(proj_name)
                # Need to highlight/scroll to the task
                QTimer.singleShot(100, lambda: self.app_ref.highlight_task(self.fav_data["task_id"]))
                
    def remove_fav(self):
        settings = self.app_ref.projects.get("__settings__", {})
        cats = settings.get("categories", {})
        cat_name = self.category_name or "我的最愛"
        
        if cat_name in cats:
            if self.fav_data in cats[cat_name]:
                cats[cat_name].remove(self.fav_data)
                save_data(self.app_ref.projects)
                self.app_ref.refresh_projects()
