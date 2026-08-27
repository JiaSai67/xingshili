from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QApplication, QMenu, QInputDialog, QMessageBox
from PyQt6.QtCore import Qt, QEvent, QTimer, pyqtProperty, QPropertyAnimation, QEasingCurve, QMimeData
from PyQt6.QtGui import QFont, QCursor, QColor, QDrag

from config import get_font, COLORS, hex_to_rgba, save_data
from components.hover_label import HoverLabel

class ProjectButton(QWidget):
    def __init__(self, name, app_ref, is_new=False, category_name=None, item_index=-1, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.name = name
        self.app_ref = app_ref
        self.category_name = category_name
        self.item_index = item_index
        
        self._shake_offset = 0
        self._err_color = QColor(COLORS["text_main"])
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(25, 12, 15, 12)
        
        self.lbl = HoverLabel(self.name, COLORS["text_main"], COLORS["accent_hover"], 14, parent=self)
        font = self.lbl.font()
        font.setFamily("Segoe UI Variable Display, Microsoft YaHei UI")
        self.lbl.setFont(font)
        self.lbl.clicked.connect(self.select_project)
        self.lbl.doubleClicked.connect(self.on_text_double_click)
        self.layout.addWidget(self.lbl)
        
        self.editor = QLineEdit(self)
        self.editor.setFont(font)
        self.editor.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; 
                border: none;
                color: {self._err_color.name()}; 
                padding: 0px;
            }}
        """)
        self.editor.editingFinished.connect(self.finalize_edit)
        self.editor.installEventFilter(self)
        self.layout.addWidget(self.editor)
        self.editor.hide()
        
        self.layout.addStretch()
        
        self.btn_del = HoverLabel("×", "transparent", COLORS["accent_hover"], 16, parent=self)
        self.btn_del.clicked.connect(self.delete_project)
        self.layout.addWidget(self.btn_del)
        
        self.is_active = False
        self.installEventFilter(self)
        
        self.update_view()
        if is_new:
            self.setup_edit_mode()

    def update_view(self):
        self.lbl.setText(self.name)
        self.editor.hide()
        self.lbl.show()
        self.update_style(self.app_ref.current_project == self.name)
        
    def setup_edit_mode(self):
        self.editor.setText(self.name)
        self.lbl.hide()
        self.editor.show()
        QTimer.singleShot(50, self.editor.setFocus)
        
    def cancel_edit(self):
        is_new = (self.name == "")
        if is_new:
            if self in self.app_ref.proj_widgets:
                self.app_ref.proj_widgets.remove(self)
            self.app_ref.animate_widget_exit(self)
        else:
            self.update_view()

    def select_project(self):
        if not self.editor.isVisible():
            self.app_ref.load_project(self.name)
        
    def delete_project(self):
        if not self.editor.isVisible():
            self.app_ref.delete_project(self.name)
        
    def update_style(self, is_active):
        self.is_active = is_active
        if is_active and not self.editor.isVisible():
            self.setStyleSheet(f"background-color: {COLORS['bg_active']};")
            self.lbl.default_color = COLORS["text_title"]
            font = self.lbl.font()
            font.setBold(True)
            self.lbl.setFont(font)
        else:
            self.setStyleSheet("background-color: transparent;")
            self.lbl.default_color = COLORS["text_main"]
            font = self.lbl.font()
            font.setBold(False)
            self.lbl.setFont(font)
            
        if not self.editor.isVisible():
            self.lbl.setStyleSheet(f"color: {self.lbl.default_color}; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self.editor.isVisible():
            return
        if not hasattr(self, 'drag_start_pos'):
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime = QMimeData()
        cat = self.category_name if self.category_name else "未歸類"
        mime.setText(f"CAT_ITEM:{cat}:{self.item_index}")
        drag.setMimeData(mime)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        drag.exec(Qt.DropAction.MoveAction)
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['bg_right']};
                border: 1px solid {COLORS['divider_strong']};
                color: {COLORS['text_main']};
            }}
            QMenu::item:selected {{
                background-color: {COLORS['bg_active']};
            }}
        """)
        
        settings = self.app_ref.projects.get("__settings__", {})
        categories = settings.get("categories", {})
        
        cat_menu = menu.addMenu("📁 加入分類")
        
        # Determine which categories this project is already in
        current_cats = []
        for cat_name, items in categories.items():
            if any((isinstance(f, dict) and f.get("target") == self.name) or (isinstance(f, str) and f == self.name) for f in items):
                current_cats.append(cat_name)
                
        has_other_cats = False
        for cat_name in categories.keys():
            if cat_name not in current_cats:
                action = cat_menu.addAction(cat_name)
                action.triggered.connect(lambda checked, c=cat_name: self.add_to_category(c))
                has_other_cats = True
                
        if has_other_cats:
            cat_menu.addSeparator()
            
        action_new_cat = cat_menu.addAction("+ 新增分類")
        action_new_cat.triggered.connect(self.create_new_category)
        
        if current_cats:
            rm_menu = menu.addMenu("❌ 從分類移除")
            for c in current_cats:
                action = rm_menu.addAction(c)
                action.triggered.connect(lambda checked, cat=c: self.remove_from_category(cat))
                
        menu.exec(event.globalPos())

    def add_to_category(self, cat_name):
        settings = self.app_ref.projects.get("__settings__", {})
        cats = settings.get("categories", {})
        if cat_name not in cats:
            cats[cat_name] = []
            
        cats[cat_name].append({"name": self.name, "type": "project", "target": self.name})
        save_data(self.app_ref.projects)
        self.app_ref.refresh_projects()

    def remove_from_category(self, cat_name):
        settings = self.app_ref.projects.get("__settings__", {})
        cats = settings.get("categories", {})
        if cat_name in cats:
            cats[cat_name] = [
                i for i in cats[cat_name] 
                if not ((isinstance(i, dict) and i.get("target") == self.name) or (isinstance(i, str) and i == self.name))
            ]
            save_data(self.app_ref.projects)
            self.app_ref.refresh_projects()

    def create_new_category(self):
        text, ok = QInputDialog.getText(self.app_ref, "新增分類", "請輸入新分類名稱：")
        if ok and text.strip():
            cat_name = text.strip()
            settings = self.app_ref.projects.get("__settings__", {})
            cats = settings.setdefault("categories", {})
            if cat_name not in cats:
                cats[cat_name] = []
            
            self.add_to_category(cat_name)

    def eventFilter(self, obj, event):
        if obj == self and not self.editor.isVisible():
            if event.type() == QEvent.Type.Enter:
                if not self.is_active:
                    self.setStyleSheet(f"background-color: {hex_to_rgba(COLORS['bg_active'], 0.4)};")
                self.btn_del.setStyleSheet(f"color: {COLORS['divider_strong']}; background: transparent;")
            elif event.type() == QEvent.Type.Leave:
                if not self.is_active:
                    self.setStyleSheet("background-color: transparent;")
                self.btn_del.setStyleSheet("color: transparent; background: transparent;")
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.select_project()
        elif obj == self.editor:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    self.cancel_edit()
                    return True
        return super().eventFilter(obj, event)

    def on_text_double_click(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.setup_edit_mode()

    def finalize_edit(self):
        if not self.editor.isVisible(): return
        
        new_name = self.editor.text().strip()
        is_new = (self.name == "")
        
        if not new_name:
            if is_new:
                if self in self.app_ref.proj_widgets:
                    self.app_ref.proj_widgets.remove(self)
                self.app_ref.animate_widget_exit(self)
                return
            else:
                new_name = self.name
        else:
            if new_name != self.name and new_name in self.app_ref.projects:
                self.shake_and_flash_error()
                self.editor.setFocus()
                return
            
            if new_name != self.name:
                if not is_new:
                    new_projects = {}
                    for k, v in self.app_ref.projects.items():
                        if k == self.name:
                            new_projects[new_name] = v
                        else:
                            new_projects[k] = v
                    self.app_ref.projects = new_projects
                    if self.app_ref.current_project == self.name:
                        self.app_ref.current_project = new_name
                else:
                    self.app_ref.projects[new_name] = []
                    
                self.name = new_name
                save_data(self.app_ref.projects)
                
        self.update_view()
        if is_new:
            self.app_ref.refresh_projects()
            self.app_ref.load_project(self.name)
        else:
            if self.app_ref.current_project == self.name:
                self.app_ref.lbl_right_title.setText(self.name)

    def get_shake_offset(self):
        return self._shake_offset
        
    def set_shake_offset(self, offset):
        self._shake_offset = offset
        self.layout.setContentsMargins(25 + offset, 12, 15 - offset, 12)
        
    shake_offset = pyqtProperty(int, get_shake_offset, set_shake_offset)

    def get_err_color(self):
        return self._err_color
        
    def set_err_color(self, color):
        self._err_color = color
        if hasattr(self, 'editor'):
            self.editor.setStyleSheet(f"""
                QLineEdit {{
                    background: transparent; 
                    border: none;
                    color: {color.name()}; 
                    padding: 0px;
                }}
            """)
            
    err_color = pyqtProperty(QColor, get_err_color, set_err_color)

    def shake_and_flash_error(self):
        self.anim_shake = QPropertyAnimation(self, b"shake_offset", self)
        self.anim_shake.setDuration(400)
        self.anim_shake.setKeyValueAt(0, 0)
        self.anim_shake.setKeyValueAt(0.1, 5)
        self.anim_shake.setKeyValueAt(0.3, -5)
        self.anim_shake.setKeyValueAt(0.5, 5)
        self.anim_shake.setKeyValueAt(0.7, -5)
        self.anim_shake.setKeyValueAt(0.9, 5)
        self.anim_shake.setKeyValueAt(1, 0)
        
        self.anim_color = QPropertyAnimation(self, b"err_color", self)
        self.anim_color.setDuration(400)
        self.anim_color.setStartValue(QColor(COLORS["text_main"]))
        self.anim_color.setKeyValueAt(0.5, QColor(COLORS["error"]))
        self.anim_color.setEndValue(QColor(COLORS["text_main"]))
        
        self.anim_shake.start()
        self.anim_color.start()
