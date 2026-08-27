import sys
from PyQt6.QtWidgets import QApplication

VERSION = "1.0.4"

if __name__ == "__main__":
    import ctypes
    try:
        myappid = 'xingshili.dailyplan.app.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    from planner_app import PlannerApp
    
    app = QApplication(sys.argv)
    window = PlannerApp()
    window.setWindowTitle(f"專屬計畫書 🌸 v{VERSION}")
    window.show()
    sys.exit(app.exec())
