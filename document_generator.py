from pathlib import Path
import os
from typing import List, Dict, Any
from docxtpl import DocxTemplate
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, 
                           QWidget, QCheckBox, QPushButton, QFileDialog,
                           QProgressDialog, QLabel)
from PyQt6.QtCore import QThread, pyqtSignal
import shutil

class DocumentGeneratorThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    processed_ids = pyqtSignal(list)
    
    def __init__(self, templates: List[str], save_path: str, data: List[Dict[str, Any]]):
        super().__init__()
        self.templates = templates
        self.save_path = save_path
        self.data = data
        self.successful_ids = []
        
    def run(self):
        try:
            total_steps = len(self.data) * len(self.templates)
            current_step = 0
            
            for row_data in self.data:
                success = True
                
                # Создаем папку для документов
                folder_name = f"{row_data.get('SBKTS_NOMER')} СБКТС {row_data.get('MARKA')} {row_data.get('VIN')}"
                folder_path = Path(self.save_path) / folder_name
                folder_path.mkdir(parents=True, exist_ok=True)
                
                # Обрабатываем каждый шаблон
                for template_path in self.templates:
                    try:
                        # Загружаем шаблон
                        doc = DocxTemplate(template_path)
                        
                        # Рендерим документ
                        doc.render(row_data)
                        
                        # Сохраняем документ
                        template_name = Path(template_path).stem
                        output_file = folder_path / f"{template_name}_{row_data.get('VIN', 'NO_VIN')}.docx"
                        doc.save(output_file)
                        
                        current_step += 1
                        self.progress.emit(int(current_step * 100 / total_steps))
                        
                    except Exception as e:
                        self.error.emit(f"Ошибка при обработке шаблона {template_path}: {str(e)}")
                        success = False
                        break
                
                # Если все шаблоны для текущей записи обработаны успешно
                if success and 'id' in row_data:
                    self.successful_ids.append(row_data['id'])
            
            # Отправляем список ID успешно обработанных записей
            self.processed_ids.emit(self.successful_ids)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(f"Общая ошибка: {str(e)}")

class TemplateSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор шаблонов")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Создаем область прокрутки
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Получаем список шаблонов
        templates_dir = Path("templates")
        self.templates = list(templates_dir.glob("*.docx"))
        
        # Добавляем чекбоксы
        self.checkboxes = []
        for template in self.templates:
            cb = QCheckBox(template.name)
            self.checkboxes.append((cb, template))
            scroll_layout.addWidget(cb)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Кнопка создания документов
        self.create_btn = QPushButton("Создать документы")
        self.create_btn.clicked.connect(self.create_documents)
        layout.addWidget(self.create_btn)
        
        self.selected_path = None
        self.generator_thread = None
        
    def create_documents(self):
        # Получаем выбранные шаблоны
        selected_templates = [str(template) for cb, template in self.checkboxes if cb.isChecked()]
        if not selected_templates:
            return
            
        # Запрашиваем папку для сохранения
        save_path = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if not save_path:
            return
            
        self.selected_path = save_path
        self.accept()
        
    def get_selected_data(self):
        if self.selected_path:
            selected_templates = [str(template) for cb, template in self.checkboxes if cb.isChecked()]
            return selected_templates, self.selected_path
        return None, None

def generate_documents(parent, data: List[Dict[str, Any]]):
    # Показываем диалог выбора шаблонов
    dialog = TemplateSelectionDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        templates, save_path = dialog.get_selected_data()
        if templates and save_path:
            # Создаем и запускаем поток
            progress_dialog = QProgressDialog("Генерация документов...", "Отмена", 0, 100, parent)
            progress_dialog.setWindowTitle("Прогресс")
            progress_dialog.setModal(True)
            
            generator_thread = DocumentGeneratorThread(templates, save_path, data)
            
            # Подключаем сигналы
            generator_thread.progress.connect(progress_dialog.setValue)
            generator_thread.finished.connect(progress_dialog.accept)
            generator_thread.error.connect(lambda msg: parent.show_error(msg))
            generator_thread.processed_ids.connect(parent.update_archive_status)
            
            # Запускаем генерацию
            generator_thread.start()
            progress_dialog.exec() 




"""
№ ТС BY А-BY.1739.14360ТАМОЖЕННЫЙ СОЮЗ
СВИДЕТЕЛЬСТВО О БЕЗОПАСНОСТИ КОНСТРУКЦИИ
ТРАНСПОРТНОГО СРЕДСТВА
ИСПЫТАТЕЛЬНАЯ ЛАБОРАТОРИЯ
Центр инновационных исследований Общества с ограниченной ответственностью "Центромаш"
юридический адрес: 220012, Республика Беларусь, г. Минск, ул. Платонова, 49, офис 411; фактический
адрес: 220113, Республика Беларусь, г. Минск, ул. Я. Коласа, 73/3, помещение 6; факс: +375 (17) 2430449;
тел.: +375 (17) 2430449; электронная почта: info@centromash.by; аттестат аккредитации BY/112 1.1739 от
06.12.2013 до 08.12.2028
МАРКА Купава
КОММЕРЧЕСКОЕ
НАИМЕНОВАНИЕ47KL00
ТИП 47KL00
ШАССИ QINGLING Q3
ИДЕНТИФИКАЦИОН
НЫЙ НОМЕР (VIN)Y3H47KL00S0085913
ГОД ВЫПУСКА 2025 г.
КАТЕГОРИЯ N2
ЭКОЛОГИЧЕСКИЙ
КЛАССшестой
ЗАЯВИТЕЛЬ И ЕГО
АДРЕСОбщество с ограниченной ответственностью «Завод
автомобильных прицепов и кузовов «МАЗ-Купава» (ООО
«Завод автомобильных прицепов и кузовов «МАЗ-Купава»),
ОГРН: 190032958, юридический адрес: 220118, Республика
Беларусь, гор. Минск, ул. Машиностроителей, д. 18,
фактический адрес: 220118, Республика Беларусь, гор. Минск,
ул. Машиностроителей, д. 18, телефон/факс: +375173963751,
+375172913024, электронная почта: kupava@kupava.byТРАНСПОРТНОЕ СРЕДСТВОМ.П.Стр.2
ТС BY А-BY.1739.14360Свидетельство о безопасности
конструкции транспортного средства №
ИЗГОТОВИТЕЛЬ И
ЕГО АДРЕСОбщество с ограниченной ответственностью «Завод
автомобильных прицепов и кузовов «МАЗ-Купава» (ООО
«Завод автомобильных прицепов и кузовов «МАЗ-Купава»),
ОГРН: 190032958, юридический адрес: 220118, Республика
Беларусь, гор. Минск, ул. Машиностроителей, д. 18,
фактический адрес: 220118, Республика Беларусь, гор. Минск,
ул. Машиностроителей, д. 18
СБОРОЧНЫЙ ЗАВОД
И ЕГО АДРЕСОбщество с ограниченной ответственностью «Завод
автомобильных прицепов и кузовов «МАЗ-Купава» (ООО
«Завод автомобильных прицепов и кузовов «МАЗ-Купава»),
ОГРН: 190032958, юридический адрес: 220118, Республика
Беларусь, гор. Минск, ул. Машиностроителей, д. 18,
фактический адрес: 220118, Республика Беларусь, гор. Минск,
ул. Машиностроителей, д. 18
Колесная
формула/ведущие
колеса4x2/задние
Схема компоновки
транспортного
средствакабина над двигателем
Исполнение
загрузочного
пространстваизотермический фургон «Купава», рефрижератор
Кабина цельнометаллическая, двухдверная, трехместная,
откидывающаяся вперед, однорядная
Масса транспортного
средства в
снаряженном
состоянии, кг5700
Технически
допустимая
максимальная масса
транспортного
средства, кг11995
Габаритные размеры,
мм
- длина 8270
- ширина 2600
- высота 3290
База, мм 4425
Колея передних/задних
колес, мм1680/1650ОБЩИЕ ХАРАКТЕРИСТИКИ ТРАНСПОРТНОГО СРЕДСТВАМ.П.Стр.3
ТС BY А-BY.1739.14360Свидетельство о безопасности
конструкции транспортного средства №
Двигатель внутреннего
сгорания (марка, тип)ISUZU, 4HK1-TCG61, четырехтактный, четырехцилиндровый с
водяным охлаждением, наддувом и промежуточным
охлаждением, с воспламенением от сжатия
- количество и
расположение
цилиндров4, рядное
- рабочий объем
цилиндров, см³5193
- степень сжатия 17.5
- максимальная
мощность, кВт (мин-1)138 (2600)
Топливо Дизельное топливо
Система питания (тип) непосредственное впрыскивание топлива с общей рампой
Система выпуска и
нейтрализации
отработавших газоводин глушитель с нейтрализатором и фильтром твердых
частиц, с системой рециркуляции отработавших газов,
функцию глушителя выполняет нейтрализатор
(DOC+DPF+SCR+ASC(4))
Трансмиссия механическая, с ручным управлением
Сцепление (марка, тип) сухое, однодисковое
Коробка передач
(марка, тип)механическая, с ручным управлением
Подвеска (тип)
Передняя зависимая, рессорная, с гидравлическими телескопическими
амортизаторами, без стабилизатора поперечной устойчивости
Задняя зависимая, рессорная, с гидравлическими телескопическими
амортизаторами, без стабилизатора поперечной устойчивости
Рулевое управление
(марка, тип)рулевой привод с гидроусилителем, «винт – шариковая гайка –
рейка – сектор»
Тормозные системы
(тип)
- рабочая пневматическая, двухконтурный привод с разделением на
переднюю ось и задний мост, с АБС, тормозные механизмы
всех колес – барабанные
- запасная каждый контур рабочей тормозной системы
- стояночная привод от пружинных энергоаккумуляторов к тормозным
механизмам колес заднего моста
- вспомогательная
(износостойкая)газодинамическая, установлена в системе выпуска
отработавших газов
Шины 8.25R20
Оборудование
транспортного
средствахолодильно-отопительная установка
номер УВЭОС 8970177000113013208М.П.Стр.4
ТС BY А-BY.1739.14360Свидетельство о безопасности
конструкции транспортного средства №
соответствуют требованиям технического регламента Таможенного союза "О безопасности колесных
транспортных средств".
Пригодно для использования на всей сети дорог общего пользования без ограничений.
Идентификационный номер (VIN) шасси: LWLDAANK2RL004546
Транспортное средство изготовлено на базовом транспортном средстве (шасси) модификации
QL1120AJMAY
ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ
Дата оформления "24" января 2025 г.
Руководитель испытательной лабораторииО. Н. Смирнов
инициалы, фамилия
"""

"""
ОБЩИЕ ХАРАКТЕРИСТИКИ ТРАНСПОРТНОГО СРЕДСТВАМ.П.Стр.3
ТС BY А-BY.1739.14360Свидетельство о безопасности
конструкции транспортного средства №
"""
"""
М.П.Стр.4
ТС BY А-BY.1739.14360Свидетельство о безопасности
конструкции транспортного средства №
"""
"""
ТРАНСПОРТНОЕ СРЕДСТВОМ.П.Стр.2
ТС BY А-BY.1739.14360Свидетельство о безопасности
конструкции транспортного средства №
"""
"""
М.П.Стр.4
ТС BY А-BY.1739.14360Свидетельство о безопасности
конструкции транспортного средства №
"""