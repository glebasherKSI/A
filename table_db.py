import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableView, QVBoxLayout, QWidget, 
                            QMessageBox, QDialog, QLineEdit, QPushButton, QMenu, QCheckBox,
                            QScrollArea, QVBoxLayout, QPlainTextEdit, QHBoxLayout, QFrame, QWidgetAction,
                            QLabel, QStyledItemDelegate)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QEvent
from PyQt6.QtGui import QAction, QColor, QCursor, QPainter, QPalette
import sqlite3
from PyQt6.QtWidgets import QToolTip
from PyQt6.QtCore import QTimer
from sql_to_myaql import DataSync
from typing import List, Any, Dict
from document_generator import generate_documents
from PyQt6.QtWidgets import QComboBox
from db_thread import DBWorker, SyncWorker

class Database:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.connection = sqlite3.connect('vehicles.db')
            self.cursor = self.connection.cursor()
        except Exception as e:
            print(f"Ошибка подключения к БД: {e}")
            raise

    def close(self):
        if self.connection:
            self.connection.close()

    def execute(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка выполнения запроса: {e}")
            return False

    def fetch_all(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения данных: {e}")
            return []

class TableModel(QAbstractTableModel):
    def __init__(self, data=None, headers=None):
        super().__init__()
        self._data = data or []
        self._headers = headers or []
        self._original_data = data.copy() if data else []
        self._column_types = {}
        self._filtered_columns = set()
        
    def set_column_types(self, types):
        self._column_types = types
        
    def set_column_filtered(self, column, is_filtered):
        if is_filtered:
            self._filtered_columns.add(column)
        else:
            self._filtered_columns.discard(column)
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, column, column)
        
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole and section < len(self._headers):
                # Добавляем индикатор фильтра (точку) к заголовку
                if section in self._filtered_columns:
                    return f"● {self._headers[section]}"
                return self._headers[section]
            elif role == Qt.ItemDataRole.BackgroundRole:
                if section in self._filtered_columns:
                    return QColor("#7B5AF4")  # Фиолетовый цвет для отфильтрованных колонок
                return QColor("#24273A")  # Стандартный цвет для остальных
            elif role == Qt.ItemDataRole.ForegroundRole:
                return QColor("white")  # Белый цвет текста для всех заголовков
        return None

    def rowCount(self, parent):
        return len(self._data)

    def columnCount(self, parent):
        return len(self._headers)

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._data[index.row()][index.column()])
        return None

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            self._data[index.row()][index.column()] = value
            return True
        return False

    def removeRow(self, row):
        self.beginRemoveRows(self.index(row, 0).parent(), row, row)
        del self._data[row]
        self.endRemoveRows()
        return True

class FilterDialog(QDialog):
    def __init__(self, values, current_selected=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Фильтр")
        self.setModal(True)
        self.resize(300, 400)
        
        layout = QVBoxLayout(self)
        
        # Создаем область прокрутки
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Добавляем чекбоксы
        self.checkboxes = []
        for value in sorted(set(values)):
            if value:
                cb = QCheckBox(str(value))
                # Устанавливаем состояние на основе текущего фильтра
                if current_selected:
                    cb.setChecked(str(value) in current_selected)
        else:
                cb.setChecked(False)
                self.checkboxes.append(cb)
                scroll_layout.addWidget(cb)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Кнопки
        btn_layout = QVBoxLayout()
        
        # Кнопки Выделить все/Снять выделение
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выделить все")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("Снять выделение")
        deselect_all_btn.clicked.connect(self.deselect_all)
        
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(deselect_all_btn)
        btn_layout.addLayout(select_layout)
        
        # Кнопка применить
        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
        
        # Применяем стили
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1B26;
            }
            QScrollArea {
                border: none;
                background-color: #1A1B26;
            }
            QCheckBox {
                color: white;
                padding: 5px;
            }
            QCheckBox:hover {
                background-color: #2F3242;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #7B5AF4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #8D6FF5;
            }
        """)
        
    def select_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)
            
    def deselect_all(self):
        for cb in self.checkboxes:
            cb.setChecked(False)
    
    def get_selected_values(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

class EditDialog(QDialog):
    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Заменяем \n на буквальный текст '\n' для отображения
        display_value = str(value).replace('\n', '\\n')
        
        self.edit = QPlainTextEdit()
        self.edit.setPlainText(display_value)
        self.edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2F3242;
                color: white;
                border: 1px solid #3D4258;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                min-height: 200px;
                line-height: 1.5;
                font-family: Consolas, monospace;
            }
            QPlainTextEdit:focus {
                border: 1px solid #7B5AF4;
            }
        """)
        layout.addWidget(self.edit)
        
        btn = QPushButton("Сохранить")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #7B5AF4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #8D6FF5;
            }
        """)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        
    def get_value(self):
        # Заменяем текстовые '\n' обратно на реальные переносы строк
        text = self.edit.toPlainText()
        return text.replace('\\n', '\n')

class CustomProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = {}

    def set_filter(self, column, values):
        if values:
            self.filters[column] = values
        else:
            self.filters.pop(column, None)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        for column, values in self.filters.items():
            value = str(self.sourceModel().data(self.sourceModel().index(source_row, column), Qt.ItemDataRole.DisplayRole))
            if value not in values:
                return False
        return True

class CustomTooltip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Устанавливаем флаги окна для тултипа
        self.setWindowFlags(
            Qt.WindowType.ToolTip |  # Делаем окно тултипом
            Qt.WindowType.FramelessWindowHint |  # Убираем рамку
            Qt.WindowType.WindowStaysOnTopHint  # Держим поверх других окон
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Делаем фон прозрачным
        
        # Создаем контейнер для контента
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: #24273A;
                border: 1px solid #6E738D;
                border-radius: 4px;
            }
        """)
        
        # Создаем layout для контейнера
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # Создаем метку для текста
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
            }
        """)
        self.layout.addWidget(self.label)
        
        # Создаем layout для основного виджета
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        
        self.hide()

    def showTooltip(self, text, pos):
        self.label.setText(text)
        self.container.adjustSize()
        self.adjustSize()
        # Корректируем позицию, чтобы подсказка не выходила за пределы экрана
        screen = QApplication.primaryScreen().geometry()
        if pos.x() + self.width() > screen.width():
            pos.setX(screen.width() - self.width())
        if pos.y() + self.height() > screen.height():
            pos.setY(screen.height() - self.height())
        self.move(pos)
        self.show()
        self.raise_()

class EmptyCellDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        value = index.data(Qt.ItemDataRole.DisplayRole)
        if value is None or str(value).strip() == '':
            # Сохраняем оригинальный цвет фона
            original_color = option.palette.base().color()
            # Создаем новый цвет с желтым оттенком
            yellow_color = QColor(255, 255, 0, 30)
            # Смешиваем цвета с учетом прозрачности
            mixed_color = QColor(
                int(original_color.red() * 0.85 + yellow_color.red() * 0.15),
                int(original_color.green() * 0.85 + yellow_color.green() * 0.15),
                int(original_color.blue() * 0.85 + yellow_color.blue() * 0.15)
            )
            # Создаем новую палитру
            palette = option.palette
            palette.setColor(QPalette.ColorRole.Base, mixed_color)
            option.palette = palette
            
            # Рисуем фон
            painter.fillRect(option.rect, mixed_color)
            
            # Рисуем текст
            if value is not None:
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, str(value))
        else:
            super().paint(painter, option, index)

class TableWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Просмотр данных")
        self.resize(1200, 800)
        
        # Словарь для хранения всех уникальных значений по колонкам
        self.column_values = {}
        # Словарь для хранения текущих фильтров
        self.current_filters = {}
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Создаем таблицу
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Устанавливаем делегат для подсветки пустых ячеек
        self.empty_cell_delegate = EmptyCellDelegate(self.table)
        self.table.setItemDelegate(self.empty_cell_delegate)
        # Создаем кнопку синхронизации
        sync_button = QPushButton("Синхронизировать")
        sync_button.setStyleSheet("""
        
            QPushButton {
                background-color: #363A4F;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #494D64;
            }
            QPushButton:pressed {
                background-color: #7B5AF4;
            }
        """)
        sync_button.clicked.connect(self.sync_database)
        
        # Добавляем кнопку в layout перед таблицей
        layout.addWidget(sync_button)
        layout.addWidget(self.table)
        # Устанавливаем фиксированную ширину для всех колонок
        self.table.horizontalHeader().setDefaultSectionSize(150)
        
        # Настройка внешнего вида таблицы
        self.table.setStyleSheet("""
            QTableView {
                background-color: #1A1B26;
                color: white;
                gridline-color: #2F3242;
                border: none;
                selection-background-color: #7B5AF4;
                selection-color: white;
            }
            QTableView::item {
                padding: 5px;
                border: none;
            }
            QTableView::item:selected {
                background-color: #7B5AF4;
            }
            QHeaderView::section {
                background-color: #24273A;
                color: white;
                padding: 5px;
                border: none;
                border-right: 1px solid #2F3242;
                border-bottom: 1px solid #2F3242;
            }
            QHeaderView::section:hover {
                background-color: #2F3242;
            }
            QScrollBar:vertical {
                background-color: #1A1B26;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #2F3242;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #3F4252;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #1A1B26;
                height: 14px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #2F3242;
                min-width: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #3F4252;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # Устанавливаем контекстное меню для заголовков
        self.table.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self.show_filter_menu)
        
        # Настройка заголовков
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)
        
        # Загружаем данные
        self.load_data()
        
        # Устанавливаем цвет фона окна
        self.setStyleSheet("QMainWindow { background-color: #1A1B26; }")
        
        # Настройка для подсказок
        self.table.setMouseTracking(True)  # Включаем отслеживание движения мыши
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.setInterval(300)  # 300 мс задержка перед показом
        self.tooltip_timer.timeout.connect(self.show_tooltip)
        
        # Создаем кастомную подсказку
        self.tooltip = CustomTooltip()
        
        self.current_cell = None
        self.current_pos = None
        self.last_cell = None
        self._tooltip_shown = False
        
        # Устанавливаем фильтр событий для viewport таблицы и приложения
        self.table.viewport().installEventFilter(self)
        QApplication.instance().installEventFilter(self)

    def load_data(self):
        try:
            db = Database()
            # Получаем заголовки и типы данных
            db.cursor.execute("PRAGMA table_info(vehicles)")
            columns_info = db.cursor.fetchall()
            headers = []
            column_types = {}
            
            for i, col in enumerate(columns_info):
                name = col[1]
                col_type = col[2].upper()
                headers.append(name)
                column_types[i] = col_type
            
            # Получаем данные
            rows = db.fetch_all("SELECT * FROM vehicles")
            if rows:
                # Преобразуем в список списков для редактирования
                data = [list(row) for row in rows]
                
                # Собираем уникальные значения для каждой колонки
                for col_idx, header in enumerate(headers):
                    self.column_values[col_idx] = sorted(set(str(row[col_idx]) for row in data if row[col_idx] is not None))
                
                # Создаем модель
                self.model = TableModel(data, headers)
                self.model.set_column_types(column_types)
                
                # Создаем кастомную прокси-модель
                self.proxy_model = CustomProxyModel(self)
                self.proxy_model.setSourceModel(self.model)
                self.table.setModel(self.proxy_model)
                
                # Устанавливаем размеры столбцов
                for column in range(len(headers)):
                    # Получаем максимальную ширину содержимого в столбце
                    max_width = len(headers[column]) * 10  # Базовая ширина от заголовка
                    for row in range(len(data)):
                        content_width = len(str(data[row][column])) * 8
                        max_width = max(max_width, content_width)
                    # Устанавливаем минимальную ширину 150 пикселей
                    self.table.setColumnWidth(column, max(150, min(max_width, 300)))
                
                # Разрешаем сортировку
                self.table.setSortingEnabled(True)
                
            db.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {str(e)}")
    def sync_database(self):
        try:
            # Создаем и запускаем поток для синхронизации
            self.sync_worker = SyncWorker()
            self.sync_worker.finished.connect(self.on_sync_finished)
            self.sync_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка синхронизации: {str(e)}")
            
    def on_sync_finished(self, success: bool, message: str):
        if success:
            QMessageBox.information(self, "Успех", message)
            self.load_data()
        else:
            QMessageBox.critical(self, "Ошибка", message)
    def show_context_menu(self, pos):
        # Получаем индекс ячейки под курсором
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #24273A;
                color: white;
                border: 1px solid #6E738D;
            }
            QMenu::item {
                padding: 5px 10px;
            }
            QMenu::item:selected {
                background-color: #494D64;
            }
        """)

        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(lambda: self.edit_selected(index))
        menu.addAction(edit_action)
        
        copy_action = QAction("Копировать", self)
        copy_action.triggered.connect(self.copy_selected)
        menu.addAction(copy_action)
        
        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(self.delete_selected)
        menu.addAction(delete_action)

        # Добавляем пункт создания документов
        if self.table.selectedIndexes():
            create_docs_action = QAction("Создать документы", self)
            create_docs_action.triggered.connect(self.create_documents)
            menu.addAction(create_docs_action)
        # Добавляем пункт отправки на редактирование
        if self.table.selectedIndexes():
            send_to_edit_action = QAction("Отправить на редактирование", self)
            send_to_edit_action.triggered.connect(self.send_to_edit)
            menu.addAction(send_to_edit_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def send_to_edit(self):
        try:
            # Создаем диалог выбора пользователя
            dialog = QDialog(self)
            dialog.setWindowTitle("Выбор пользователя")
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #24273A;
                    color: white;
                }
                QComboBox {
                    background-color: #363A4F;
                    color: white;
                    border: 1px solid #6E738D;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #363A4F;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    margin: 5px;
                }
                QPushButton:hover {
                    background-color: #494D64;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Создаем выпадающий список пользователей
            user_combo = QComboBox()
            layout.addWidget(user_combo)
            
            # Кнопки подтверждения/отмены  
            buttons_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Отмена")
            
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            buttons_layout.addWidget(ok_button)
            buttons_layout.addWidget(cancel_button)
            layout.addLayout(buttons_layout)

            # Создаем отдельный поток для работы с БД
            

            # Создаем и запускаем поток для загрузки пользователей
            def on_users_loaded(users):
                for user in users:
                    user_combo.addItem(user['username'], user['user_id'])
                    
            worker = DBWorker()
            worker.users_loaded.connect(on_users_loaded)
            worker.finished.connect(lambda success, msg: 
                QMessageBox.critical(self, "Ошибка", msg) if not success else None)
            worker.start()

            # Показываем диалог
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_user_id = user_combo.currentData()
                
                # Получаем выделенные строки через прокси-модель
                proxy_model = self.table.model()
                source_model = proxy_model.sourceModel()
                
                selected_rows = set()
                selected_data = []
                
                for index in self.table.selectedIndexes():
                    source_index = proxy_model.mapToSource(index)
                    selected_rows.add(source_index.row())
                
                for row in selected_rows:
                    row_data = {}
                    for col in range(source_model.columnCount(None)):
                        header = source_model._headers[col]
                        value = source_model._data[row][col]
                        row_data[header] = value
                    selected_data.append(row_data)
                
                if not selected_data:
                    QMessageBox.critical(self, "Ошибка", "Не выбраны данные для отправки")
                    return

                # Создаем и запускаем поток для отправки данных
                worker = DBWorker(selected_data, selected_user_id)
                worker.finished.connect(lambda success, msg:
                    QMessageBox.information(self, "Успех", msg) if success 
                    else QMessageBox.critical(self, "Ошибка", msg))
                worker.start()
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")
        

    def show_filter_menu(self, pos):
        header = self.table.horizontalHeader()
        column = header.logicalIndexAt(pos)
        
        if column < 0:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #24273A;
                color: white;
                border: 1px solid #6E738D;
            }
            QMenu::item:selected {
                background-color: #494D64;
            }
            QPushButton {
                background-color: #363A4F;
                color: white;
                border: none;
                padding: 5px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #494D64;
            }
            QCheckBox {
                color: white;
            }
        """)

        # Создаем виджет для размещения элементов
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Кнопки выбора
        select_buttons = QHBoxLayout()
        select_all = QPushButton("Выделить все")
        deselect_all = QPushButton("Снять выделение")
        select_buttons.addWidget(select_all)
        select_buttons.addWidget(deselect_all)
        layout.addLayout(select_buttons)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #6E738D;")
        layout.addWidget(line)
        
        # Получаем уникальные значения для колонки
        unique_values = set()
        from PyQt6.QtCore import QModelIndex
        for row in range(self.proxy_model.rowCount(QModelIndex())):
            source_index = self.proxy_model.mapToSource(self.proxy_model.index(row, column))
            value = str(self.model.data(source_index, Qt.ItemDataRole.DisplayRole))
            unique_values.add(value)
        
        # Создаем чекбоксы
        checkboxes = []
        for value in sorted(unique_values):
            checkbox = QCheckBox(value)
            if column in self.current_filters and value in self.current_filters[column]:
                checkbox.setChecked(True)
            checkboxes.append(checkbox)
            layout.addWidget(checkbox)
            
        # Кнопки применения
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Применить")
        clear_button = QPushButton("Очистить фильтр")
        button_layout.addWidget(apply_button)
        button_layout.addWidget(clear_button)
        layout.addLayout(button_layout)
        
        # Создаем действие для виджета
        action = QWidgetAction(menu)
        action.setDefaultWidget(container)
        menu.addAction(action)
        
        # Обработчики кнопок
        def select_all_clicked():
            for cb in checkboxes:
                cb.setChecked(True)
                
        def deselect_all_clicked():
            for cb in checkboxes:
                cb.setChecked(False)
                
        def apply_filter():
            selected_values = {cb.text() for cb in checkboxes if cb.isChecked()}
            if selected_values:
                self.current_filters[column] = selected_values
                self.model.set_column_filtered(column, True)
            else:
                self.current_filters.pop(column, None)
                self.model.set_column_filtered(column, False)
            self.apply_filters()
            menu.close()
            
        def clear_filter():
            self.current_filters.pop(column, None)
            self.model.set_column_filtered(column, False)
            self.proxy_model.set_filter(column, None)
            self.proxy_model.invalidateFilter()
            menu.close()
        
        select_all.clicked.connect(select_all_clicked)
        deselect_all.clicked.connect(deselect_all_clicked)
        apply_button.clicked.connect(apply_filter)
        clear_button.clicked.connect(clear_filter)
        
        menu.exec(header.mapToGlobal(pos))

    

    def apply_filters(self):
        for column, values in self.current_filters.items():
            self.proxy_model.set_filter(column, values)
            self.model.set_column_filtered(column, bool(values))
        
        # Если в колонке нет выбранных значений, очищаем фильтр для этой колонки
        for column in range(self.model.columnCount(None)):
            if column not in self.current_filters:
                self.proxy_model.set_filter(column, None)
                self.model.set_column_filtered(column, False)
        
        self.proxy_model.invalidateFilter()

    def clear_filter(self, column):
        if column in self.current_filters:
            del self.current_filters[column]
            self.model.set_column_filtered(column, False)
            self.proxy_model.set_filter(column, None)
            self.proxy_model.invalidateFilter()

    def update_archive_status(self, processed_ids: List[int]):
        """Обновляет статус архивации для обработанных записей"""
        if not processed_ids:
            return
            
        try:
            db = Database()
            
            # Начинаем транзакцию
            db.execute("BEGIN TRANSACTION")
            success_count = 0
            
            # Обновляем каждую запись
            for row_id in processed_ids:
                if db.execute("UPDATE vehicles SET in_archive = 1 WHERE id = ?", (row_id,)):
                    success_count += 1
                    
                    # Обновляем значение в модели
                    for row in range(self.model.rowCount(None)):
                        if self.model._data[row][0] == row_id:  # ID всегда в первой колонке
                            # Находим индекс колонки in_archive
                            archive_col = self.model._headers.index('in_archive')
                            self.model._data[row][archive_col] = 1
                            break
            
            # Если были успешные обновления, коммитим транзакцию
            if success_count > 0:
                db.execute("COMMIT")
                # Уведомляем модель об изменении данных
                self.model.layoutChanged.emit()
                QMessageBox.information(self, "Результат", 
                                     f"Документы созданы успешно.\nОбновлено записей: {success_count}")
            else:
                db.execute("ROLLBACK")
                QMessageBox.warning(self, "Предупреждение", 
                                  "Не удалось обновить статус архивации")
                
        except Exception as e:
            if 'db' in locals():
                db.execute("ROLLBACK")
            QMessageBox.critical(self, "Ошибка", 
                               f"Ошибка при обновлении статуса архивации: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()

    def create_documents(self):
        # Получаем выбранные строки
        selected_rows = set()
        for index in self.table.selectedIndexes():
            selected_rows.add(index.row())
            
        if not selected_rows:
            return

        # Собираем данные для выбранных строк
        data = []
        for row in selected_rows:
            row_data = {}
            source_row = self.proxy_model.mapToSource(self.proxy_model.index(row, 0)).row()
            
            # Собираем данные из всех колонок
            for col in range(self.model.columnCount(None)):
                header = self.model._headers[col]
                value = self.model._data[source_row][col]
                
                # Разбираем сложные поля (если они в JSON формате)
                if header in ['DVIGATEL', 'TOPLIVO', 'TRANSMISSIYA', 'PODVESKA', 'TORMOZNAYA_SISTEMA', 'GABARITY', 'BAZOVOE_TS', 'SBKTS']:
                    try:
                        if isinstance(value, str):
                            import json
                            value = json.loads(value)
                    except:
                        pass
                        
                row_data[header] = value
                
            data.append(row_data)
            
        # Запускаем генерацию документов
        generate_documents(self, data)

    def show_error(self, message: str):
        QMessageBox.critical(self, "Ошибка", message)

    def edit_selected(self, clicked_index=None):
        if not clicked_index:
            return

        # Получаем все выделенные индексы
        selected_indexes = self.table.selectedIndexes()
        if not selected_indexes:
            return

        # Определяем столбец для редактирования из кликнутой ячейки
        clicked_column = clicked_index.column()
        
        # Фильтруем только индексы из нужного столбца
        column_indexes = [idx for idx in selected_indexes if idx.column() == clicked_column]
        if not column_indexes:
            return

        # Получаем текущее значение из кликнутой ячейки
        source_index = self.proxy_model.mapToSource(clicked_index)
        current_value = self.model.data(source_index, Qt.ItemDataRole.DisplayRole)
        
        # Показываем диалог редактирования
        dialog = EditDialog(current_value, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_value = dialog.get_value()
            
            try:
                db = Database()
                column_name = self.model._headers[clicked_column]
                column_type = self.model._column_types.get(clicked_column, 'TEXT')
                
                # Конвертируем значение в правильный тип
                try:
                    if column_type == 'INTEGER':
                        converted_value = int(new_value) if new_value else None
                    elif column_type == 'REAL':
                        converted_value = float(new_value) if new_value else None
                    elif column_type == 'BOOLEAN':
                        converted_value = bool(int(new_value)) if new_value else False
                    else:
                        converted_value = new_value
                except ValueError:
                    QMessageBox.warning(self, "Предупреждение", 
                                     f"Неверный формат данных. Ожидается {column_type}")
                    return
                
                # Защищаем имя колонки от SQL инъекций
                safe_column_name = f"`{column_name}`"
                
                # Начинаем транзакцию
                db.execute("BEGIN TRANSACTION")
                success_count = 0
                error_count = 0
                
                try:
                    # Обновляем каждую выбранную ячейку
                    for proxy_idx in column_indexes:
                        source_idx = self.proxy_model.mapToSource(proxy_idx)
                        row_id = self.model._data[source_idx.row()][0]  # ID всегда в первой колонке
                        
                        # Обновляем значение в БД
                        query = f"UPDATE vehicles SET {safe_column_name} = ? WHERE id = ?"
                        if db.execute(query, (converted_value, row_id)):
                            # Обновляем значение в модели
                            self.model.setData(source_idx, converted_value, Qt.ItemDataRole.EditRole)
                            success_count += 1
                        else:
                            error_count += 1
                    
                    # Если были успешные обновления, коммитим транзакцию
                    if success_count > 0:
                        db.execute("COMMIT")
                        # Уведомляем модель об изменении данных
                        self.model.dataChanged.emit(
                            self.model.index(0, clicked_column),
                            self.model.index(self.model.rowCount(None)-1, clicked_column)
                        )
                        
                        msg = f"Обновлено успешно: {success_count}"
                        if error_count > 0:
                            msg += f"\nОшибок: {error_count}"
                        QMessageBox.information(self, "Результат", msg)
                    else:
                        db.execute("ROLLBACK")
                        QMessageBox.warning(self, "Предупреждение", "Не удалось обновить данные")
                        
                except Exception as e:
                    db.execute("ROLLBACK")
                    raise e
                    
                finally:
                    db.close()
                    
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка обновления данных: {str(e)}")
                print(f"Ошибка при обновлении: {str(e)}")

    def copy_selected(self):
        indexes = self.table.selectedIndexes()
        if not indexes:
            return

        # Собираем текст для копирования
        text = []
        current_row = indexes[0].row()
        row_text = []
        
        for index in sorted(indexes):
            if index.row() != current_row:
                text.append("\t".join(row_text))
                row_text = []
                current_row = index.row()
            row_text.append(str(self.proxy_model.data(index, Qt.ItemDataRole.DisplayRole)))
        text.append("\t".join(row_text))
        
        QApplication.clipboard().setText("\n".join(text))

    def delete_selected(self):
        indexes = self.table.selectedIndexes()
        if not indexes:
            return

        # Получаем уникальные строки
        rows = set()
        for index in indexes:
            rows.add(index.row())
            
        if QMessageBox.question(self, "Подтверждение", 
                              f"Удалить выбранные записи ({len(rows)})?",
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
            return

        try:
            db = Database()
            
            # Начинаем транзакцию
            db.execute("BEGIN TRANSACTION")
            success_count = 0
            
            # Удаляем записи
            for row in sorted(rows, reverse=True):
                source_row = self.proxy_model.mapToSource(self.proxy_model.index(row, 0)).row()
                row_id = self.model._data[source_row][0]  # ID всегда в первой колонке
                
                if db.execute("DELETE FROM vehicles WHERE id = ?", (row_id,)):
                    self.model.removeRow(source_row)
                    success_count += 1
            
            # Если были успешные удаления, коммитим транзакцию
            if success_count > 0:
                db.execute("COMMIT")
                QMessageBox.information(self, "Результат", f"Удалено записей: {success_count}")
            else:
                db.execute("ROLLBACK")
                QMessageBox.warning(self, "Предупреждение", "Не удалось удалить записи")
            
            db.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка удаления данных: {str(e)}")
            if 'db' in locals():
                db.execute("ROLLBACK")
                db.close()

    def show_tooltip(self):
        """Показывает подсказку для текущей ячейки"""
        if self.current_cell and self.current_cell.isValid():
            # Получаем значение ячейки
            value = self.proxy_model.data(self.current_cell, Qt.ItemDataRole.DisplayRole)
            if value:
                text = str(value)
                
                # Получаем ширину текста и ячейки
                rect = self.table.visualRect(self.current_cell)
                fm = self.table.fontMetrics()
                text_width = fm.horizontalAdvance(text)
                
                # Если текст не помещается, показываем подсказку
                if text_width > rect.width() - 10:  # Немного отступа
                    # Получаем заголовок колонки для контекста
                    header = self.model._headers[self.current_cell.column()]
                    tooltip = f"{header}:\n{text}"
                    
                    # Получаем глобальную позицию курсора
                    cursor_pos = QCursor.pos()
                    # Смещаем позицию немного вниз и вправо от курсора
                    cursor_pos.setX(cursor_pos.x() + 10)
                    cursor_pos.setY(cursor_pos.y() + 10)
                    
                    # Показываем кастомную подсказку
                    self.tooltip.showTooltip(tooltip, cursor_pos)
                    self._tooltip_shown = True

    def eventFilter(self, obj, event):
        if obj == self.table.viewport():
            if event.type() == QEvent.Type.MouseMove:
                # Получаем индекс ячейки под курсором
                index = self.table.indexAt(event.pos())
                if index.isValid():
                    # Если переместились на новую ячейку
                    if self.last_cell != index:
                        # Скрываем подсказку при переходе на другую ячейку
                        self.tooltip.hide()
                        # Запоминаем текущую ячейку как последнюю
                        self.last_cell = index
                        # Сохраняем текущую ячейку и позицию
                        self.current_cell = index
                        self.current_pos = QCursor.pos()  # Используем глобальную позицию курсора
                        # Запускаем таймер для показа подсказки с задержкой
                        self.tooltip_timer.start()
                    else:
                        # Обновляем только позицию
                        self.current_pos = QCursor.pos()
                        # Обновляем позицию подсказки если она показана
                        if self._tooltip_shown:
                            self.tooltip.move(self.current_pos)
                else:
                    # Курсор не над ячейкой
                    self.last_cell = None
                    self._tooltip_shown = False
                    # Скрываем подсказку и останавливаем таймер
                    self.tooltip.hide()
                    self.tooltip_timer.stop()
            
            # Скрываем подсказку при уходе с viewport
            elif event.type() == QEvent.Type.Leave:
                self.last_cell = None
                self._tooltip_shown = False
                self.tooltip.hide()
                self.tooltip_timer.stop()
                
        return super().eventFilter(obj, event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TableWindow()
    window.show()
    sys.exit(app.exec())
