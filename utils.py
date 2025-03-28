import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict
import os
import re

def read_excel_data(excel_path: str, date: datetime, sheet_name: str = None) -> Optional[pd.DataFrame]:
    """
    Читает Excel файл и возвращает подготовленный для поиска данных DataFrame.
    
    Args:
        excel_path (str): Путь к Excel файлу
        date (datetime): Дата, для которой нужно получить данные
        sheet_name (str): Название листа Excel (если None, берется первый лист)
        
    Returns:
        Optional[pd.DataFrame]: Подготовленный DataFrame или None в случае ошибки
    """
    try:
        if not excel_path or not os.path.exists(excel_path):
            print(f"[DEBUG CLIMATE] Excel файл не найден: {excel_path}")
            return None
            
        # Читаем Excel файл
        print(f"[DEBUG CLIMATE] Читаем Excel файл: {excel_path}")
        
        # Если лист не указан, читаем первый лист
        if sheet_name is None:
            # Получаем список всех листов
            all_sheets = pd.read_excel(excel_path, sheet_name=None)
            if not all_sheets:
                print("[DEBUG CLIMATE] Excel файл не содержит листов")
                return None
            # Берем первый лист
            sheet_name = list(all_sheets.keys())[0]
            
        # Читаем конкретный лист
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        print(f"[DEBUG CLIMATE] Читаем лист: {sheet_name}")
        print(f"[DEBUG CLIMATE] Доступные колонки: {list(df.columns)}")
        
        # Конвертируем столбец с датой в datetime
        date_column = None
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]' or 'date' in col.lower() or 'дата' in col.lower():
                date_column = col
                # Пробуем сконвертировать разные форматы даты
                try:
                    df[col] = pd.to_datetime(df[col], format='%d.%m.%Y', errors='coerce')
                except:
                    try:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    except:
                        continue
                print(f"[DEBUG CLIMATE] Найдена колонка с датой: {col}")
                break
                
        if date_column is None:
            print("[DEBUG CLIMATE] Колонка с датой не найдена")
            return None
            
        # Ищем столбцы с температурой и влажностью
        temp_column = None
        humidity_column = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'temp' in col_lower or 'температура' in col_lower:
                temp_column = col
                print(f"[DEBUG CLIMATE] Найдена колонка с температурой: {col}")
            elif 'humid' in col_lower or 'влажность' in col_lower:
                humidity_column = col
                print(f"[DEBUG CLIMATE] Найдена колонка с влажностью: {col}")
                
        if temp_column is None or humidity_column is None:
            print("[DEBUG CLIMATE] Не найдены колонки с температурой или влажностью")
            return None

        # Возвращаем подготовленный DataFrame с найденными колонками
        return df[[date_column, temp_column, humidity_column]]
        
    except Exception as e:
        print(f"[DEBUG CLIMATE] Ошибка: {str(e)}")
        return None

def get_climate_data(excel_path: str, date: datetime, sheet_name: str = None) -> Optional[Dict[str, float]]:
    """
    Получает данные о температуре и влажности.
    
    Args:
        excel_path (str): Путь к Excel файлу
        date (datetime): Дата, для которой нужно получить данные
        sheet_name (str): Название листа Excel (если None, берется первый лист)
        
    Returns:
        Optional[Dict[str, float]]: Словарь с температурой и влажностью или None
    """
    print(f"[DEBUG CLIMATE] Запрос данных для даты: {date}")
    return read_excel_data(excel_path, date, sheet_name)

def get_sbkts_data(excel_path: str, sheet_name: str = None) -> Optional[pd.DataFrame]:
    """
    Получает подготовленный DataFrame из Excel файла СБКТС.
    
    Args:
        excel_path (str): Путь к Excel файлу
        sheet_name (str): Название листа Excel (если None, берется первый лист)
        
    Returns:
        Optional[pd.DataFrame]: Подготовленный DataFrame или None в случае ошибки
    """
    try:
        if not excel_path or not os.path.exists(excel_path):
            print(f"[DEBUG SBKTS] Excel файл не найден: {excel_path}")
            return None
            
        print(f"[DEBUG SBKTS] Читаем Excel файл: {excel_path}")
        
        # Если лист не указан, читаем первый лист
        if sheet_name is None:
            # Получаем список всех листов
            all_sheets = pd.read_excel(excel_path, sheet_name=None)
            if not all_sheets:
                print("[DEBUG SBKTS] Excel файл не содержит листов")
                return None
            # Берем первый лист
            sheet_name = list(all_sheets.keys())[0]
            
        # Читаем Excel файл
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        print(f"[DEBUG SBKTS] Прочитан лист: {sheet_name}")
        print(f"[DEBUG SBKTS] Доступные колонки: {list(df.columns)}")
        
        # Проверяем наличие нужных колонок
        required_columns = []
        
        # Ищем колонку с регистрационным номером СБКТС
        reg_number_column = None
        for col in df.columns:
            if 'регистрационный' in col.lower() and 'номер' in col.lower() and 'сбктс' in col.lower():
                reg_number_column = col
                required_columns.append(col)
                print(f"[DEBUG SBKTS] Найдена колонка с рег. номером СБКТС: {col}")
                break
                
        if reg_number_column is None:
            print("[DEBUG SBKTS] Не найдена колонка с рег. номером СБКТС")
            return None
            
        # Ищем остальные нужные колонки
        for col in df.columns:
            col_lower = col.lower()
            # Колонка с номером
            if '№' in col and 'п/п' in col:
                required_columns.append(col)
                print(f"[DEBUG SBKTS] Найдена колонка с номером: {col}")
            # Колонка с датой    
            elif 'дата' in col_lower and 'заяв' in col_lower:
                required_columns.append(col)
                print(f"[DEBUG SBKTS] Найдена колонка с датой: {col}")
            # Колонка с инженером    
            elif 'инженер' in col_lower:
                required_columns.append(col)
                print(f"[DEBUG SBKTS] Найдена колонка с инженером: {col}")
                
        if len(required_columns) < 4:  # Рег. номер + 3 обязательных поля
            print("[DEBUG SBKTS] Не найдены все необходимые колонки")
            print(f"[DEBUG SBKTS] Найденные колонки: {required_columns}")
            return None
            
        # Возвращаем DataFrame только с нужными колонками
        result_df = df[required_columns]
        print(f"[DEBUG SBKTS] Данные успешно подготовлены, строк: {len(result_df)}")
        
        return result_df
        
    except Exception as e:
        print(f"[DEBUG SBKTS] Ошибка при обработке СБКТС: {str(e)}")
        import traceback
        print(f"[DEBUG SBKTS] Полный стек ошибки:\n{traceback.format_exc()}")
        return None

if __name__ == "__main__":
    data = get_sbkts_data(excel_path='СБКТС_ЕТС 2025.xlsx', sheet_name='5-22 Журнал СБКТС 2024')
    
            