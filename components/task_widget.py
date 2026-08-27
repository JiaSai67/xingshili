from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame, QMessageBox, QApplication, QGraphicsOpacityEffect, QLayout, QScrollArea, QAbstractScrollArea, QSizePolicy, QMenu, QInputDialog
from PyQt6.QtCore import Qt, QTimer, QEvent, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QMimeData, QPoint
from PyQt6.QtGui import QFont, QPixmap, QCursor, QDrag

from config import get_font, COLORS, hex_to_rgba, save_data, get_resource_path
from components.hover_label import HoverLabel

class AddParentButton(QWidget):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 15, 0, 15)
        
        is_memo = self.app_ref.is_project_memo_mode()
        lbl_text = "＋ 新增備忘項目" if is_memo else "＋ 新增母項目"
        self.lbl = HoverLabel(lbl_text, COLORS["divider_strong"], COLORS["accent_hover"], 14, True, parent=self)
        self.lbl.clicked.connect(self.add_parent)
        layout.addWidget(self.lbl)
        layout.addStretch()
        
    def add_parent(self):
        project_tasks = self.app_ref.projects.get(self.app_ref.current_project, [])
        new_task = {"text": "", "done": False, "children": []}
        project_tasks.append(new_task)
        
        tw = TaskWidget(new_task, 1, project_tasks, self.app_ref, is_new=True, parent=self.parentWidget())
        tw.hide()
        idx = self.app_ref.tasks_layout.indexOf(self)
        self.app_ref.tasks_layout.insertWidget(idx, tw)
        self.app_ref.animate_widget_enter(tw)

class TaskWidget(QWidget):
    def __init__(self, task_data, level, parent_list, app_ref, is_new=False, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        self.task_data = task_data
        self.level = level
        self.parent_list = parent_list
        self.app_ref = app_ref
        self._collapse_anim = None
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.header = QFrame(self)
        self.header.setObjectName("TaskHeader")
        self.header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.update_opacity_style()
        
        self.h_layout = QHBoxLayout(self.header)
        indent = (level - 1) * 35
        v_margin = 10 if level == 1 else 8
        self.h_layout.setContentsMargins(indent, v_margin, 0, v_margin)
        self.main_layout.addWidget(self.header)
        
        self.children_container = QWidget(self)
        self.children_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.children_container.setStyleSheet("background: transparent;")
        
        self.c_layout = QVBoxLayout(self.children_container)
        self.c_layout.setContentsMargins(0, 0, 0, 0)
        self.c_layout.setSpacing(0)
        
        self.main_layout.addWidget(self.children_container)
        
        if self.level == 1:
            self.divider = QFrame(self)
            self.divider.setFixedHeight(1)
            self.divider.setStyleSheet(f"background-color: {COLORS['divider']}; margin-right: 3px;")
            self.main_layout.addWidget(self.divider)
        
        # Setup Widgets Once
        self.lbl_collapse = QLabel("", self.header)
        self.lbl_collapse.setFont(get_font(14, target="task"))
        self.lbl_collapse.setStyleSheet(f"color: {COLORS['text_main']}; background: transparent;")
        self.lbl_collapse.setFixedWidth(20)
        self.h_layout.addWidget(self.lbl_collapse)
        
        self.lbl_icon = HoverLabel("☐", COLORS["text_main"], COLORS["accent_hover"], 18, parent=self.header)
        self.lbl_icon.clicked.connect(self.toggle_check)
        self.h_layout.addWidget(self.lbl_icon)
        
        font_size = 14 if self.level == 1 else (13 if self.level == 2 else 12)
        self.lbl_text = HoverLabel("", COLORS["text_main"], COLORS["accent_hover"], font_size, parent=self.header)
        font = self.lbl_text.font()
        font.setFamily("Segoe UI Variable Display, Microsoft YaHei UI")
        self.lbl_text.setFont(font)
        self.lbl_text.clicked.connect(self.toggle_collapse)
        self.lbl_text.doubleClicked.connect(self.on_text_double_click)
        self.h_layout.addWidget(self.lbl_text)
        
        self.editor = QLineEdit(self.header)
        self.editor.setFont(font)
        self.editor.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; 
                border: none;
                color: {COLORS['text_main']}; 
                padding: 0px;
            }}
        """)
        self.editor.installEventFilter(self)
        self.editor.editingFinished.connect(self.finalize_edit)
        self.h_layout.addWidget(self.editor)
        self.editor.hide()
        
        self.h_layout.addStretch()
        
        if self.level < 3:
            self.btn_add = HoverLabel("＋", "transparent", COLORS["accent_hover"], 16, parent=self.header)
            self.btn_add.clicked.connect(self.add_subtask)
            self.h_layout.addWidget(self.btn_add)
            
        self.btn_del = HoverLabel("×", "transparent", COLORS["accent_hover"], 18, parent=self.header)
        self.btn_del.clicked.connect(self.delete_task)
        self.h_layout.addWidget(self.btn_del)
        self.h_layout.addSpacing(10)
        
        self.header.installEventFilter(self)
        
        self.render_children()
        self.update_view()
        if is_new:
            self.setup_edit_mode()

    def update_opacity_style(self):
        opacity = self.app_ref.projects.get("__settings__", {}).get("task_opacity", 0.75)
        bg_color = hex_to_rgba(COLORS['card_bg'], opacity)
        bg_hover = hex_to_rgba(COLORS['card_bg'], min(1.0, opacity + 0.2))
        self.header.setStyleSheet(f"""
            #TaskHeader {{
                background-color: {bg_color};
                border-radius: 8px;
                margin: 2px 10px 2px 0px;
            }}
            #TaskHeader:hover {{
                background-color: {bg_hover};
            }}
        """)

    def update_view(self):
        text = self.task_data.get("text", "")
        self.lbl_text.setText(text)
        
        is_memo = self.app_ref.is_project_memo_mode()
        if is_memo:
            self.lbl_icon.hide()
            self.lbl_text.default_color = COLORS["text_main"]
            self.lbl_text.setStyleSheet(f"color: {COLORS['text_main']}; background: transparent;")
            font = self.lbl_text.font()
            font.setStrikeOut(False)
            self.lbl_text.setFont(font)
        else:
            self.lbl_icon.show()
            self.is_done = self.task_data.get("done", False)
            if self.is_done:
                self.lbl_icon.setText("")
                self.lbl_icon.setPixmap(QPixmap(get_resource_path("assets/cat_paw.svg")).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                color = COLORS["text_done"]
            else:
                self.lbl_icon.setPixmap(QPixmap())
                self.lbl_icon.setText("☐")
                color = COLORS["text_main"]
            
            self.lbl_icon.default_color = color
            self.lbl_icon.setStyleSheet(f"color: {color}; background: transparent;")
            
            self.lbl_text.default_color = color
            self.lbl_text.setStyleSheet(f"color: {color}; background: transparent;")
            font = self.lbl_text.font()
            font.setStrikeOut(self.is_done)
            self.lbl_text.setFont(font)
        
        has_children = len(self.task_data.get("children", [])) > 0
        is_collapsed = self.task_data.get("collapsed", False)
        collapse_char = ""
        if has_children:
            collapse_char = "▸" if is_collapsed else "▾"
        self.lbl_collapse.setText(collapse_char)
        
        if not has_children:
            self.children_container.setVisible(False)
            
        self.editor.hide()
        self.lbl_text.show()
        
    def setup_edit_mode(self):
        self.editor.setText(self.task_data.get("text", ""))
        self.lbl_text.hide()
        self.editor.show()
        QTimer.singleShot(50, self.editor.setFocus)
        
    def cancel_edit(self):
        is_new = (self.task_data.get("text", "") == "")
        if is_new:
            if self.task_data in self.parent_list:
                self.parent_list.remove(self.task_data)
            self.app_ref.animate_widget_exit(self)
        else:
            self.update_view()

    def finalize_edit(self):
        if not self.editor.isVisible(): return
        
        text = self.editor.text().strip()
        is_new = (self.task_data.get("text", "") == "")
        
        if not text:
            if is_new:
                if self.task_data in self.parent_list:
                    self.parent_list.remove(self.task_data)
                self.app_ref.animate_widget_exit(self)
                return
            else:
                pass # keep old text
        else:
            self.task_data["text"] = text
            save_data(self.app_ref.projects)
            
        self.update_view()

    def eventFilter(self, obj, event):
        if obj == self.header and not self.editor.isVisible():
            if event.type() == QEvent.Type.Enter:
                self.btn_del.setStyleSheet(f"color: {COLORS['divider_strong']}; background: transparent;")
                if self.level < 3:
                    self.btn_add.setStyleSheet(f"color: {COLORS['divider_strong']}; background: transparent;")
            elif event.type() == QEvent.Type.Leave:
                self.btn_del.setStyleSheet("color: transparent; background: transparent;")
                if self.level < 3:
                    self.btn_add.setStyleSheet("color: transparent; background: transparent;")
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.drag_start_pos = event.pos()
                    if event.modifiers() != Qt.KeyboardModifier.ControlModifier:
                        self.toggle_collapse()
            elif event.type() == QEvent.Type.MouseMove:
                if hasattr(self, 'drag_start_pos') and event.buttons() & Qt.MouseButton.LeftButton:
                    if (event.pos() - self.drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                        self.start_drag()
                        return True
        elif obj == self.editor:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    self.cancel_edit()
                    return True
        return super().eventFilter(obj, event)
        
    def on_text_double_click(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.setup_edit_mode()
            
    def toggle_collapse(self):
        if not self.task_data.get("children"): return
        is_collapsed = self.task_data.get("collapsed", False)
        self.task_data["collapsed"] = not is_collapsed
        save_data(self.app_ref.projects)
        
        QTimer.singleShot(0, self._apply_collapse)
        
    def _apply_collapse(self):
        # Freeze screen updates on both the main app and the scroll viewport
        self.app_ref.setUpdatesEnabled(False)
        self.app_ref.tasks_scroll.viewport().setUpdatesEnabled(False)
        
        self.update_view()
        self.children_container.setVisible(not self.task_data["collapsed"])
            
        # Unfreeze screen updates
        self.app_ref.tasks_scroll.viewport().setUpdatesEnabled(True)
        self.app_ref.setUpdatesEnabled(True)

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
        action = menu.addAction("⭐ 加入我的最愛")
        selected = menu.exec(event.globalPos())
        if selected == action:
            self.add_to_favorites()

    def add_to_favorites(self):
        default_name = self.task_data.get("text", "")
        name, ok = QInputDialog.getText(self, "加入我的最愛", "請輸入最愛名稱:", text=default_name)
        if ok and name:
            settings = self.app_ref.projects.get("__settings__", {})
            favs = settings.get("favorites", [])
            fav = {"name": name, "type": "task", "project": self.app_ref.current_project, "task_id": self.task_data["id"]}
            favs.append(fav)
            settings["favorites"] = favs
            self.app_ref.projects["__settings__"] = settings
            save_data(self.app_ref.projects)
            self.app_ref.refresh_favorites()

    def toggle_check(self):
        if self.app_ref.is_project_memo_mode():
            return
        new_state = not self.task_data.get("done", False)
        def update_data_recursive(t, state):
            t["done"] = state
            for c in t.get("children", []):
                update_data_recursive(c, state)
                
        update_data_recursive(self.task_data, new_state)
        save_data(self.app_ref.projects)
        self.refresh_view_recursive()

    def start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        group_id = str(id(self.parent_list))
        my_index = self.parent_list.index(self.task_data)
        mime.setText(f"TASK:{group_id}:{my_index}")
        drag.setMimeData(mime)
        
        pixmap = self.header.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("TASK:"):
            _, group_id, _ = event.mimeData().text().split(":")
            if group_id == str(id(self.parent_list)):
                event.acceptProposedAction()
                bg_drag = hex_to_rgba(COLORS['card_bg'], 0.95)
                self.header.setStyleSheet(f"""
                    #TaskHeader {{
                        background-color: {bg_drag};
                        border: 2px dashed {COLORS['accent']};
                        border-radius: 8px;
                        margin: 2px 10px 2px 0px;
                    }}
                """)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("TASK:"):
            _, group_id, _ = event.mimeData().text().split(":")
            if group_id == str(id(self.parent_list)):
                event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.update_opacity_style()

    def dropEvent(self, event):
        text = event.mimeData().text()
        if text.startswith("TASK:"):
            _, group_id, drag_index_str = text.split(":")
            if group_id == str(id(self.parent_list)):
                drag_index = int(drag_index_str)
                drop_index = self.parent_list.index(self.task_data)
                
                if event.position().y() > self.header.height() / 2:
                    drop_index += 1
                    
                if drag_index != drop_index and drag_index + 1 != drop_index:
                    item = self.parent_list.pop(drag_index)
                    if drop_index > drag_index:
                        drop_index -= 1
                    self.parent_list.insert(drop_index, item)
                    save_data(self.app_ref.projects)
                    self.app_ref.render_tasks_no_anim()
                    
                event.acceptProposedAction()
        self.dragLeaveEvent(event)

    def refresh_view_recursive(self):
        self.update_view()
        for i in range(self.c_layout.count()):
            item = self.c_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), TaskWidget):
                item.widget().refresh_view_recursive()

    def add_subtask(self):
        if "children" not in self.task_data:
            self.task_data["children"] = []
        new_task = {"text": "", "done": False, "children": []}
        self.task_data["children"].append(new_task)
        
        self.update_view()
        if self.task_data.get("collapsed", False):
            self.toggle_collapse()
        else:
            self.children_container.setVisible(True)
            
        new_widget = TaskWidget(new_task, self.level + 1, self.task_data["children"], self.app_ref, is_new=True, parent=self.children_container)
        new_widget.hide()
        self.c_layout.addWidget(new_widget)
        self.app_ref.animate_widget_enter(new_widget)
        
        # Must re-calculate target height if expanding! Actually toggle_collapse handled it if it was collapsed.
        # But if it was already expanded, we just added a child. No height anim needed for parent, QVBoxLayout handles it natively.

    def delete_task(self):
        if self.task_data in self.parent_list:
            self.parent_list.remove(self.task_data)
            save_data(self.app_ref.projects)
            
            # update parent view so if last child is deleted, the collapse arrow goes away
            parent_tw = self.parentWidget().parentWidget() if self.parentWidget() else None
            if hasattr(parent_tw, 'update_view'):
                parent_tw.update_view()
                
            self.app_ref.animate_widget_exit(self)

    def render_children(self):
        while self.c_layout.count():
            item = self.c_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        children = self.task_data.get("children", [])
        for child_data in children:
            cw = TaskWidget(child_data, self.level + 1, children, self.app_ref, parent=self.children_container)
            self.c_layout.addWidget(cw)
            
        has_children = len(children) > 0
        is_collapsed = self.task_data.get("collapsed", False)
        
        if not has_children or is_collapsed:
            self.children_container.setVisible(False)
        else:
            self.children_container.setVisible(True)
