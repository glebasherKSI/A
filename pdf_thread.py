from PyQt6.QtCore import QThread, pyqtSignal
import os
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import traceback
from database import Database, CustomDatabase
from pdf_parser import PDFParser

@dataclass
class ProcessingResult:
    """Результат обработки одного PDF файла"""
    filename: str
    success: bool
    data: Dict[str, Any]
    error: str = ""

class PDFProcessThread(QThread):
    progress_updated = pyqtSignal(int)
    file_processed = pyqtSignal(str, dict)
    processing_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    stats_updated = pyqtSignal(int, int)

    def __init__(self, folder_path: str, excel_path: str = None, sheet_name: str = None, 
                 sbkts_excel_path: str = None, sbkts_sheet_name: str = None, table_name: str = None):
        super().__init__()
        self.folder_path = folder_path
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        self.sbkts_excel_path = sbkts_excel_path
        self.sbkts_sheet_name = sbkts_sheet_name
        self.table_name = table_name
        self.is_running = True
        self.results: List[ProcessingResult] = []

    def run(self):
        try:
            # Создаем парсер и БД
            parser = PDFParser(
                excel_path=self.excel_path,
                sheet_name=self.sheet_name,
                sbkts_excel_path=self.sbkts_excel_path,
                sbkts_sheet_name=self.sbkts_sheet_name
            )
            db = CustomDatabase(self.table_name)
            
            # Получаем список PDF файлов
            pdf_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.pdf')]
            total_files = len(pdf_files)
            
            if not pdf_files:
                self.error_occurred.emit("В указанной папке не найдены PDF файлы")
                return
                
            # Обрабатываем каждый файл
            for i, filename in enumerate(pdf_files, 1):
                if not self.is_running:
                    break
                    
                try:
                    # Полный путь к файлу
                    file_path = os.path.join(self.folder_path, filename)
                    
                    # Извлекаем текст из PDF
                    text = parser.extract_text_from_pdf(file_path)
                    
                    # Парсим данные используя существующий парсер
                    data = parser.parse_vehicle_data(text)
                    
                    # Проверяем обязательные поля
                    if not all(data.get(field) for field in ['MARKA', 'VIN', 'GOD_VIPUSKA']):
                        raise ValueError("Отсутствуют обязательные поля (MARKA, VIN, GOD_VIPUSKA)")
                    data['filename'] = filename
                    # Сохраняем в БД
                    if db.insert_vehicle_data(data):
                        result = ProcessingResult(filename=filename, success=True, data=data)
                        self.file_processed.emit(filename, data)
                    else:
                        raise ValueError("Не удалось сохранить данные в БД")
                        
                except Exception as e:
                    error_msg = f"Ошибка обработки {filename}: {str(e)}"
                    self.error_occurred.emit(error_msg)
                    result = ProcessingResult(
                        filename=filename,
                        success=False,
                        data={},
                        error=error_msg
                    )
                
                self.results.append(result)
                self.progress_updated.emit(int(i / total_files * 100))
                
            # Выводим итоговую статистику
            success_count = sum(1 for r in self.results if r.success)
            self.stats_updated.emit(success_count, len(self.results))
            self.error_occurred.emit(
                f"\nОбработка завершена:\n"
                f"Успешно: {success_count}\n"
                f"Ошибок: {len(self.results) - success_count}"
            )
            
        except Exception as e:
            self.error_occurred.emit(f"Критическая ошибка: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.processing_finished.emit()
            
    def stop(self):
        self.is_running = False 