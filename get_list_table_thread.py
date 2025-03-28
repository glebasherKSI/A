from PyQt6.QtCore import QThread, pyqtSignal
from database import CustomDatabase

class GetTablesThread(QThread):
    tables_received = pyqtSignal(list) # Сигнал со списком таблиц
    error_occurred = pyqtSignal(str) # Сигнал с ошибкой

    def run(self):
        try:
            db = CustomDatabase()
            tables = db.get_tables()
            db.close()
            self.tables_received.emit(tables)
        except Exception as e:
            self.error_occurred.emit(str(e))
