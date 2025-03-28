import mysql.connector
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Настройка логирования
logging.basicConfig(
    filename=f'sync_log_{datetime.now().strftime("%Y%m%d")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DatabaseError(Exception):
    """Базовый класс для исключений базы данных"""
    pass

class MySQLConnectionError(DatabaseError):
    """Исключение при ошибке подключения к MySQL"""
    pass

class SQLiteConnectionError(DatabaseError):
    """Исключение при ошибке подключения к SQLite"""
    pass

class DataSync:
    def __init__(self, mysql_config: Dict[str, Any], sqlite_path: str):
        """
        Инициализация класса синхронизации данных.
        
        Args:
            mysql_config: Конфигурация для подключения к MySQL
            sqlite_path: Путь к файлу SQLite базы данных
        """
        self.mysql_config = mysql_config
        self.sqlite_path = sqlite_path
        self.logger = logging.getLogger(__name__)

    def _connect_mysql(self) -> tuple:
        """
        Установка соединения с MySQL.
        
        Returns:
            tuple: (connection, cursor)
        
        Raises:
            MySQLConnectionError: При ошибке подключения к MySQL
        """
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            return conn, cursor
        except mysql.connector.Error as e:
            error_msg = f"Ошибка подключения к MySQL: {str(e)}"
            self.logger.error(error_msg)
            raise MySQLConnectionError(error_msg)

    def _connect_sqlite(self) -> tuple:
        """
        Установка соединения с SQLite.
        
        Returns:
            tuple: (connection, cursor)
        
        Raises:
            SQLiteConnectionError: При ошибке подключения к SQLite
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            return conn, cursor
        except sqlite3.Error as e:
            error_msg = f"Ошибка подключения к SQLite: {str(e)}"
            self.logger.error(error_msg)
            raise SQLiteConnectionError(error_msg)

    def send_to_mysql(self, data: List[Dict[str, Any]], user_id: int) -> bool:
        """
        Отправка данных на сервер MySQL.
        
        Args:
            data: Список словарей с данными
            user_id: ID пользователя
        
        Returns:
            bool: True если данные успешно отправлены, False в случае ошибки
        """
        try:
            conn, cursor = self._connect_mysql()
            
            # Проверяем существование пользователя
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if not cursor.fetchone():
                raise ValueError(f"Пользователь с ID {user_id} не найден")

            # Вставляем данные
            for row in data:
                query = """
                INSERT INTO user_data (user_id, data, updated)
                VALUES (%s, %s, 1)
                """
                cursor.execute(query, (user_id, json.dumps(row)))

            conn.commit()
            self.logger.info(f"Успешно отправлено {len(data)} записей для пользователя {user_id}")
            return True

        except (MySQLConnectionError, ValueError) as e:
            self.logger.error(f"Ошибка при отправке данных: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при отправке данных: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                cursor.close()
                conn.close()

    def sync_with_sqlite(self) -> bool:
        """
        Синхронизация данных из MySQL в SQLite.
        
        Returns:
            bool: True если синхронизация успешна, False в случае ошибки
        """
        try:
            # Подключаемся к обеим базам
            mysql_conn, mysql_cursor = self._connect_mysql()
            sqlite_conn, sqlite_cursor = self._connect_sqlite()

            # Получаем обновленные записи из MySQL
            mysql_cursor.execute("""
                SELECT data_id, user_id, data 
                FROM user_data 
                WHERE updated = 1
            """)
            changes = mysql_cursor.fetchall()

            if not changes:
                self.logger.info("Нет данных для синхронизации")
                return True

            # Обновляем данные в SQLite
            for change in changes:
                data = json.loads(change['data'])
                
                # Проверяем наличие id в данных
                if 'id' not in data:
                    self.logger.warning(f"Пропущена запись без id: {data}")
                    continue
                    
                record_id = data['id']
                
                # Формируем SET часть запроса для UPDATE
                set_parts = []
                values = []
                for column, value in data.items():
                    if column != 'id':  # Пропускаем id в SET
                        set_parts.append(f"{column} = ?")
                        values.append(value)
                
                # Добавляем id в конец для WHERE условия
                values.append(record_id)
                
                query = f"""
                UPDATE vehicles 
                SET {', '.join(set_parts)}
                WHERE id = ?
                """
                
                sqlite_cursor.execute(query, values)

                # Отмечаем запись как синхронизированную в MySQL
                mysql_cursor.execute("""
                    UPDATE user_data 
                    SET updated = 0 
                    WHERE data_id = %s
                """, (change['data_id'],))
            print(f"Успешно синхронизировано {len(changes)} записей")
            # Сохраняем изменения
            sqlite_conn.commit()
            mysql_conn.commit()

            self.logger.info(f"Успешно синхронизировано {len(changes)} записей")
            return True

        except (MySQLConnectionError, SQLiteConnectionError) as e:
            self.logger.error(f"Ошибка подключения при синхронизации: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при синхронизации: {str(e)}")
            return False
        finally:
            if 'mysql_conn' in locals():
                mysql_cursor.close()
                mysql_conn.close()
            if 'sqlite_conn' in locals():
                sqlite_cursor.close()
                sqlite_conn.close()

    def get_sync_status(self) -> Optional[Dict[str, int]]:
        """
        Получение статуса синхронизации.
        
        Returns:
            Dict[str, int]: Словарь с количеством записей, ожидающих синхронизации
        """
        try:
            conn, cursor = self._connect_mysql()
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM user_data 
                WHERE updated = 1
            """)
            result = cursor.fetchone()
            return {"pending_updates": result['count']}
        except Exception as e:
            self.logger.error(f"Ошибка при получении статуса синхронизации: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                cursor.close()
                conn.close()

    def get_users(self) -> Optional[List[Dict[str, Any]]]:
        """
        Получение списка всех пользователей из MySQL.
        
        Returns:
            Optional[List[Dict[str, Any]]]: Список словарей с информацией о пользователях
            Каждый словарь содержит:
            - user_id: ID пользователя
            - username: Имя пользователя
            - email: Email пользователя
            Возвращает None в случае ошибки
        """
        try:
            conn, cursor = self._connect_mysql()
            cursor.execute("""
                SELECT user_id, username 
                FROM users 
                ORDER BY username
            """)
            users = cursor.fetchall()
            
            if not users:
                self.logger.info("Пользователи не найдены")
                return []
                
            self.logger.info(f"Успешно получен список пользователей: {len(users)} записей")
            return users
            
        except MySQLConnectionError as e:
            self.logger.error(f"Ошибка подключения при получении списка пользователей: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при получении списка пользователей: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                cursor.close()
                conn.close()

# Пример использования:
if __name__ == "__main__":
    # Конфигурация для подключения к MySQL
    mysql_config = {
                'host': '91.209.226.31',
                'user': 'USER',
                'password': 'password',
                'database': 'Centramash'
            }

    # Создание экземпляра класса
    sync = DataSync(mysql_config, 'vehicles.db')

    # Получение списка пользователей
    users = sync.get_users()
    if users:
        print("Список пользователей:")
        for user in users:
            print(f"ID: {user['user_id']}, Имя: {user['username']}")

    # Пример данных для отправки
    test_data = [
        {"column1": "value1", "column2": "value2"},
        {"column1": "value3", "column2": "value4", "column3": "value5"}
    ]

    # Отправка данных
    if sync.send_to_mysql(test_data, user_id=1):
        print("Данные успешно отправлены")

    # Синхронизация
    if sync.sync_with_sqlite():
        print("Синхронизация выполнена успешно")

    # Проверка статуса
    status = sync.get_sync_status()
    if status:
        print(f"Ожидает синхронизации: {status['pending_updates']} записей")
