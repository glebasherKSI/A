from PyPDF2 import PdfReader
import re
from datetime import datetime
from utils import read_excel_data, get_sbkts_data
import json
from typing import Dict, Any, Optional
from copy import deepcopy

class PDFParser:
    _sbkts_df = None  # Статический DataFrame для всех экземпляров класса
    
    @classmethod
    def load_sbkts_data(cls, excel_path: str, sheet_name: str = None):
        """Загружает данные СБКТС один раз для всех экземпляров класса"""
        if cls._sbkts_df is None:
            cls._sbkts_df = get_sbkts_data(excel_path, sheet_name)
            print(f"[DEBUG PARSER] СБКТС данные загружены, строк: {len(cls._sbkts_df) if cls._sbkts_df is not None else 0}")
    
    def __init__(self, excel_path: str = None, sheet_name: str = None, sbkts_excel_path: str = None, sbkts_sheet_name: str = None):
        print(f"\n[DEBUG PARSER] Инициализация PDFParser:")
        print(f"[DEBUG PARSER] Excel файл с погодой: {excel_path}")
        print(f"[DEBUG PARSER] Excel файл СБКТС: {sbkts_excel_path}")
        print(f"[DEBUG PARSER] Лист СБКТС: {sbkts_sheet_name}")
        self.df_climate_date = read_excel_data(excel_path, sheet_name) if excel_path != None else None
        
        # Загружаем СБКТС данные, если они еще не загружены
        if sbkts_excel_path and self._sbkts_df is None:
            self.load_sbkts_data(sbkts_excel_path, sbkts_sheet_name)
            
        # Инициализируем словарь для хранения данных о транспортном средстве
        self.vehicle_data = {
            # Основная информация о транспортном средстве
            'MARKA': '',                    # Марка транспортного средства
            'KOMMERCHESKOE_NAIMENOVANIE': '', # Коммерческое наименование
            'TIP': '',                      # Тип транспортного средства
            'SHASSI': '',                   # Номер шасси
            'VIN': '',                      # Идентификационный номер (VIN)
            'GOD_VIPUSKA': '',              # Год выпуска
            'KATEGORIA': '',                # Категория транспортного средства
            'EKOLOGICHESKIY_KLASS': '',     # Экологический класс
            'DATA_OFORMLENIYA': '',        # Дата оформления документа (дд.мм.гггг)
            'DAY':'',
            'MONTH':'',
            
            # Информация о производителе и заявителе
            'ZAYAVITEL': '',                # Заявитель и его адрес
            'IZGOTOVITEL': '',              # Изготовитель и его адрес
            'SBOROCHNIY_ZAVOD': '',         # Сборочный завод и его адрес
            
            # Технические характеристики шасси
            'KOLESNAYA_FORMULA': '',        # Колесная формула/ведущие колеса
            'SHEMA_KOMPONOVKI': '',         # Схема компоновки транспортного средства
            'ZAGRUZOCHNOE_PROSTRANSTVO': '', # Исполнение загрузочного пространства
            'KABINA': '',                   # Тип кабины
            
            # Массогабаритные характеристики
            'MASSA_SNARYAZHENNAYA': '',     # Масса в снаряженном состоянии, кг
            'MASSA_MAKSIMALNAYA': '',       # Технически допустимая максимальная масса, кг
            'GABARITY': {                   # Габаритные размеры
                'dlina': '',                # Длина, мм
                'shirina': '',              # Ширина, мм
                'vysota': ''                # Высота, мм
            },
            'BAZA': '',                     # База, мм
            'KOLEYA': '',                   # Колея передних/задних колес, мм
            
            # Характеристики двигателя
            'DVIGATEL': {
                'model': '',                # Марка и тип двигателя
                'cylindry': '',             # Количество и расположение цилиндров
                'moshnost': '',             # Максимальная мощность, кВт (мин-1)
                'obem': '',                 # Рабочий объем цилиндров, см³
                'szhatiye': ''              # Степень сжатия
            },
            
            # Топливная система
            'TOPLIVO': {
                'tip': '',                  # Тип топлива
                'sistema_pitaniya': '',     # Система питания (тип)
                'sistema_vipuska': ''       # Система выпуска и нейтрализации отработавших газов
            },
            
            # Трансмиссия
            'TRANSMISSIYA': {
                'tip': '',                  # Тип трансмиссии
                'sceplenie': '',            # Сцепление (марка, тип)
                'korobka': ''               # Коробка передач (марка, тип)
            },
            
            # Подвеска
            'PODVESKA': {
                'perednyaya': '',           # Передняя подвеска
                'zadnyaya': ''              # Задняя подвеска
            },
            
            # Рулевое управление
            'RULEVOE_UPRAVLENIE': '',       # Рулевое управление (марка, тип)
            
            # Тормозная система
            'TORMOZNAYA_SISTEMA': {
                'rabochaya': '',            # Рабочая тормозная система
                'stoyanochnaya': '',        # Стояночная тормозная система
                'zapasnaya': '',            # Запасная тормозная система
                'vspomogatelnaya': ''       # Вспомогательная тормозная система
            },
            
            # Шины и дополнительное оборудование
            'SHINY': '',                    # Размерность шин
            'OBORUDOVANIE': '',             # Оборудование транспортного средства
            'UVEOS': '',                    # Номер УВЭОС
            
            # Информация о базовом транспортном средстве
            'BAZOVOE_TS': {
                'vin': '',                  # VIN базового транспортного средства
                'modifikaciya': ''          # Модификация базового транспортного средства
            },
            
            # Данные из Excel файла СБКТС
            'SBKTS': {
                'nomer': '',                # Номер п/п из Excel
                'data_zayavki': '',         # Дата заявки из Excel
                'inzhener': ''              # Инженер из Excel
            }
        }
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        self.sbkts_excel_path = sbkts_excel_path
        self.sbkts_sheet_name = sbkts_sheet_name
        
        # Словарь для преобразования месяцев
        self.month_map = {
            'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
            'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
            'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
        }
        
        # Общий словарь паттернов для всех типов ТС
        self.patterns = {
            'MARKA': r'МАРКА\s+(.+?)(?=\n|КОММЕРЧЕСКОЕ)',
            'KOMMERCHESKOE_NAIMENOVANIE': r'КОММЕРЧЕСКОЕ\s+НАИМЕНОВАНИЕ\s*(.+?)(?=\n|ТИП)',
            'TIP': r'ТИП\s+(.+?)(?=\n|ШАССИ)',
            'SHASSI': r'ШАССИ\s+(.+?)(?=\n|ИДЕНТИФИКАЦИОН)',
            'VIN': r'ИДЕНТИФИКАЦИОН\s*НЫЙ\s+НОМЕР\s+\(VIN\)\s*(.+?)(?=\n|ГОД)',
            'GOD_VIPUSKA': r'ГОД\s+ВЫПУСКА\s+(.+?)(?=\n|КАТЕГОРИЯ)',
            'KATEGORIA': r'КАТЕГОРИЯ\s+(.+?)(?=\n|ЭКОЛОГИЧЕСКИЙ)',
            'EKOLOGICHESKIY_KLASS': r'ЭКОЛОГИЧЕСКИЙ\s+КЛАСС\s*(.+?)(?=\n|ЗАЯВИТЕЛЬ)',
            'ZAYAVITEL': r'ЗАЯВИТЕЛЬ\s+И\s+ЕГО\s+АДРЕС\s*(.+?)(?=ТРАНСПОРТНОЕ\s+СРЕДСТВО|ИЗГОТОВИТЕЛЬ)',
            'IZGOTOVITEL': r'ИЗГОТОВИТЕЛЬ\s+И\s+ЕГО\s+АДРЕС\s*(.+?)(?=СБОРОЧНЫЙ\s+ЗАВОД|ТРАНСПОРТНОЕ\s+СРЕДСТВО)',
            'SBOROCHNIY_ZAVOD': r'СБОРОЧНЫЙ\s+ЗАВОД\s+И\s+ЕГО\s+АДРЕС\s*(.+?)(?=Колесная|ТРАНСПОРТНОЕ\s+СРЕДСТВО)',
            'KOLESNAYA_FORMULA': r'Колесная\s+формула/ведущие\s+колеса\s*(.+?)(?=\n|Схема)',
            'SHEMA_KOMPONOVKI': r'Схема\s+компоновки\s+транспортного\s+средства\s*(.+?)(?=\n|Тип)',
            'TIP_KUZOVA': r'Тип\s+кузова/количество\s+дверей\s*(.+?)(?=\n|Количество)',
            'MESTA': r'Количество\s+мест\s+спереди/сзади\s*(.+?)(?=\n|Масса)',
            'MASSA_SNARYAZHENNAYA': r'Масса\s+транспортного\s+средства\s+в\s+снаряженном\s+состоянии,\s+кг\s*(\d+)',
            'MASSA_MAKSIMALNAYA': r'Технически\s+допустимая\s+максимальная\s+масса\s+транспортного\s+средства,\s+кг\s*(\d+)',
            'GABARITY': r'Габаритные\s+размеры,\s+мм\s*\n-\s*длина\s+(\d+)\s*\n-\s*ширина\s+(\d+)\s*\n-\s*высота\s+(\d+)',
            'BAZA': r'База,\s+мм\s+(\d+)',
            'KOLEYA': r'Колея\s+передних/задних\s+колес,\s+мм\s*(.+?)(?=\n|Двигатель)',
            'DVIGATEL_MODEL': r'Двигатель\s+внутреннего\s+сгорания\s+\(марка,\s+тип\)\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*-\s*количество|ОБЩИЕ)',
            'DVIGATEL_CYLINDRY': r'количество\s+и\s+расположение\s+цилиндров\s*(.+?)(?=\n|-\s*рабочий)',
            'DVIGATEL_OBEM': r'рабочий\s+объем\s+цилиндров,\s+см³\s*(\d+)',
            'DVIGATEL_SZHATIYE': r'степень\s+сжатия\s+(.+?)(?=\n|-\s*максимальная)',
            'DVIGATEL_MOSHNOST': r'максимальная\s+мощность,\s+кВт\s+\(мин-1\)\s*(.+?)(?=\n|Топливо)',
            'TOPLIVO_TIP': r'Топливо\s+(.+?)(?=\n|Система)',
            'TOPLIVO_SISTEMA_PITANIYA': r'Система\s+питания\s+\(тип\)\s+(.+?)(?=\n|Система\s+выпуска)',
            'TOPLIVO_SISTEMA_VIPUSKA': r'Система\s+выпуска\s+и\s+нейтрализации\s+отработавших\s+газов\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*Трансмиссия)',
            'TRANSMISSIYA_TIP': r'Трансмиссия\s+(.+?)(?=\n|Сцепление)',
            'TRANSMISSIYA_SCEPLENIE': r'Сцепление\s+\(марка,\s+тип\)\s+(.+?)(?=\n|Коробка)',
            'TRANSMISSIYA_KOROBKA': r'Коробка\s+передач\s+\(марка,\s+тип\)\s*(.+?)(?=\n|Подвеска)',
            'PODVESKA_PEREDNYAYA': r'Подвеска\s*\(тип\)\s*\n\s*Передняя\s+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*Задняя)',
            'PODVESKA_ZADNYAYA': r'Задняя\s+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*Рулевое)',
            'RULEVOE_UPRAVLENIE': r'Рулевое\s+управление\s*(?:\(марка,\s*тип\))?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*Тормозные)',
            # 'RULEVOE_UPRAVLENIE': r'Рулевое\s+управление\s+\(марка,\s+тип\)\s*(.+?)(?=\n|Тормозные)',
            'TORMOZNAYA_RABOCHAYA': r'-\s*рабочая\s+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*-\s*запасная)',
            'TORMOZNAYA_ZAPASNAYA': r'-\s*запасная\s+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*-\s*стояночная)',
            'TORMOZNAYA_STOYANOCHNAYA': r'-\s*стояночная\s+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:-\s*вспомогательная|Шины))',
            'TORMOZNAYA_VSPOMOGATELNAYA': r'-\s*вспомогательная\s*\(?износостойкая\)?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*Шины)',
            'SHINY': r'Шины\s+(.+?)(?=\n|Оборудование)',
            'OBORUDOVANIE': r'Оборудование\s+транспортного\s+средства\s*(.+?)(?=соответствуют|номер\s+УВЭОС)',
            'UVEOS': r'номер\s+УВЭОС\s+(\d+)',
            'BAZOVOE_VIN': r'Идентификационный\s+номер\s+шасси\s+([A-Z0-9]+)',
            'BAZOVOE_MODIFIKACIYA': r'модификации\s+(\d+)',
            'DATA_OFORMLENIYA': r'Дата\s+оформления\s+"(\d{2})"\s+([а-я]+)\s+(\d{4})',
            'TIP_KUZOVA_DVERI': r'(?:Тип\s+кузова\s*/\s*количество\s+дверей|Тип\s+кузова[^\n]*?/[^\n]*?двер(?:ей|и))\s*([^\n]+?)(?=\s*Количество|$)',
            'NOMER_REGISTRACII': r'№\s*ТС\s*([A-Z]{2}\s*[А-Я]-[A-Z]{2}\.\d+\.\d+)',
           
        }

        # Специфические поля для разных категорий
        self.category_fields = {
            'M1': {
                'PASSAZHIROVMESTIMOST': r'Пассажировместимость\s*[:-]?\s*(\d+)',
                'OBEM_BAGAZHNIKA': r'Объем\s+багажника,\s*л\s*(\d+)',
                'PODUSHKI_BEZOPASNOSTI': r'Подушки\s+безопасности\s+([^\n]+)',
                'KLIMAT_USTANOVKA': r'Климатическая\s+установка\s+([^\n]+)',
                'TIP_KUZOVA_DVERI': r'(?:Тип\s+кузова\s*/\s*количество\s+дверей|Тип\s+кузова[^\n]*?/[^\n]*?двер(?:ей|и))\s*([^\n]+?)(?=\s*Количество|$)',
                'MESTA_SPEREDI_SZADI': r'(?:Количество\s+мест\s+спереди\s*/\s*сзади|Количество\s+мест[^\n]*?спереди[^\n]*?сзади)\s*(\d+\s*/\s*\d+)',
                'SHEMA_KOMPONOVKI': r'(?:(?:Схема\s*компоновки\s*транспортного\s*средства|(?:капотная|вагонная|полукапотная|кабина\s+над\s+двигателем|переднеприводная))\s*(.*?))(?=\s*(?:Исполнение|Тип|$))'
            },
            'M3': {
                'PASSAZHIROVMESTIMOST': r'Пассажировместимость\s*[:-]?\s*(\d+)',
                'MESTA_DLYA_STOYANIYA': r'Места\s+для\s+стояния\s*[:-]?\s*(\d+)',
                'AVARIYNIE_VYHODY': r'Аварийные\s+выходы\s+([^\n]+)',
                'MARSHRUTOUKAZATELI': r'Маршрутоуказатели\s+([^\n]+)',
                'SHEMA_KOMPONOVKI': r'Схема\s+компоновки\s+([^\n]+)'
            },
            'N2': {
                'GRUZOPODYEMNOST': r'Грузоподъемность,\s*кг\s*(\d+)',
                'OBEM_GRUZOVOGO_OTSEKA': r'Объем\s+грузового\s+отсека,\s*м³\s*(\d+(?:\.\d+)?)',
                'POGRUZOCHNAYA_VYSOTA': r'Погрузочная\s+высота,\s*мм\s*(\d+)',
                'SHEMA_KOMPONOVKI': r'Схема\s+компоновки\s+([^\n]+)'
            },
            'N3': {
                'GRUZOPODYEMNOST': r'Грузоподъемность,\s*кг\s*(\d+)',
                'NAGRUZKA_SSU': r'Нагрузка\s+на\s+седельно-сцепное\s+устройство,\s*кг\s*(\d+)',
                'MASSA_PRICEPA': r'Масса\s+буксируемого\s+прицепа,\s*кг\s*(\d+)',
                'SHEMA_KOMPONOVKI': r'Схема\s+компоновки\s+([^\n]+)'
            },
            'O4': {
                'GRUZOPODYEMNOST': r'Грузоподъемность,\s*кг\s*(\d+)',
                'KOLICHESTVO_OSEY': r'Количество\s+осей\s*[:-]?\s*(\d+)',
                'NAGRUZKA_SHKVORNYA': r'Нагрузка\s+на\s+шкворень,\s*кг\s*(\d+)',
                'SHEMA_KOMPONOVKI': r'Схема\s+компоновки\s+([^\n]+)'
            }
        }
    def get_climate_data(self, date_str: str) -> Optional[Dict[str, float]]:
        """
        Получает данные о температуре и влажности по дате.
        
        Args:
            date_str (str): Дата в формате dd.mm.yyyy
            
        Returns:
            Optional[Dict[str, float]]: Словарь с температурой и влажностью или None
        """
        try:
            if not self.df_climate_date is not None:
                return None
                
            # Преобразуем строку в datetime
            date = datetime.strptime(date_str, '%d.%m.%Y')
            
            # Находим колонки с датой, температурой и влажностью
            date_col = None
            temp_col = None
            humid_col = None
            
            for col in self.df_climate_date.columns:
                col_lower = col.lower()
                if self.df_climate_date[col].dtype == 'datetime64[ns]':
                    date_col = col
                elif 'темп' in col_lower or 'temp' in col_lower:
                    temp_col = col  
                elif 'влаж' in col_lower or 'humid' in col_lower:
                    humid_col = col

            if not all([date_col, temp_col, humid_col]):
                return None

            # Ищем строку с нужной датой
            row = self.df_climate_date[self.df_climate_date[date_col].dt.date == date.date()]
            
            if row.empty:
                return None
                
            return {
                'temperature': float(row[temp_col].iloc[0]),
                'humidity': float(row[humid_col].iloc[0])
            }
            
        except Exception as e:
            print(f"Ошибка при получении климатических данных: {str(e)}")
            return None
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Извлекает текст из PDF файла"""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            # Очищаем текст от служебных фраз
            text = re.sub(r'(?:ОБЩИЕ ХАРАКТЕРИСТИКИ ТРАНСПОРТНОГО СРЕДСТВАМ\.П\.Стр\.\d|ТРАНСПОРТНОЕ СРЕДСТВОМ\.П\.Стр\.\d|М\.П\.Стр\.\d)\s*ТС\s*BY\s*А-BY\.\d+\.\d+Свидетельство\s*о\s*безопасности\s*конструкции\s*транспортного\s*средства\s*№', '', text)
            print(text)
            return text
        except Exception as e:
            raise Exception(f"Ошибка при чтении PDF файла: {str(e)}")
            
    def parse_vehicle_data(self, text):
        """Извлекает данные о транспортном средстве из текста PDF"""
        result_data = deepcopy(self.vehicle_data)
        
        # Обрабатываем все поля
        for key, pattern in self.patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                if key == 'GABARITY':
                    result_data[key] = {
                        'dlina': match.group(1),
                        'shirina': match.group(2),
                        'vysota': match.group(3)
                    }
                elif key == 'DATA_OFORMLENIYA':
                    day = match.group(1)
                    month_name = match.group(2)
                    year = match.group(3)
                    month = self.month_map.get(month_name.lower(), '01')
                    day = day.zfill(2)
                    result_data[key] = f"{day}.{month}.{year}"
                    result_data['DAY'] = day
                    result_data['MONTH'] = month_name
                    wether = self.get_climate_data(result_data[key])
                    if wether:
                        result_data['temperature'] = wether['temperature']
                        result_data['humidity'] = wether['humidity']
                
                elif key == 'SHASSI':
                    result_data['SHASSI'] = self._clean_value(match.group(1))
                elif key == 'ZAYAVITEL':
                    
                    result_data['ZAYAVITEL'] = self._clean_value(match.group(1))
                elif key == 'IZGOTOVITEL':
                    result_data['IZGOTOVITEL'] = self._clean_value(match.group(1))
                elif key == 'RULEVOE_UPRAVLENIE':
                    result_data['RULEVOE_UPRAVLENIE'] = self._clean_value(match.group(1))
                elif key == 'SBOROCHNIY_ZAVOD':
                    result_data['SBOROCHNIY_ZAVOD'] = self._clean_value(match.group(1))
                elif key == 'TIP_KUZOVA_DVERI':
                    print(f"[DEBUG PDF] TIP_KUZOVA_DVERI: {match.group(1)}")
                    result_data['TIP_KUZOVA_DVERI'] = self._clean_value(match.group(1))
                elif key.startswith('DVIGATEL_'):
                    field_name = key.replace('DVIGATEL_', '').lower()
                    result_data['DVIGATEL'][field_name] = self._clean_value(match.group(1))
                elif key.startswith('TOPLIVO_'):
                    field_name = key.replace('TOPLIVO_', '').lower()
                    print(f"[DEBUG PDF] TOPLIVO_: {match.group(1)}")
                    result_data['TOPLIVO'][field_name] = self._clean_value(match.group(1))
                elif key.startswith('TRANSMISSIYA_'):
                    field_name = key.replace('TRANSMISSIYA_', '').lower()
                    result_data['TRANSMISSIYA'][field_name] = self._clean_value(match.group(1))
                elif key.startswith('PODVESKA_'):
                    field_name = key.replace('PODVESKA_', '').lower()
                    result_data['PODVESKA'][field_name] = self._clean_value(match.group(1))
                elif key.startswith('TORMOZNAYA_'):
                    field_name = key.replace('TORMOZNAYA_', '').lower()
                    result_data['TORMOZNAYA_SISTEMA'][field_name] = self._clean_value(match.group(1))
                elif key.startswith('BAZOVOE_'):
                    field_name = key.replace('BAZOVOE_', '').lower()
                    result_data['BAZOVOE_TS'][field_name] = self._clean_value(match.group(1))
                else:
                    result_data[key] = self._clean_value(match.group(1))

        # Получаем данные из СБКТС Excel
        if self._sbkts_df is not None and result_data.get('NOMER_REGISTRACII'):
            print(f"\n[DEBUG PDF] Пытаемся получить данные СБКТС:")
            print(f"[DEBUG PDF] VIN: {result_data['NOMER_REGISTRACII']}")
            
            try:
                # Проверяем наличие нужной колонки
                model_column = None
                for col in self._sbkts_df.columns:
                    if 'регистрационный' in col.lower() and 'номер' in col.lower() and 'сбктс' in col.lower():
                        model_column = col
                        break
                
                if model_column is None:
                    print("[DEBUG PDF] Не найдена колонка")
                    return result_data
                
                # Ищем строку с нужным VIN
                vin_mask = self._sbkts_df[model_column].astype(str).str.contains(result_data['NOMER_REGISTRACII'], na=False, case=False, regex=False)
                matching_row = self._sbkts_df[vin_mask]
                
                if not matching_row.empty:
                    # Берем первую найденную строку
                    row = matching_row.iloc[0]
                    
                    # Ищем нужные колонки и заполняем данные
                    for col in row.index:
                        col_lower = col.lower()
                        if '№' in col and 'п/п' in col:
                            result_data['SBKTS']['nomer'] = str(row[col])
                        elif 'дата' in col_lower and 'заяв' in col_lower:
                            result_data['SBKTS']['data_zayavki'] = row[col].strftime('%d.%m.%Y') if isinstance(row[col], datetime) else str(row[col])
                        elif 'инженер' in col_lower:
                            result_data['SBKTS']['inzhener'] = str(row[col])
                    
                            print("[DEBUG PDF] Данные СБКТС успешно получены")
                    else:
                            print(f"[DEBUG PDF] VIN {result_data['VIN']} не найден в СБКТС")
                    
            except Exception as e:
                print(f"[DEBUG PDF] Ошибка при обработке СБКТС: {str(e)}")
                import traceback
                print(f"[DEBUG PDF] Полный стек ошибки:\n{traceback.format_exc()}")
                
        else:
            print(f"\n[DEBUG PDF] Пропускаем поиск данных СБКТС:")
            print(f"[DEBUG PDF] DataFrame СБКТС установлен: {self._sbkts_df is not None}")
            print(f"[DEBUG PDF] VIN найден: {bool(result_data.get('VIN'))}")
        print(result_data)          
        return result_data

    def get_vehicle_data(self):
        return self.vehicle_data 

    def _clean_value(self, value: str) -> str:
        """Очищает значение от лишних пробелов и символов"""
        if not value:
            return value
        return re.sub(r'\s+', ' ', value.strip())

    

       

    

  