from PyQt6.QtCore import QThread, pyqtSignal
from sql_to_myaql import DataSync
import traceback

class DBWorker(QThread):
    finished = pyqtSignal(bool, str)
    users_loaded = pyqtSignal(list)
    
    def __init__(self, selected_data=None, user_id=None):
        super().__init__()
        self.selected_data = selected_data
        self.user_id = user_id
        self.sync = None
        
    def run(self):
        try:
            # Создаем экземпляр DataSync только при первом запуске
            if not self.sync:
                self.sync = DataSync({
                    'host': '91.209.226.31',
                    'user': 'USER', 
                    'password': 'password',
                    'database': 'Centramash',
                    'connection_timeout': 10,  # Добавляем таймаут подключения
                    'use_pure': True  # Используем чистый Python для подключения
                }, 'vehicles.db')
            
            if not self.selected_data:
                # Загружаем список пользователей
                users = self.sync.get_users()
                if users is None:  # Проверяем на None, так как пустой список - валидный результат
                    self.finished.emit(False, "Не удалось получить список пользователей")
                    return
                self.users_loaded.emit(users)
                self.finished.emit(True, "")
            else:
                # Отправляем данные
                if not self.user_id:
                    self.finished.emit(False, "Не указан ID пользователя")
                    return
                    
                success = self.sync.send_to_mysql(self.selected_data, self.user_id)
                self.finished.emit(success, 
                    "Данные успешно отправлены" if success else "Не удалось отправить данные")
                
        except Exception as e:
            error_msg = f"Ошибка: {str(e)}\n{traceback.format_exc()}"
            self.finished.emit(False, error_msg)

class SyncWorker(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, mysql_config=None, sqlite_db=None):
        super().__init__()
        self.mysql_config = mysql_config
        self.sqlite_db = sqlite_db
        self.sync = None
        
    def run(self):
        try:
            # Создаем экземпляр DataSync только при первом запуске
            if not self.sync:
                self.sync = DataSync({
                    'host': '91.209.226.31',
                    'user': 'USER',
                    'password': 'password', 
                    'database': 'Centramash',
                    'connection_timeout': 10,  # Добавляем таймаут подключения
                    'use_pure': True  # Используем чистый Python для подключения
                }, 'vehicles.db')
            
            success = self.sync.sync_with_sqlite()
            print(f"Успешно синхронизировано {success} записей")
            self.finished.emit(success,
                "Синхронизация выполнена успешно" if success else "Ошибка при синхронизации")
                
        except Exception as e:
            error_msg = f"Ошибка синхронизации: {str(e)}\n{traceback.format_exc()}"
            self.finished.emit(False, error_msg)
