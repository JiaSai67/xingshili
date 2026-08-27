import os
import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QScrollArea, QFrame, QInputDialog, QMessageBox, 
                             QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QLayout, QFileDialog,
                             QSlider, QMenu, QDialog, QListWidget, QStackedWidget, QComboBox, QListWidgetItem)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QEvent, QTimer, QByteArray
from PyQt6.QtGui import QFont, QCursor, QIcon, QPainter, QPixmap, QColor, QFontDatabase

from config import get_font, COLORS, hex_to_rgba, load_data, save_data, get_resource_path, GLOBAL_SETTINGS
from components.project_button import ProjectButton
from components.task_widget import TaskWidget, AddParentButton
from components.favorite_button import FavoriteButton
from components.category_widget import CategoryWidget

class SettingsDialog(QDialog):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.setWindowTitle("設定")
        self.setStyleSheet(f"background-color: {COLORS['bg_right']}; color: {COLORS['text_main']};")
        self.setMinimumSize(480, 320)
        
        from PyQt6.QtCore import QByteArray
        settings = self.app_ref.projects.get("__settings__", {})
        saved_geom = settings.get("settings_geometry")
        if saved_geom:
            self.restoreGeometry(QByteArray.fromBase64(saved_geom.encode()))
        else:
            self.resize(550, 400)
        
        outer_layout = QVBoxLayout(self)
        
        main_layout = QHBoxLayout()
        
        from PyQt6.QtWidgets import QListWidget, QStackedWidget, QComboBox, QWidget, QListWidgetItem
        import os
        
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(130)
        self.list_widget.addItem("字體")
        self.list_widget.addItem("透明度")
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_left']};
                border: 1px solid {COLORS['divider_strong']};
                border-radius: 6px;
                outline: 0;
            }}
            QListWidget::item {{
                padding: 12px 10px;
                border-radius: 4px;
                margin: 2px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['accent']};
                color: {COLORS['white']};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {COLORS['bg_active']};
            }}
        """)
        self.list_widget.currentRowChanged.connect(self.switch_page)
        
        self.stacked_widget = QStackedWidget()
        
        self.page_font = QWidget()
        font_layout = QVBoxLayout(self.page_font)
        
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        lbl_font = QLabel("字體設定")
        lbl_font.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        lbl_font.setStyleSheet(f"color: {COLORS['accent']};")
        scroll_layout.addWidget(lbl_font)
        
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet(f"background-color: {COLORS['divider_strong']}; margin-bottom: 10px;")
        scroll_layout.addWidget(div1)
        
        settings = self.app_ref.projects.get("__settings__", {})
        
        # Helper to create a targeted font setting section
        self.font_combos = {}
        self.font_sliders = {}
        self.font_val_labels = {}
        
        def create_target_section(target_id, target_name):
            sec_layout = QVBoxLayout()
            sec_title = QLabel(f"{target_name} 字體:")
            sec_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            sec_layout.addWidget(sec_title)
            
            combo = QComboBox()
            combo.setStyleSheet(f"padding: 6px; border: 1px solid {COLORS['divider_strong']}; border-radius: 4px;")
            combo.addItem("繼承全域字體" if target_id != "default" else "預設字體 (Segoe UI)", "default")
            
            font_dir = get_resource_path("fonts")
            if os.path.exists(font_dir):
                for f in os.listdir(font_dir):
                    if f.lower().endswith(('.ttf', '.otf')):
                        combo.addItem(os.path.splitext(f)[0], f)
                        
            curr_font = settings.get(f"{target_id}_font_file", "default") if target_id != "default" else settings.get("font_file", "default")
            idx = combo.findData(curr_font)
            if idx >= 0: combo.setCurrentIndex(idx)
            combo.setProperty("target_id", target_id)
            combo.currentIndexChanged.connect(self.on_font_combo_changed)
            sec_layout.addWidget(combo)
            
            size_layout = QHBoxLayout()
            size_layout.addWidget(QLabel("大小微調:"))
            val_lbl = QLabel(f"{settings.get(f'{target_id}_font_size_offset' if target_id != 'default' else 'font_size_offset', 0):+d}")
            val_lbl.setFixedWidth(30)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(-4, 12)
            slider.setValue(settings.get(f"{target_id}_font_size_offset" if target_id != "default" else "font_size_offset", 0))
            slider.setProperty("target_id", target_id)
            slider.valueChanged.connect(self.on_font_slider_changed)
            
            size_layout.addWidget(slider)
            size_layout.addWidget(val_lbl)
            sec_layout.addLayout(size_layout)
            
            self.font_combos[target_id] = combo
            self.font_sliders[target_id] = slider
            self.font_val_labels[target_id] = val_lbl
            
            scroll_layout.addLayout(sec_layout)
            
            div = QFrame()
            div.setFixedHeight(1)
            div.setStyleSheet(f"background-color: {COLORS['divider_strong']}; margin: 8px 0px;")
            scroll_layout.addWidget(div)
            
        create_target_section("default", "全域預設 (未特別指定時套用)")
        create_target_section("sidebar", "側邊欄 (收藏庫/專案清單)")
        create_target_section("title", "右側標題")
        create_target_section("task", "待辦清單")
        
        lbl_font_hint = QLabel("提示: 修改後請重新啟動程式以完整套用字體變更。")
        lbl_font_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-top: 5px;")
        scroll_layout.addWidget(lbl_font_hint)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        font_layout.addWidget(scroll)
        
        self.stacked_widget.addWidget(self.page_font)

        # Page 2: Opacity
        self.page_opacity = QWidget()
        op_layout = QVBoxLayout(self.page_opacity)
        
        lbl_op = QLabel("透明度設定")
        lbl_op.setFont(get_font(16, QFont.Weight.Bold))
        lbl_op.setStyleSheet(f"color: {COLORS['accent']};")
        op_layout.addWidget(lbl_op)
        
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet(f"background-color: {COLORS['divider_strong']}; margin-bottom: 10px;")
        op_layout.addWidget(div2)
        
        bg_op_layout = QHBoxLayout()
        lbl_bg_op = QLabel("背景透明度:")
        self.val_bg_op = QLabel(f"{int(settings.get('bg_opacity', 0.5) * 100)}%")
        self.slider_bg_op = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_op.setRange(0, 100)
        self.slider_bg_op.setValue(int(settings.get('bg_opacity', 0.5) * 100))
        self.slider_bg_op.valueChanged.connect(self.on_bg_opacity_changed)
        bg_op_layout.addWidget(lbl_bg_op)
        bg_op_layout.addWidget(self.slider_bg_op)
        bg_op_layout.addWidget(self.val_bg_op)
        op_layout.addLayout(bg_op_layout)
        
        task_op_layout = QHBoxLayout()
        lbl_task_op = QLabel("任務透明度:")
        self.val_task_op = QLabel(f"{int(settings.get('task_opacity', 0.75) * 100)}%")
        self.slider_task_op = QSlider(Qt.Orientation.Horizontal)
        self.slider_task_op.setRange(0, 100)
        self.slider_task_op.setValue(int(settings.get('task_opacity', 0.75) * 100))
        self.slider_task_op.valueChanged.connect(self.on_task_opacity_changed)
        task_op_layout.addWidget(lbl_task_op)
        task_op_layout.addWidget(self.slider_task_op)
        task_op_layout.addWidget(self.val_task_op)
        op_layout.addLayout(task_op_layout)
        
        op_layout.addStretch()
        self.stacked_widget.addWidget(self.page_opacity)
        
        main_layout.addWidget(self.list_widget)
        main_layout.addWidget(self.stacked_widget)
        
        btn_close = QPushButton("關閉")
        btn_close.setFixedSize(80, 32)
        btn_close.setStyleSheet(f"background-color: {COLORS['accent']}; color: {COLORS['white']}; border-radius: 4px; font-weight: bold;")
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        
        outer_layout.addLayout(main_layout)
        outer_layout.addLayout(btn_layout)
        
    def accept(self):
        self.save_geometry()
        super().accept()
        
    def reject(self):
        self.save_geometry()
        super().reject()
        
    def save_geometry(self):
        settings = self.app_ref.projects.setdefault("__settings__", {})
        settings["settings_geometry"] = self.saveGeometry().toBase64().data().decode()
        self.app_ref.save_data_debounced()
        from config import GLOBAL_SETTINGS
        GLOBAL_SETTINGS.update(settings)
        
    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        
    def on_font_combo_changed(self, index):
        combo = self.sender()
        target_id = combo.property("target_id")
        font_file = combo.itemData(index)
        settings = self.app_ref.projects.setdefault("__settings__", {})
        key = f"{target_id}_font_file" if target_id != "default" else "font_file"
        settings[key] = font_file
        self.app_ref.save_data_debounced()
        GLOBAL_SETTINGS.update(settings)
        self.app_ref.apply_custom_fonts_live()
        
    def on_font_slider_changed(self, val):
        slider = self.sender()
        target_id = slider.property("target_id")
        self.font_val_labels[target_id].setText(f"{val:+d}")
        settings = self.app_ref.projects.setdefault("__settings__", {})
        key = f"{target_id}_font_size_offset" if target_id != "default" else "font_size_offset"
        settings[key] = val
        self.app_ref.save_data_debounced()
        GLOBAL_SETTINGS.update(settings)
        self.app_ref.apply_custom_fonts_live()
            
    def on_bg_opacity_changed(self, val):
        self.val_bg_op.setText(f"{val}%")
        self.app_ref.on_bg_opacity_changed(val)
        
    def on_task_opacity_changed(self, val):
        self.val_task_op.setText(f"{val}%")
        self.app_ref.on_task_opacity_changed(val)

class BackgroundWidget(QWidget):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.bg_image = QPixmap(get_resource_path("assets/bg_cats.png"))
        self.bg_opacity = self.app_ref.projects.get("__settings__", {}).get("bg_opacity", 0.5) 
        
        self._cached_bg = None
        self._last_size = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._cached_bg = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(COLORS['bg_right']))
        
        if not self.bg_image.isNull():
            painter.setOpacity(self.bg_opacity)
            
            widget_size = self.size()
            if self._cached_bg is None or self._last_size != widget_size:
                scaled = self.bg_image.scaled(
                    widget_size, 
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                    Qt.TransformationMode.SmoothTransformation
                )
                
                x_offset = (scaled.width() - widget_size.width()) // 2
                y_offset = (scaled.height() - widget_size.height()) // 2
                
                self._cached_bg = scaled.copy(x_offset, y_offset, widget_size.width(), widget_size.height())
                self._last_size = widget_size
                
            painter.drawPixmap(0, 0, self._cached_bg)

# Removing ProjectContainer as it is no longer used. Drag & Drop logic can be revisited later or added to CategoryWidget.

class PlannerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("專屬計畫書 🌸")
        self.setWindowIcon(QIcon(get_resource_path("assets/icon.png")))
        self.resize(900, 650)
        
        self.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0, 0, 0, 0.25);
                min-height: 40px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(0, 0, 0, 0.45);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                border: none;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: transparent;
                height: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(0, 0, 0, 0.25);
                min-width: 40px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: rgba(0, 0, 0, 0.45);
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                border: none;
                background: none;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
            QMessageBox {{
                background-color: {COLORS['bg_right']};
            }}
            QMessageBox QLabel {{
                color: {COLORS['text_main']};
            }}
            QInputDialog {{
                background-color: {COLORS['bg_right']};
            }}
            QInputDialog QLabel {{
                color: {COLORS['text_main']};
            }}
            QLineEdit {{
                padding: 5px;
                border: 1px solid {COLORS['divider_strong']};
                border-radius: 4px;
                color: {COLORS['text_main']};
            }}
            QPushButton {{
                background-color: {COLORS['bg_left']};
                border: 1px solid {COLORS['divider_strong']};
                border-radius: 4px;
                padding: 5px 15px;
                color: {COLORS['text_main']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_active']};
            }}
        """)
        
        self.projects = load_data()
        
        # Load and set custom font if configured
        settings = self.projects.get("__settings__", {})
        font_file = settings.get("font_file", "default")
        if font_file != "default":
            font_path = get_resource_path(os.path.join("fonts", font_file))
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        app_font = QFont(font_families[0])
                        QApplication.instance().setFont(app_font)
        else:
            QApplication.instance().setFont(QFont("Segoe UI Variable Display, Microsoft YaHei UI"))
                        
        self.current_project = None
        self.setup_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_projects()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Left Sidebar ---
        self.left_frame = QFrame()
        self.left_frame.setFixedWidth(240)
        self.left_frame.setStyleSheet(f"background-color: {COLORS['bg_left']};")
        left_layout = QVBoxLayout(self.left_frame)
        left_layout.setContentsMargins(0, 40, 0, 20)
        left_layout.setSpacing(0)
        
        # Settings Button (Hamburger)
        self.btn_settings = QPushButton("☰", self.left_frame)
        self.btn_settings.setGeometry(8, 8, 20, 20)
        self.btn_settings.setStyleSheet(f"color: {COLORS['text_main']}; font-family: 'Segoe UI Variable Display', 'Microsoft YaHei UI', Arial; font-size: 16px; font-weight: bold; background: transparent; border: none; padding: 0px;")
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_settings.show()
        self.btn_settings.raise_()
        
        # Title Layout
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(15, 0, 15, 0)
        
        self.lbl_title = QLabel("Daily Plan")
        self.lbl_title.setFont(get_font(18, QFont.Weight.Bold, target="sidebar"))
        self.lbl_title.setStyleSheet(f"color: {COLORS['accent']}; padding-left: 25px; background: transparent;")
        title_layout.addWidget(self.lbl_title)
        title_layout.addStretch()
        left_layout.addLayout(title_layout)
        
        div1 = QFrame()
        div1.setFixedHeight(2)
        div1.setStyleSheet(f"background-color: {COLORS['divider_strong']}; margin: 11px 25px 19px 25px;")
        left_layout.addWidget(div1)
        
        # --- Single Scroll Area for Sidebar ---
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setStyleSheet("border: none; background: transparent;")
        
        self.sidebar_content = QWidget()
        self.sidebar_content.setStyleSheet("background: transparent;")
        self.sidebar_layout = QVBoxLayout(self.sidebar_content)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)
        
        self.sidebar_scroll.setWidget(self.sidebar_content)
        left_layout.addWidget(self.sidebar_scroll)
        
        self.btn_add_proj = QPushButton("+ 新增")
        self.btn_add_proj.setFont(get_font(13, target="sidebar"))
        self.btn_add_proj.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_proj.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; color: {COLORS['accent_hover']}; border: none; padding: 10px; }}
            QPushButton:hover {{ background-color: {COLORS['bg_active']}; }}
        """)
        self.btn_add_proj.clicked.connect(self.add_project)
        
        self.btn_import_proj = QPushButton("📥 匯入")
        self.btn_import_proj.setFont(get_font(13, target="sidebar"))
        self.btn_import_proj.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_import_proj.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; color: {COLORS['accent_hover']}; border: none; padding: 10px; }}
            QPushButton:hover {{ background-color: {COLORS['bg_active']}; }}
        """)
        self.btn_import_proj.clicked.connect(self.import_project)
        
        bottom_left_layout = QHBoxLayout()
        bottom_left_layout.setContentsMargins(0, 0, 0, 0)
        bottom_left_layout.addWidget(self.btn_add_proj)
        bottom_left_layout.addWidget(self.btn_import_proj)
        
        left_layout.addLayout(bottom_left_layout)
        
        main_layout.addWidget(self.left_frame)
        
        # --- Right Content ---
        self.right_frame = BackgroundWidget(self)
        right_layout = QVBoxLayout(self.right_frame)
        right_layout.setContentsMargins(50, 45, 46, 40)
        
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        self.lbl_right_title = QLabel("")
        self.lbl_right_title.setFont(get_font(22, QFont.Weight.Bold, target="title"))
        self.lbl_right_title.setStyleSheet(f"color: {COLORS['text_title']}; background: transparent;")
        
        # 加入白色發光效果讓標題在背景上依然清晰
        glow = QGraphicsDropShadowEffect(self.lbl_right_title)
        glow.setOffset(0, 0)
        glow.setBlurRadius(12)
        glow.setColor(QColor(255, 255, 255, 255))
        self.lbl_right_title.setGraphicsEffect(glow)
        
        title_layout.addWidget(self.lbl_right_title)
        title_layout.addStretch()
        
        # Mode Toggle Button (Todo vs Memo)
        self.btn_mode_toggle = QPushButton("☑️ 待辦清單")
        self.btn_mode_toggle.setFont(get_font(12, target="default"))
        self.btn_mode_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_mode_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_left']};
                color: {COLORS['text_main']};
                border: 1px solid {COLORS['divider_strong']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_active']};
            }}
        """)
        self.btn_mode_toggle.clicked.connect(self.toggle_project_mode)
        self.btn_mode_toggle.setVisible(False)
        title_layout.addWidget(self.btn_mode_toggle)
        
        # Uncheck All Button
        self.btn_uncheck_all = QPushButton("🔄 一鍵取消勾選")
        self.btn_uncheck_all.setFont(get_font(12, target="default"))
        self.btn_uncheck_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_uncheck_all.setToolTip("取消當前清單的所有勾選狀態")
        self.btn_uncheck_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_left']};
                color: {COLORS['text_main']};
                border: 1px solid {COLORS['divider_strong']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_active']};
            }}
        """)
        self.btn_uncheck_all.clicked.connect(self.uncheck_all_tasks)
        self.btn_uncheck_all.setVisible(False)
        title_layout.addWidget(self.btn_uncheck_all)
        
        self.btn_export = QPushButton("📤 匯出目前清單")
        self.btn_export.setFont(get_font(12, target="default"))
        self.btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_left']};
                color: {COLORS['text_main']};
                border: 1px solid {COLORS['divider_strong']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_active']};
            }}
        """)
        self.btn_export.clicked.connect(self.export_project)
        self.btn_export.setVisible(False)
        title_layout.addWidget(self.btn_export)
        
        right_layout.addLayout(title_layout)
        
        div2 = QFrame()
        div2.setFixedHeight(2)
        div2.setStyleSheet(f"background-color: {COLORS['divider_strong']}; margin-top: 10px; margin-bottom: 20px;")
        right_layout.addWidget(div2)
        
        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background: transparent;")
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(0)
        self.tasks_layout.addStretch()
        
        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.tasks_scroll.setWidget(self.tasks_container)
        self.tasks_scroll.setStyleSheet("border: none; background: transparent;")
        right_layout.addWidget(self.tasks_scroll)
        
        main_layout.addWidget(self.right_frame)
        self.refresh_projects()

    def refresh_projects(self):
        while self.sidebar_layout.count():
            item = self.sidebar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.proj_widgets = []
        
        settings = self.projects.get("__settings__", {})
        categories = settings.get("categories", {})
        
        categorized_projects = set()
        for cat_name, items in categories.items():
            for item in items:
                if isinstance(item, dict) and item.get("type") == "project":
                    categorized_projects.add(item.get("target"))
                elif isinstance(item, str):
                    categorized_projects.add(item)
                    
        for cat_name, items in categories.items():
            cw = CategoryWidget(cat_name, items, self, is_uncategorized=False, parent=self.sidebar_content)
            self.sidebar_layout.addWidget(cw)
            
        uncategorized = []
        for p in self.projects.keys():
            if p == "__settings__": continue
            if p not in categorized_projects:
                uncategorized.append(p)
                
        if uncategorized or not categories:
            cw = CategoryWidget("未歸類", uncategorized, self, is_uncategorized=True, parent=self.sidebar_content)
            self.sidebar_layout.addWidget(cw)
            
        self.sidebar_layout.addStretch()

        if self.current_project and self.current_project in self.projects:
            self.load_project(self.current_project)
        elif self.projects and len(self.projects) > 1:
            first_proj = next(p for p in self.projects.keys() if p != "__settings__")
            self.load_project(first_proj)

    def open_settings(self):
        dlg = SettingsDialog(self, self)
        dlg.exec()

    def add_project(self):
        from components.project_button import ProjectButton
        # Always insert new project to the end of Uncategorized
        pw = ProjectButton("", self, is_new=True)
        pw.hide()
        
        # We need to find the uncategorized category widget
        uncat_cw = None
        for i in range(self.sidebar_layout.count()):
            item = self.sidebar_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), CategoryWidget):
                if item.widget().is_uncategorized:
                    uncat_cw = item.widget()
                    break
                    
        if uncat_cw:
            uncat_cw.container_layout.addWidget(pw)
            self.proj_widgets.append(pw)
            self.animate_widget_enter(pw)
        else:
            # If no uncategorized exists yet, refresh to force create it, then add
            self.projects[""] = []
            self.refresh_projects()
            # find the empty project button and trigger edit
            for pw in self.proj_widgets:
                if pw.name == "":
                    pw.setup_edit_mode()
                    break

    def is_project_memo_mode(self, project_name=None):
        if project_name is None:
            project_name = self.current_project
        if not project_name:
            return False
        settings = self.projects.get("__settings__", {})
        modes = settings.get("project_modes", {})
        return modes.get(project_name, "todo") == "memo"

    def toggle_project_mode(self):
        if not self.current_project:
            return
        settings = self.projects.setdefault("__settings__", {})
        modes = settings.setdefault("project_modes", {})
        curr_mode = modes.get(self.current_project, "todo")
        new_mode = "memo" if curr_mode == "todo" else "todo"
        modes[self.current_project] = new_mode
        self.save_data_debounced()
        self.update_mode_ui()
        self.render_tasks_no_anim()

    def uncheck_all_tasks(self):
        if not self.current_project:
            return
        tasks = self.projects.get(self.current_project, [])
        if not tasks:
            return
            
        def uncheck_recursive(t_list):
            for t in t_list:
                t["done"] = False
                if "children" in t:
                    uncheck_recursive(t["children"])
                    
        uncheck_recursive(tasks)
        self.save_data_debounced()
        self.render_tasks_no_anim()

    def update_mode_ui(self):
        if not self.current_project:
            self.btn_mode_toggle.setVisible(False)
            self.btn_uncheck_all.setVisible(False)
            self.btn_export.setVisible(False)
            return
            
        is_memo = self.is_project_memo_mode(self.current_project)
        self.btn_mode_toggle.setVisible(True)
        self.btn_export.setVisible(True)
        if is_memo:
            self.btn_mode_toggle.setText("📝 備忘錄模式")
            self.btn_mode_toggle.setToolTip("目前為備忘錄模式（無勾選框）。點擊切換為待辦清單模式")
            self.btn_uncheck_all.setVisible(False)
        else:
            self.btn_mode_toggle.setText("☑️ 待辦清單")
            self.btn_mode_toggle.setToolTip("目前為待辦清單模式（含勾選框）。點擊切換為備忘錄模式")
            self.btn_uncheck_all.setVisible(True)

    def load_project(self, name):
        self.current_project = name
        self.lbl_right_title.setText(name)
        self.update_mode_ui()
        
        for pw in self.proj_widgets:
            pw.update_style(pw.name == name)
            
        self.render_tasks()

    def render_tasks(self):
        # Clear existing tasks
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        project_tasks = self.projects.get(self.current_project, []) if self.current_project else []
        for p_data in project_tasks:
            tw = TaskWidget(p_data, 1, project_tasks, self, parent=self.tasks_container)
            self.tasks_layout.addWidget(tw)
            
        self.add_parent_btn = AddParentButton(self, parent=self.tasks_container)
        self.tasks_layout.addWidget(self.add_parent_btn)
        self.tasks_layout.addStretch()
        
        # Reset scroll
        self.tasks_scroll.verticalScrollBar().setValue(0)

    def delete_project(self, name):
        del self.projects[name]
        
        # also remove from categories
        settings = self.projects.get("__settings__", {})
        cats = settings.get("categories", {})
        for cat_name, items in cats.items():
            cats[cat_name] = [
                i for i in items 
                if not ((isinstance(i, dict) and i.get("target") == name) or (isinstance(i, str) and i == name))
            ]
        modes = settings.get("project_modes", {})
        if name in modes:
            del modes[name]
            
        self.save_data_debounced()
        self.refresh_projects()
        
        if self.current_project and self.current_project != "__settings__":
            self.lbl_right_title.setText(self.current_project)
            self.update_mode_ui()
            self.render_tasks_no_anim()
        else:
            self.current_project = None
            self.lbl_right_title.setText("")
            self.update_mode_ui()
            self.render_tasks_no_anim()

    def render_tasks_no_anim(self):
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        project_tasks = self.projects.get(self.current_project, []) if self.current_project else []
        for p_data in project_tasks:
            tw = TaskWidget(p_data, 1, project_tasks, self, parent=self.tasks_container)
            self.tasks_layout.addWidget(tw)
            
        self.add_parent_btn = AddParentButton(self, parent=self.tasks_container)
        self.tasks_layout.addWidget(self.add_parent_btn)
        self.tasks_layout.addStretch()

    def animate_widget_enter(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        widget.show()
        
        anim_op = QPropertyAnimation(effect, b"opacity", self)
        anim_op.setDuration(250)
        anim_op.setStartValue(0.0)
        anim_op.setEndValue(1.0)
        anim_op.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        def cleanup():
            widget.setGraphicsEffect(None)
            
        anim_op.finished.connect(cleanup)
        widget._anim_group = anim_op
        anim_op.start()

    def animate_widget_exit(self, widget, callback=None):
        if not widget.graphicsEffect():
            widget.setGraphicsEffect(QGraphicsOpacityEffect(widget))
            
        anim_op = QPropertyAnimation(widget.graphicsEffect(), b"opacity", self)
        anim_op.setDuration(150)
        anim_op.setStartValue(1.0)
        anim_op.setEndValue(0.0)
        anim_op.setEasingCurve(QEasingCurve.Type.InCubic)
        
        widget._anim_group = anim_op
        
        if callback:
            anim_op.finished.connect(callback)
        else:
            anim_op.finished.connect(widget.deleteLater)
            if hasattr(self, 'proj_widgets') and widget in self.proj_widgets:
                self.proj_widgets.remove(widget)
                
        anim_op.start()

    def import_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "選擇要匯入的清單", "", "JSON Files (*.json)")
        if not file_path: return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)
            
            if isinstance(imported_data, dict) and "name" in imported_data and "tasks" in imported_data:
                base_name = imported_data["name"]
                tasks = imported_data["tasks"]
            elif isinstance(imported_data, list):
                import os
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                tasks = imported_data
            else:
                raise ValueError("檔案格式不符合預期")
            
            new_name = base_name
            counter = 1
            while new_name in self.projects:
                new_name = f"{base_name} ({counter})"
                counter += 1
                
            self.projects[new_name] = tasks
            self.save_data_debounced()
            self.refresh_projects()
            self.load_project(new_name)
            QMessageBox.information(self, "匯入成功", f"成功匯入清單：{new_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "匯入失敗", f"無法讀取檔案:\n{str(e)}")
        
    def save_data_debounced(self):
        if not hasattr(self, '_save_timer'):
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(lambda: save_data(self.projects))
        self._save_timer.start(500)

    def apply_custom_fonts_live(self):
        settings = self.projects.get("__settings__", {})
        font_file = settings.get("font_file", "default")
        
        if font_file != "default":
            font_path = get_resource_path(os.path.join("fonts", font_file))
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        app_font = QFont(font_families[0])
                        QApplication.instance().setFont(app_font)
        else:
            QApplication.instance().setFont(QFont("Segoe UI Variable Display, Microsoft YaHei UI"))
            
        self.lbl_right_title.setFont(get_font(22, QFont.Weight.Bold, target="title"))
        if hasattr(self, 'lbl_title'):
            self.lbl_title.setFont(get_font(18, QFont.Weight.Bold, target="sidebar"))
        if hasattr(self, 'btn_add_proj'):
            self.btn_add_proj.setFont(get_font(13, target="sidebar"))
        if hasattr(self, 'btn_import_proj'):
            self.btn_import_proj.setFont(get_font(13, target="sidebar"))
        if hasattr(self, 'btn_mode_toggle'):
            self.btn_mode_toggle.setFont(get_font(12, target="default"))
        if hasattr(self, 'btn_uncheck_all'):
            self.btn_uncheck_all.setFont(get_font(12, target="default"))
        if hasattr(self, 'btn_export'):
            self.btn_export.setFont(get_font(12, target="default"))
        
        # Redraw UI elements to apply fonts instantly
        expanded_cats = []
        for i in range(self.sidebar_layout.count()):
            item = self.sidebar_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if hasattr(w, 'is_collapsed') and not w.is_collapsed:
                    expanded_cats.append(w.name)
                
        self.refresh_projects()
        
        # Restore expanded state
        for i in range(self.sidebar_layout.count()):
            item = self.sidebar_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if hasattr(w, 'name') and w.name in expanded_cats:
                    if w.is_collapsed:
                        w.toggle_collapse()
                
        if self.current_project:
            self.load_project(self.current_project)
            
    def on_bg_opacity_changed(self, val):
        alpha = val / 100.0
        if "__settings__" not in self.projects:
            self.projects["__settings__"] = {}
        self.projects["__settings__"]["bg_opacity"] = alpha
        self.right_frame.bg_opacity = alpha
        self.right_frame.update()
        self.save_data_debounced()
        
    def on_task_opacity_changed(self, val):
        alpha = val / 100.0
        if "__settings__" not in self.projects:
            self.projects["__settings__"] = {}
        self.projects["__settings__"]["task_opacity"] = alpha
        
        def update_tw_recursive(layout):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    if isinstance(w, TaskWidget):
                        w.update_opacity_style()
                        if hasattr(w, 'c_layout'):
                            update_tw_recursive(w.c_layout)
                            
        update_tw_recursive(self.tasks_layout)
        self.save_data_debounced()

    def highlight_task(self, task_id):
        def find_path(tasks, tid, current_path):
            for t in tasks:
                if t.get("id") == tid:
                    return current_path
                if "children" in t:
                    res = find_path(t["children"], tid, current_path + [t])
                    if res is not None:
                        return res
            return None
            
        proj_tasks = self.projects.get(self.current_project, [])
        path = find_path(proj_tasks, task_id, [])
        if path is not None:
            for p in path:
                p["collapsed"] = False
            self.render_tasks_no_anim()
            
            def find_widget(layout, tid):
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), TaskWidget):
                        w = item.widget()
                        if w.task_data.get("id") == tid:
                            return w
                        if hasattr(w, 'c_layout'):
                            res = find_widget(w.c_layout, tid)
                            if res: return res
                return None
                
            w = find_widget(self.tasks_layout, task_id)
            if w:
                self.tasks_scroll.ensureWidgetVisible(w, 50, 50)
                w.header.setStyleSheet(f"""
                    #TaskHeader {{
                        background-color: {hex_to_rgba(COLORS['highlight_bg'], 0.95)};
                        border: 2px solid {COLORS['accent']};
                        border-radius: 8px;
                        margin: 2px 10px 2px 0px;
                    }}
                """)
                QTimer.singleShot(1500, w.update_opacity_style)

    def export_project(self):
        if not self.current_project: return
        
        default_name = f"{self.current_project}.json"
        file_path, _ = QFileDialog.getSaveFileName(self, "儲存清單", default_name, "JSON Files (*.json)")
        if not file_path: return
        
        try:
            export_data = {
                "name": self.current_project,
                "tasks": self.projects[self.current_project]
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "匯出成功", "清單已成功匯出！")
        except Exception as e:
            QMessageBox.warning(self, "匯出失敗", f"無法寫入檔案：{str(e)}")
