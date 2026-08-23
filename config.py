import os
import sys
import json

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

DATA_DIR = get_resource_path("data")
DATA_FILE = os.path.join(DATA_DIR, "data.json")

COLORS = {
    "bg_right": "#FCF8F9",
    "bg_left": "#F7E6EB",
    "bg_active": "#EFCBD6",
    "text_title": "#2D282A",
    "text_main": "#4A4144",
    "text_done": "#B3A6AA",
    "accent": "#D68C9F",
    "accent_hover": "#C5788C",
    "divider": "#EAD9DE",
    "divider_strong": "#DFBAC5"
}

import uuid

def ensure_ids(tasks):
    for t in tasks:
        if "id" not in t:
            t["id"] = uuid.uuid4().hex
        if "children" in t:
            ensure_ids(t["children"])

GLOBAL_SETTINGS = {}

def get_font(base_size, weight=None, target="default"):
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont, QFontDatabase
    import os
    app = QApplication.instance()
    
    # Load specific font if configured
    font_file = GLOBAL_SETTINGS.get(f"{target}_font_file", "default")
    if font_file == "default" and target != "default":
        font_file = GLOBAL_SETTINGS.get("font_file", "default")
        
    family = "Segoe UI Variable Display, Microsoft YaHei UI, Arial"
    if app:
        family = app.font().family()
        
    if font_file != "default":
        font_path = get_resource_path(os.path.join("fonts", font_file))
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    family = families[0]
                    
    offset = GLOBAL_SETTINGS.get(f"{target}_font_size_offset", 0)
    
    font = QFont(family, base_size + offset)
    if weight is not None:
        if isinstance(weight, bool):
            font.setBold(weight)
        else:
            font.setWeight(weight)
    return font

def load_data():
    data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except: pass
    elif os.path.exists(get_resource_path("data.json")):
        with open(get_resource_path("data.json"), "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except: pass
            
    if "__settings__" not in data:
        data["__settings__"] = {
            "bg_opacity": 0.5,
            "task_opacity": 0.75,
            "categories": {"我的最愛": []}
        }
        
    settings = data["__settings__"]
    if "favorites" in settings:
        if "categories" not in settings:
            settings["categories"] = {"我的最愛": settings["favorites"]}
        else:
            settings["categories"]["我的最愛"] = settings["favorites"]
        del settings["favorites"]
    elif "categories" not in settings:
        settings["categories"] = {"我的最愛": []}
        
    for k, v in data.items():
        if k != "__settings__":
            ensure_ids(v)
            
    GLOBAL_SETTINGS.update(data.get("__settings__", {}))        
    return data

def save_data(projects):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)
