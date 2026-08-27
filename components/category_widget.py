from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QCursor
from config import get_font, COLORS, hex_to_rgba, save_data

class CategoryWidget(QWidget):
    def __init__(self, name, items, app_ref, is_uncategorized=False, parent=None):
        super().__init__(parent)
        self.name = name
        self.items = items
        self.app_ref = app_ref
        self.is_uncategorized = is_uncategorized
        self.setAcceptDrops(True)
        
        from PyQt6.QtWidgets import QApplication, QFrame
        self.placeholder = QFrame()
        self.placeholder.setFixedHeight(3)
        self.placeholder.setStyleSheet(f"background-color: {COLORS['accent']}; margin: 0px 10px;")
        self.placeholder.hide()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 10)
        self.layout.setSpacing(0)
        
        # Header
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(25, 0, 25, 5)
        
        self.btn_toggle = QPushButton("-")
        self.btn_toggle.setFixedSize(16, 16)
        self.btn_toggle.setStyleSheet(f"background: transparent; border: none; color: {COLORS['text_main']}; font-weight: bold; padding: 0px;")
        self.btn_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        
        header_layout.addWidget(self.btn_toggle)
        
        if is_uncategorized:
            self.lbl_name = QLabel(f"{name} ({len(items)})")
            self.lbl_name.setFont(get_font(11, QFont.Weight.Bold, target="sidebar"))
            self.lbl_name.setStyleSheet(f"color: {COLORS['text_main']}; background: transparent;")
            header_layout.addWidget(self.lbl_name)
        else:
            from components.hover_label import HoverLabel
            self.lbl_name = HoverLabel(f"{name} ({len(items)})", COLORS["text_main"], COLORS["accent_hover"], 11, parent=self)
            font = self.lbl_name.font()
            font.setFamily("Segoe UI Variable Display, Microsoft YaHei UI")
            font.setBold(True)
            self.lbl_name.setFont(font)
            self.lbl_name.doubleClicked.connect(self.start_edit)
            header_layout.addWidget(self.lbl_name)
            
            self.editor = QLineEdit(self)
            self.editor.setFont(font)
            self.editor.setStyleSheet(f"background: transparent; border: 1px solid {COLORS['divider_strong']}; color: {COLORS['text_main']}; padding: 0px;")
            self.editor.hide()
            self.editor.editingFinished.connect(self.finish_edit)
            header_layout.addWidget(self.editor)
            
        header_layout.addStretch()
        
        if not is_uncategorized:
            self.btn_del = QPushButton("×")
            self.btn_del.setFixedSize(20, 20)
            self.btn_del.setStyleSheet(f"background: transparent; border: none; color: {COLORS['divider_strong']}; font-weight: bold; font-size: 14px;")
            self.btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.btn_del.clicked.connect(self.delete_category)
            header_layout.addWidget(self.btn_del)
            
        self.layout.addWidget(self.header)
        
        # Container
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        self.layout.addWidget(self.container)
        
        self.populate_items()
        
        self.is_collapsed = self.app_ref.projects.get("__settings__", {}).get("collapsed_categories", {}).get(self.name, False)
        if self.is_collapsed:
            self.container.hide()
            self.btn_toggle.setText("+")
            
    def populate_items(self):
        from components.project_button import ProjectButton
        from components.favorite_button import FavoriteButton
        
        for i, item in enumerate(self.items):
            if isinstance(item, dict) and item.get("type") == "task":
                btn = FavoriteButton(item, self.app_ref, category_name=self.name, item_index=i)
                self.container_layout.addWidget(btn)
            else:
                proj_name = item.get("target") if isinstance(item, dict) else item
                if proj_name in self.app_ref.projects:
                    btn = ProjectButton(proj_name, self.app_ref, category_name=self.name, item_index=i)
                    self.app_ref.proj_widgets.append(btn)
                    self.container_layout.addWidget(btn)
                
    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self.container.setVisible(not self.is_collapsed)
        self.btn_toggle.setText("+" if self.is_collapsed else "-")
        
        settings = self.app_ref.projects.get("__settings__", {})
        if "collapsed_categories" not in settings:
            settings["collapsed_categories"] = {}
        settings["collapsed_categories"][self.name] = self.is_collapsed
        self.app_ref.save_data_debounced()
        
    def start_edit(self):
        self.editor.setText(self.name)
        self.lbl_name.hide()
        self.editor.show()
        QTimer.singleShot(50, self.editor.setFocus)
        
    def finish_edit(self):
        if not self.editor.isVisible(): return
        new_name = self.editor.text().strip()
        self.editor.hide()
        self.lbl_name.show()
        
        if new_name and new_name != self.name:
            settings = self.app_ref.projects.get("__settings__", {})
            cats = settings.get("categories", {})
            if new_name not in cats:
                cats[new_name] = cats.pop(self.name)
                
                collapsed = settings.get("collapsed_categories", {})
                if self.name in collapsed:
                    collapsed[new_name] = collapsed.pop(self.name)
                    
                self.app_ref.save_data_debounced()
                self.app_ref.refresh_projects()
                return
        self.lbl_name.setText(f"{self.name} ({len(self.items)})")
        
    def delete_category(self):
        settings = self.app_ref.projects.get("__settings__", {})
        cats = settings.get("categories", {})
        if self.name in cats:
            del cats[self.name]
            
            collapsed = settings.get("collapsed_categories", {})
            if self.name in collapsed:
                del collapsed[self.name]
                
            self.app_ref.save_data_debounced()
            self.app_ref.refresh_projects()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("CAT_ITEM:"):
            event.acceptProposedAction()
            self.header.setStyleSheet(f"background-color: {hex_to_rgba(COLORS['bg_active'], 0.4)};")

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("CAT_ITEM:"):
            event.acceptProposedAction()
            
            pos = event.position().toPoint()
            drop_real_index = -1
            real_index = 0
            for i in range(self.container_layout.count()):
                item = self.container_layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    if w == self.placeholder: continue
                    mapped_pos = self.container.mapFrom(self, pos)
                    if mapped_pos.y() < w.y() + w.height() / 2:
                        drop_real_index = real_index
                        break
                    real_index += 1
                        
            if drop_real_index == -1:
                drop_real_index = real_index
                
            current_index = self.container_layout.indexOf(self.placeholder)
            if current_index != drop_real_index:
                self.container_layout.removeWidget(self.placeholder)
                self.container_layout.insertWidget(drop_real_index, self.placeholder)
                self.placeholder.show()

    def dragLeaveEvent(self, event):
        self.header.setStyleSheet("background: transparent;")
        self.placeholder.hide()

    def dropEvent(self, event):
        self.header.setStyleSheet("background: transparent;")
        self.placeholder.hide()
        text = event.mimeData().text()
        if text.startswith("CAT_ITEM:"):
            _, src_cat_name, src_index_str = text.split(":", 2)
            src_index = int(src_index_str)
            
            # Find drop index
            pos = event.position().toPoint()
            drop_index = -1
            real_index = 0
            for i in range(self.container_layout.count()):
                item = self.container_layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    if w == self.placeholder: continue
                    mapped_pos = self.container.mapFrom(self, pos)
                    if mapped_pos.y() < w.y() + w.height() / 2:
                        drop_index = real_index
                        break
                    real_index += 1
                        
            if drop_index == -1:
                drop_index = real_index
                
            settings = self.app_ref.projects.get("__settings__", {})
            cats = settings.get("categories", {})
            
            # Handle moving from uncategorized
            src_items = []
            if src_cat_name == "未歸類":
                categorized_projects = set()
                for cat_name, items in cats.items():
                    for item in items:
                        if isinstance(item, dict) and item.get("type") == "project":
                            categorized_projects.add(item.get("target"))
                        elif isinstance(item, str):
                            categorized_projects.add(item)
                uncategorized = []
                for p in self.app_ref.projects.keys():
                    if p == "__settings__": continue
                    if p not in categorized_projects:
                        uncategorized.append(p)
                src_items = uncategorized
            else:
                src_items = cats.get(src_cat_name, [])
                
            if src_index >= len(src_items):
                return
                
            item_to_move = src_items.pop(src_index)
            
            target_items = cats.setdefault(self.name, []) if not self.is_uncategorized else []
            
            if not self.is_uncategorized:
                # If dropping into same category, adjust drop_index
                if self.name == src_cat_name and drop_index > src_index:
                    drop_index -= 1
                target_items.insert(drop_index, item_to_move)
            else:
                # Target is Uncategorized
                if self.name == src_cat_name and drop_index > src_index:
                    drop_index -= 1
                    
                proj_name = item_to_move.get("target") if isinstance(item_to_move, dict) else item_to_move
                if not isinstance(proj_name, str): return
                
                current_uncat = []
                for p in self.app_ref.projects.keys():
                    if p == "__settings__": continue
                    if p not in categorized_projects and p != proj_name:
                        current_uncat.append(p)
                        
                current_uncat.insert(drop_index, proj_name)
                
                new_projects = {}
                if "__settings__" in self.app_ref.projects:
                    new_projects["__settings__"] = self.app_ref.projects["__settings__"]
                    
                for p, v in self.app_ref.projects.items():
                    if p in categorized_projects and p != proj_name:
                        new_projects[p] = v
                        
                for p in current_uncat:
                    if p in self.app_ref.projects:
                        new_projects[p] = self.app_ref.projects[p]
                        
                self.app_ref.projects = new_projects
                
            self.app_ref.save_data_debounced()
            self.app_ref.refresh_projects()
            event.acceptProposedAction()
