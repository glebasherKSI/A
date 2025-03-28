import sqlite3
from typing import Dict, Any, Optional
import os
from PyQt6.QtCore import QThread
import traceback







class Database:

    def __init__(self):
        """Инициализация подключения к БД"""
        self.db_path = 'vehicles.db'
        self._ensure_db_exists()
        
    def close(self):
        """Закрытие соединения с БД"""
        pass  # В SQLite соединения закрываются автоматически
        
    def _ensure_db_exists(self):
        """Проверяет существование БД и создает таблицы если нужно"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vehicles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT,
                        parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        -- Основные данные ТС
                        MARKA TEXT,
                        KOMMERCHESKOE_NAIMENOVANIE TEXT,
                        TIP TEXT,
                        SHASSI TEXT,
                        KATEGORIA TEXT,
                        VIN TEXT,
                        GOD_VIPUSKA TEXT,
                        NOMER_REGISTRACII TEXT,
                        
                        -- Технические характеристики двигателя
                        DVIGATEL_MODEL TEXT,
                        DVIGATEL_CYLINDRY TEXT,
                        DVIGATEL_MOSHNOST TEXT,
                        DVIGATEL_OBEM TEXT,
                        DVIGATEL_SZHATIYE TEXT,
                        -- Данные заявителя и изготовителя
                        ZAYAVITEL TEXT,
                        IZGOTOVITEL TEXT,
                        SBOROCHNIY_ZAVOD TEXT,
                    
                        
                        -- Топливная система
                        TOPLIVO_TIP TEXT,
                        TOPLIVO_SISTEMA_PITANIYA TEXT,
                        TOPLIVO_SISTEMA_VIPUSKA TEXT,
                        
                        -- Трансмиссия
                        TRANSMISSIYA_TIP TEXT,
                        TRANSMISSIYA_SCEPLENIE TEXT,
                        TRANSMISSIYA_KOROBKA TEXT,
                        
                        -- Подвеска
                        PODVESKA_PEREDNYAYA TEXT,
                        PODVESKA_ZADNYAYA TEXT,
                        RULEVOE_UPRAVLENIE TEXT,
                        -- Тормозная система
                        TORMOZNAYA_RABOCHAYA TEXT,
                        TORMOZNAYA_ZAPASNAYA TEXT,
                        TORMOZNAYA_STOYANOCHNAYA TEXT,
                        TORMOZNAYA_VSPOMOGATELNAYA TEXT,
                        
                        -- Размеры и масса
                        GABARITY_DLINA TEXT,
                        GABARITY_SHIRINA TEXT,
                        GABARITY_VYSOTA TEXT,
                        MASSA_SNARYAZHENNAYA TEXT,
                        MASSA_MAKSIMALNAYA TEXT,
                        BAZA TEXT,
                        KOLEYA TEXT,
                        
                        -- Дополнительные характеристики
                        EKOLOGICHESKIY_KLASS TEXT,
                        KOLESNAYA_FORMULA TEXT,
                        SHEMA_KOMPONOVKI TEXT,
                        ZAGRUZOCHNOE_PROSTRANSTVO TEXT,
                        KABINA TEXT,
                        TIP_KUZOVA_DVERI TEXT TEXT,
                        MESTA TEXT,
                        
                        -- Оборудование
                        SHINY TEXT,
                        OBORUDOVANIE TEXT,
                        UVEOS TEXT,
                        
                        -- Базовое ТС
                        BAZOVOE_VIN TEXT,
                        BAZOVOE_MODIFIKACIYA TEXT,
                        
                        -- Данные СБКТС
                        SBKTS_NOMER TEXT,
                        SBKTS_DATA_ZAYAVKI TEXT,
                        SBKTS_INZHENER TEXT,
                        
                        -- Даты и документы
                        DATA_OFORMLENIYA TEXT,
                        DAY TEXT,
                        MONTH TEXT,
                        
                        -- Флаги
                        suspicious INTEGER DEFAULT 0,
                        in_archive INTEGER DEFAULT 0,
                        
                        -- Метаданные
                        temperature REAL,
                        humidity REAL
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[ОШИБКА] Создание БД: {e}")
            raise

    def insert_vehicle_data(self, data: Dict[str, Any], filename: str) -> bool:
        """Вставка данных о ТС в БД"""
        try:
            print(f"\n[DEBUG DB] Попытка вставки данных для файла {filename}")
            # print(f"[DEBUG DB] Входные данные: {data}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Подготавливаем данные
                prepared_data = self._prepare_data(data)
                prepared_data['filename'] = filename
                
                # Добавляем данные о температуре и влажности
                if 'temperature' in data:
                    prepared_data['temperature'] = data['temperature']
                if 'humidity' in data:
                    prepared_data['humidity'] = data['humidity']
                if 'NOMER_REGISTRACII' in data:
                    prepared_data['NOMER_REGISTRACII'] = data['NOMER_REGISTRACII']
                if 'DAY' in data:
                    prepared_data['DAY'] = data['DAY']
                if 'MONTH' in data:
                    prepared_data['MONTH'] = data['MONTH']
                if 'SHASSI' in data:
                    prepared_data['SHASSI'] = data['SHASSI']
                if 'ZAYAVITEL' in data:
                    prepared_data['ZAYAVITEL'] = data['ZAYAVITEL']
                if 'IZGOTOVITEL' in data:
                    prepared_data['IZGOTOVITEL'] = data['IZGOTOVITEL']
                if 'SBOROCHNIY_ZAVOD' in data:
                    prepared_data['SBOROCHNIY_ZAVOD'] = data['SBOROCHNIY_ZAVOD']
                if 'TIP_KUZOVA_DVERI' in data:
                    prepared_data['TIP_KUZOVA_DVERI'] = data['TIP_KUZOVA_DVERI']
                if 'RULEVOE_UPRAVLENIE' in data:
                    prepared_data['RULEVOE_UPRAVLENIE'] = data['RULEVOE_UPRAVLENIE']
                
                print(f"[DEBUG DB] Подготовленные данные: {prepared_data}")
                
                # Проверяем VIN на дубликаты
                if vin := prepared_data.get('VIN'):
                    print(f"[DEBUG DB] Проверка VIN: {vin}")
                    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE VIN = ?", (vin,))
                    if cursor.fetchone()[0] > 0:
                        prepared_data['suspicious'] = 1
                        cursor.execute("UPDATE vehicles SET suspicious = 1 WHERE VIN = ?", (vin,))
                        print(f"[DEBUG DB] Найден дубликат VIN: {vin}")
                
                # Получаем список колонок
                cursor.execute("PRAGMA table_info(vehicles)")
                existing_columns = {row[1] for row in cursor.fetchall()}
                print(f"[DEBUG DB] Существующие колонки: {existing_columns}")
                
                # Формируем запрос
                columns = []
                values = []
                for key, value in prepared_data.items():
                    if value is not None and key in existing_columns:
                        columns.append(f"{key}")
                        values.append(value)
                
                if not columns:
                    print("[ОШИБКА] Нет данных для вставки")
                    return False
                
                # Выполняем вставку
                query = f"INSERT INTO vehicles ({', '.join(columns)}) VALUES ({', '.join(['?' for _ in values])})"
                print(f"[DEBUG DB] SQL запрос: {query}")
                print(f"[DEBUG DB] Значения: {values}")
                
                cursor.execute(query, values)
                conn.commit()
            
                print(f"[ИНФО] Данные из файла {filename} успешно добавлены")
                return True
                
        except Exception as e:
            print(f"[ОШИБКА] Вставка данных: {e}")
            print(f"[DEBUG DB] Полная ошибка: {traceback.format_exc()}")
            return False

    def _prepare_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Подготовка данных для вставки"""
        prepared = {}
        
        # Основные поля
        prepared.update({
            'MARKA': data.get('MARKA'),
            'KOMMERCHESKOE_NAIMENOVANIE': data.get('KOMMERCHESKOE_NAIMENOVANIE'),
            'TIP': data.get('TIP'),
            'KATEGORIA': data.get('KATEGORIA'),
            'VIN': data.get('VIN'),
            'GOD_VIPUSKA': data.get('GOD_VIPUSKA')
        })
        
        # Данные двигателя
        if dvigatel := data.get('DVIGATEL', {}):
            prepared.update({
                'DVIGATEL_MODEL': dvigatel.get('model'),
                'DVIGATEL_CYLINDRY': dvigatel.get('cylindry'),
                'DVIGATEL_MOSHNOST': dvigatel.get('moshnost'),
                'DVIGATEL_OBEM': dvigatel.get('obem'),
                'DVIGATEL_SZHATIYE': dvigatel.get('szhatiye')
            })
        
        # Данные топливной системы
        if toplivo := data.get('TOPLIVO', {}):
            prepared.update({
                'TOPLIVO_TIP': toplivo.get('tip'),
                'TOPLIVO_SISTEMA_PITANIYA': toplivo.get('sistema_pitaniya'),
                'TOPLIVO_SISTEMA_VIPUSKA': toplivo.get('sistema_vipuska')
            })
        
        # Данные трансмиссии
        if transmissiya := data.get('TRANSMISSIYA', {}):
            prepared.update({
                'TRANSMISSIYA_TIP': transmissiya.get('tip'),
                'TRANSMISSIYA_SCEPLENIE': transmissiya.get('sceplenie'),
                'TRANSMISSIYA_KOROBKA': transmissiya.get('korobka')
            })
        
        # Данные подвески
        if podveska := data.get('PODVESKA', {}):
            prepared.update({
                'PODVESKA_PEREDNYAYA': podveska.get('perednyaya'),
                'PODVESKA_ZADNYAYA': podveska.get('zadnyaya')
            })
        
        # Данные тормозной системы
        if tormoza := data.get('TORMOZNAYA_SISTEMA', {}):
            prepared.update({
                'TORMOZNAYA_RABOCHAYA': tormoza.get('rabochaya'),
                'TORMOZNAYA_ZAPASNAYA': tormoza.get('zapasnaya'),
                'TORMOZNAYA_STOYANOCHNAYA': tormoza.get('stoyanochnaya'),
                'TORMOZNAYA_VSPOMOGATELNAYA': tormoza.get('vspomogatelnaya')
            })
        
        # Габариты и масса
        if gabarity := data.get('GABARITY', {}):
            prepared.update({
                'GABARITY_DLINA': gabarity.get('dlina'),
                'GABARITY_SHIRINA': gabarity.get('shirina'),
                'GABARITY_VYSOTA': gabarity.get('vysota')
            })
        
        prepared.update({
            'MASSA_SNARYAZHENNAYA': data.get('MASSA_SNARYAZHENNAYA'),
            'MASSA_MAKSIMALNAYA': data.get('MASSA_MAKSIMALNAYA'),
            'BAZA': data.get('BAZA'),
            'KOLEYA': data.get('KOLEYA')
        })
        
        # Дополнительные характеристики
        prepared.update({
            'EKOLOGICHESKIY_KLASS': data.get('EKOLOGICHESKIY_KLASS'),
            'KOLESNAYA_FORMULA': data.get('KOLESNAYA_FORMULA'),
            'SHEMA_KOMPONOVKI': data.get('SHEMA_KOMPONOVKI'),
            'ZAGRUZOCHNOE_PROSTRANSTVO': data.get('ZAGRUZOCHNOE_PROSTRANSTVO'),
            'KABINA': data.get('KABINA'),
            'DVERI': data.get('DVERI'),
            'MESTA': data.get('MESTA')
        })
        
        # Оборудование
        prepared.update({
            'SHINY': data.get('SHINY'),
            'OBORUDOVANIE': data.get('OBORUDOVANIE'),
            'UVEOS': data.get('UVEOS')
        })
        
        # Базовое ТС
        if bazovoe := data.get('BAZOVOE_TS', {}):
            prepared.update({
                'BAZOVOE_VIN': bazovoe.get('vin'),
                'BAZOVOE_MODIFIKACIYA': bazovoe.get('modifikaciya')
            })
        
        # Данные СБКТС
        if sbkts := data.get('SBKTS', {}):
            prepared.update({
                'SBKTS_NOMER': sbkts.get('nomer'),
                'SBKTS_DATA_ZAYAVKI': sbkts.get('data_zayavki'),
                'SBKTS_INZHENER': sbkts.get('inzhener')
            })
        
        # Даты и документы
        prepared.update({
            'DATA_OFORMLENIYA': data.get('DATA_OFORMLENIYA')
        })
        
        return {k: v for k, v in prepared.items() if v is not None}

    def get_tables(self) -> list:
        """Получение списка таблиц в БД"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ОШИБКА] Получение списка таблиц: {e}")
            return []
    def _execute_query(self, query: str, params: tuple = ()):
        """Выполнение произвольного SQL запроса"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception as e:
            print(f"[ОШИБКА] Выполнение запроса: {e}")
            raise
        return cursor.fetchall() if cursor.description else None



class CustomDatabase:
    def __init__(self, table_name: str = None):
        """Инициализация подключения к БД с созданием указанной таблицы"""
        self.db_path = 'vehicles.db'
        self.table_name = table_name
        self._ensure_db_exists()
        
    def close(self):
        """Закрытие соединения с БД"""
        pass  # В SQLite соединения закрываются автоматически
        
    def _ensure_db_exists(self):
        """Проверяет существование БД и создает указанную таблицу если нужно"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if not self.table_name:
                    return
                    
                cursor = conn.cursor()
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT,
                        parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        MARKA TEXT,
                        KOMMERCHESKOE_NAIMENOVANIE TEXT,
                        TIP TEXT,
                        SHASSI TEXT,
                        KATEGORIA TEXT,
                        VIN TEXT,
                        GOD_VIPUSKA TEXT,
                        NOMER_REGISTRACII TEXT,
                        DVIGATEL_MODEL TEXT,
                        DVIGATEL_CYLINDRY TEXT,
                        DVIGATEL_MOSHNOST TEXT,
                        DVIGATEL_OBEM TEXT,
                        DVIGATEL_SZHATIYE TEXT,
                        ZAYAVITEL TEXT,
                        IZGOTOVITEL TEXT,
                        SBOROCHNIY_ZAVOD TEXT,
                        TOPLIVO_TIP TEXT,
                        TOPLIVO_SISTEMA_PITANIYA TEXT,
                        TOPLIVO_SISTEMA_VIPUSKA TEXT,
                        TRANSMISSIYA_TIP TEXT,
                        TRANSMISSIYA_SCEPLENIE TEXT,
                        TRANSMISSIYA_KOROBKA TEXT,
                        PODVESKA_PEREDNYAYA TEXT,
                        PODVESKA_ZADNYAYA TEXT,
                        RULEVOE_UPRAVLENIE TEXT,
                        TORMOZNAYA_RABOCHAYA TEXT,
                        TORMOZNAYA_ZAPASNAYA TEXT,
                        TORMOZNAYA_STOYANOCHNAYA TEXT,
                        TORMOZNAYA_VSPOMOGATELNAYA TEXT,
                        GABARITY_DLINA TEXT,
                        GABARITY_SHIRINA TEXT,
                        GABARITY_VYSOTA TEXT,
                        MASSA_SNARYAZHENNAYA TEXT,
                        MASSA_MAKSIMALNAYA TEXT,
                        BAZA TEXT,
                        KOLEYA TEXT,
                        EKOLOGICHESKIY_KLASS TEXT,
                        KOLESNAYA_FORMULA TEXT,
                        SHEMA_KOMPONOVKI TEXT,
                        ZAGRUZOCHNOE_PROSTRANSTVO TEXT,
                        KABINA TEXT,
                        TIP_KUZOVA_DVERI TEXT,
                        MESTA TEXT,
                        SHINY TEXT,
                        OBORUDOVANIE TEXT,
                        UVEOS TEXT,
                        BAZOVOE_VIN TEXT,
                        BAZOVOE_MODIFIKACIYA TEXT,
                        SBKTS_NOMER TEXT,
                        SBKTS_DATA_ZAYAVKI TEXT,
                        SBKTS_INZHENER TEXT,
                        DATA_OFORMLENIYA TEXT,
                        DAY TEXT,
                        MONTH TEXT,
                        suspicious INTEGER DEFAULT 0,
                        in_archive INTEGER DEFAULT 0,
                        temperature REAL,
                        humidity REAL
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[ОШИБКА] Создание таблицы {self.table_name}: {str(e)}")
            raise

    def prepare_vehicle_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Подготовка данных ТС для записи в БД"""
        prepared = {}
        
        # Основные данные
        prepared.update({
            'filename': data.get('filename'),
            'MARKA': data.get('MARKA'),
            'KOMMERCHESKOE_NAIMENOVANIE': data.get('KOMMERCHESKOE_NAIMENOVANIE'),
            'TIP': data.get('TIP'),
            'SHASSI': data.get('SHASSI'),
            'KATEGORIA': data.get('KATEGORIA'),
            'VIN': data.get('VIN'),
            'GOD_VIPUSKA': data.get('GOD_VIPUSKA'),
            'NOMER_REGISTRACII': data.get('NOMER_REGISTRACII')
        })
        
        # Данные двигателя
        if dvigatel := data.get('DVIGATEL', {}):
            prepared.update({
                'DVIGATEL_MODEL': dvigatel.get('model'),
                'DVIGATEL_CYLINDRY': dvigatel.get('cylindry'), 
                'DVIGATEL_MOSHNOST': dvigatel.get('moshnost'),
                'DVIGATEL_OBEM': dvigatel.get('obem'),
                'DVIGATEL_SZHATIYE': dvigatel.get('szhatiye')
            })
            
        prepared.update({
            'ZAYAVITEL': data.get('ZAYAVITEL'),
            'IZGOTOVITEL': data.get('IZGOTOVITEL'),
            'SBOROCHNIY_ZAVOD': data.get('SBOROCHNIY_ZAVOD')
        })
        
        # Данные топливной системы
        if toplivo := data.get('TOPLIVO', {}):
            prepared.update({
                'TOPLIVO_TIP': toplivo.get('tip'),
                'TOPLIVO_SISTEMA_PITANIYA': toplivo.get('sistema_pitaniya'),
                'TOPLIVO_SISTEMA_VIPUSKA': toplivo.get('sistema_vipuska')
            })
            
        # Данные трансмиссии
        if transmissiya := data.get('TRANSMISSIYA', {}):
            prepared.update({
                'TRANSMISSIYA_TIP': transmissiya.get('tip'),
                'TRANSMISSIYA_SCEPLENIE': transmissiya.get('sceplenie'),
                'TRANSMISSIYA_KOROBKA': transmissiya.get('korobka')
            })
            
        # Данные подвески
        if podveska := data.get('PODVESKA', {}):
            prepared.update({
                'PODVESKA_PEREDNYAYA': podveska.get('perednyaya'),
                'PODVESKA_ZADNYAYA': podveska.get('zadnyaya')
            })
            
        prepared.update({
            'RULEVOE_UPRAVLENIE': data.get('RULEVOE_UPRAVLENIE')
        })
        
        # Данные тормозной системы
        if tormoza := data.get('TORMOZNAYA_SISTEMA', {}):
            prepared.update({
                'TORMOZNAYA_RABOCHAYA': tormoza.get('rabochaya'),
                'TORMOZNAYA_ZAPASNAYA': tormoza.get('zapasnaya'),
                'TORMOZNAYA_STOYANOCHNAYA': tormoza.get('stoyanochnaya'),
                'TORMOZNAYA_VSPOMOGATELNAYA': tormoza.get('vspomogatelnaya')
            })
            
        # Габариты и масса
        if gabarity := data.get('GABARITY', {}):
            prepared.update({
                'GABARITY_DLINA': gabarity.get('dlina'),
                'GABARITY_SHIRINA': gabarity.get('shirina'),
                'GABARITY_VYSOTA': gabarity.get('vysota')
            })
            
        prepared.update({
            'MASSA_SNARYAZHENNAYA': data.get('MASSA_SNARYAZHENNAYA'),
            'MASSA_MAKSIMALNAYA': data.get('MASSA_MAKSIMALNAYA'),
            'BAZA': data.get('BAZA'),
            'KOLEYA': data.get('KOLEYA'),
            'EKOLOGICHESKIY_KLASS': data.get('EKOLOGICHESKIY_KLASS'),
            'KOLESNAYA_FORMULA': data.get('KOLESNAYA_FORMULA'),
            'SHEMA_KOMPONOVKI': data.get('SHEMA_KOMPONOVKI'),
            'ZAGRUZOCHNOE_PROSTRANSTVO': data.get('ZAGRUZOCHNOE_PROSTRANSTVO'),
            'KABINA': data.get('KABINA'),
            'TIP_KUZOVA_DVERI': data.get('TIP_KUZOVA_DVERI'),
            'MESTA': data.get('MESTA'),
            'SHINY': data.get('SHINY'),
            'OBORUDOVANIE': data.get('OBORUDOVANIE'),
            'UVEOS': data.get('UVEOS')
        })

        # Данные базового ТС
        if bazovoe := data.get('BAZOVOE_TS', {}):
            prepared.update({
                'BAZOVOE_VIN': bazovoe.get('vin'),
                'BAZOVOE_MODIFIKACIYA': bazovoe.get('modifikaciya')
            })

        # Данные СБКТС
        if sbkts := data.get('SBKTS', {}):
            prepared.update({
                'SBKTS_NOMER': sbkts.get('nomer'),
                'SBKTS_DATA_ZAYAVKI': sbkts.get('data_zayavki'),
                'SBKTS_INZHENER': sbkts.get('inzhener')
            })

        # Даты и документы
        prepared.update({
            'DATA_OFORMLENIYA': data.get('DATA_OFORMLENIYA'),
            'DAY': data.get('DAY'),
            'MONTH': data.get('MONTH'),
            'temperature': data.get('temperature'),
            'humidity': data.get('humidity')
        })
        
        return {k: v for k, v in prepared.items() if v is not None}

    def insert_vehicle_data(self, data: Dict[str, Any]) -> bool:
        """Вставка данных о ТС в БД"""
        try:
            prepared_data = self.prepare_vehicle_data(data)
            
            if not prepared_data:
                print("[ОШИБКА] Нет данных для вставки")
                return False
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем список колонок
                cursor.execute(f"PRAGMA table_info({self.table_name})")
                existing_columns = {row[1] for row in cursor.fetchall()}
                
                # Формируем запрос
                columns = []
                values = []
                
                for key, value in prepared_data.items():
                    if key in existing_columns:
                        columns.append(key)
                        values.append(value)
                
                query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(['?' for _ in values])})"
                cursor.execute(query, values)
                conn.commit()
                
                return True
                
        except Exception as e:
            print(f"[ОШИБКА] Вставка данных в БД: {str(e)}")
            return False

    def get_tables(self) -> list:
        """Получение списка таблиц в БД"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ОШИБКА] Получение списка таблиц: {e}")
            return []

    def _execute_query(self, query: str, params: tuple = ()):
        """Выполнение произвольного SQL запроса"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.fetchall() if cursor.description else None
        except Exception as e:
            print(f"[ОШИБКА] Выполнение запроса: {e}")
            raise

