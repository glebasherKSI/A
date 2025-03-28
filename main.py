import sys
import os
import math
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRectF, QPointF, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QBrush
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QFrame, QFileDialog, QGraphicsView, QGraphicsScene, QGridLayout, QLineEdit, QMessageBox,
    QProgressBar, QTextEdit, QSizePolicy, QSpacerItem, QScrollArea
)
from PyPDF2 import PdfReader
import re
from pdf_thread import PDFProcessThread
from table_db import TableWindow

from database import Database


class SideGrip(QtWidgets.QWidget):
    def __init__(self, parent, edge):
        QtWidgets.QWidget.__init__(self, parent)
        self.edge = edge
        if edge in [Qt.Edge.LeftEdge, Qt.Edge.RightEdge]:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.setFixedWidth(10)  # Увеличиваем область захвата
            self.setStyleSheet("background: transparent;")
        else:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            self.setFixedHeight(10)  # Увеличиваем область захвата
            self.setStyleSheet("background: transparent;")
        
        self.mousePos = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePos = event.globalPosition().toPoint()
            self.windowPos = self.window().pos()
            self.windowSize = self.window().size()
            
    def mouseMoveEvent(self, event):
        if self.mousePos is None:
            return
            
        delta = event.globalPosition().toPoint() - self.mousePos
        window = self.window()
        
        if self.edge == Qt.Edge.LeftEdge:
            newX = self.windowPos.x() + delta.x()
            newWidth = self.windowSize.width() - delta.x()
            if newWidth >= window.minimumWidth():
                window.setGeometry(newX, window.y(), newWidth, window.height())
        elif self.edge == Qt.Edge.RightEdge:
            newWidth = self.windowSize.width() + delta.x()
            if newWidth >= window.minimumWidth():
                window.resize(newWidth, window.height())
        elif self.edge == Qt.Edge.TopEdge:
            newY = self.windowPos.y() + delta.y()
            newHeight = self.windowSize.height() - delta.y()
            if newHeight >= window.minimumHeight():
                window.setGeometry(window.x(), newY, window.width(), newHeight)
        elif self.edge == Qt.Edge.BottomEdge:
            newHeight = self.windowSize.height() + delta.y()
            if newHeight >= window.minimumHeight():
                window.resize(window.width(), newHeight)
        
    def mouseReleaseEvent(self, event):
        self.mousePos = None
        self.windowPos = None
        self.windowSize = None
        
class MainWindow(QtWidgets.QMainWindow):
    _SIDE_GRIP_SIZE = 5
    
    def __init__(self):
        super().__init__()
        
        # Убираем стандартную рамку окна
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(600, 400)  # Уменьшаем минимальный размер окна
        # Устанавливаем начальный размер окна
        self.resize(1200, 1000)
        # Инициализируем пути к файлам
        self.excel1_path = None
        self.excel2_path = None
        
        # Создаем центральный виджет с фоном
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        central_widget.setStyleSheet("""
            QWidget#centralWidget {
                background-color: #1A1B26;
                border: 1px solid #2F3242;
                border-radius: 15px;
            }
        """)
        self.setCentralWidget(central_widget)
        
        # Добавляем рамки для изменения размера
        self.left_grip = SideGrip(self, Qt.Edge.LeftEdge)
        self.right_grip = SideGrip(self, Qt.Edge.RightEdge)
        self.top_grip = SideGrip(self, Qt.Edge.TopEdge)
        self.bottom_grip = SideGrip(self, Qt.Edge.BottomEdge)
        
        # Основной вертикальный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Создаем заголовок окна
        self.setup_title_bar()
        main_layout.addWidget(self.titleBar)
        
        # Создаем контент
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Создаем боковое меню
        self.setup_side_menu()
        content_layout.addWidget(self.sideMenu)
        
        # Создаем область контента
        self.contentArea = QFrame()
        self.contentArea.setObjectName("contentArea")
        content_area_layout = QVBoxLayout(self.contentArea)
        content_area_layout.setContentsMargins(0, 0, 0, 0)
        content_area_layout.setSpacing(0)
        
        # Добавляем лейбл с названием текущей страницы
        self.page_title = QLabel("Главная")
        self.page_title.setObjectName("pageTitle")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_area_layout.addWidget(self.page_title)
        
        self.stackedWidget = QtWidgets.QStackedWidget()
        
        # Добавляем страницы
        self.home_page = self.setup_home_page()
        self.settings_page = self.setup_settings_page()
        
        self.stackedWidget.addWidget(self.home_page)
        self.stackedWidget.addWidget(self.settings_page)
        
        # Добавляем консоль
        self.setup_console()
        
        content_area_layout.addWidget(self.stackedWidget)
        content_area_layout.addWidget(self.consoleWidget)
        
        content_layout.addWidget(self.contentArea)
        main_layout.addWidget(content_widget)
        
        # Инициализация переменных
        self.is_menu_expanded = False
        self.is_console_expanded = True
        self.menu_min_width = 50
        self.menu_max_width = 250
        self.console_min_height = 30
        self.console_max_height = 800  # Увеличиваем максимальную высоту консоли
        
        # Статистика
        self.stats = {
            'success': 75,
            'fail': 15,
            'question': 10
        }
        
        # Пути к файлам
        self.file1_path = ""
        self.file2_path = ""
        
        # Сохраняем тексты кнопок
        self.button_texts = {
            'home': ('🏠', '🏠  Главная'),
            'settings': ('⚙', '⚙  Настройки')
        }
        
        # Настройка анимаций
        self.setup_animations()
        
        # Подключение сигналов
        self.setup_connections()
        
        # Начальное состояние
        self.stackedWidget.setCurrentIndex(0)
        self.sideMenu.setMaximumWidth(self.menu_min_width)
        
        # Устанавливаем начальные тексты кнопок
        self.homeButton.setText(self.button_texts['home'][0])
        self.settingsButton.setText(self.button_texts['settings'][0])
        
        # Применяем стили напрямую
        self.setStyleSheet("""
            QMainWindow {
                background-color: transparent;
            }
            
            QWidget#sideMenu {
                background-color: #24273A;
                border: none;
            }
            
            QWidget#contentArea {
                background-color: #1A1B26;
            }
            
            QWidget#titleBar {
                background-color: #24273A;
                border-bottom: 1px solid #2F3242;
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
            }
            
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
            }
            
            QPushButton#minimizeButton, QPushButton#maximizeButton, QPushButton#closeButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 4px;
                border-radius: 4px;
                font-family: "Segoe UI";
                font-size: 16px;
            }
            
            QPushButton#minimizeButton:hover, QPushButton#maximizeButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            QPushButton#closeButton:hover {
                background-color: #DE3163;
            }
            
            QPushButton#menuButton, QPushButton#homeButton, QPushButton#settingsButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 8px;
                text-align: left;
                border-radius: 4px;
                font-size: 14px;
            }
            
            QPushButton#menuButton:hover, QPushButton#homeButton:hover, QPushButton#settingsButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            QPushButton#toggleConsoleButton {
                background-color: #7B5AF4;
                border-radius: 16px;
                padding: 8px;
                min-width: 120px;
            }
            
            QPushButton#toggleConsoleButton:hover {
                background-color: #8D6FF5;
            }
            
            QLabel {
                color: #24273A;
            }
            
            QTextEdit#console {
                background-color: #1A1B26;
                color: white;
                border: 1px solid #2F3242;
                border-radius: 8px;
                padding: 12px;
                font-family: Consolas;
                font-size: 13px;
            }
            
            QTextEdit#console QScrollBar:vertical {
                border: none;
                background: #1A1B26;
                width: 8px;
                margin: 0;
            }

            QTextEdit#console QScrollBar::handle:vertical {
                background: #7B5AF4;
                border-radius: 4px;
                min-height: 20px;
            }

            QTextEdit#console QScrollBar::handle:vertical:hover {
                background: #8D6FF5;
            }

            QTextEdit#console QScrollBar::add-line:vertical,
            QTextEdit#console QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QTextEdit#console QScrollBar::add-page:vertical,
            QTextEdit#console QScrollBar::sub-page:vertical {
                background: none;
            }
            
            QPushButton#selectFile1Button, QPushButton#selectFile2Button, QPushButton#selectPdfFolderButton, QPushButton#loadPdfButton {
                background-color: #7B5AF4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                min-width: 150px;
            }
            
            QPushButton#selectFile1Button:hover, QPushButton#selectFile2Button:hover, QPushButton#selectPdfFolderButton:hover, QPushButton#loadPdfButton:hover {
                background-color: #8D6FF5;
            }
            
            QPushButton#startButton {
                background-color: #7B5AF4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                margin-top: 16px;
            }
            
            QPushButton#startButton:hover {
                background-color: #8D6FF5;
            }
            
            QWidget#statsWidget {
                background-color: transparent;
                padding: 0;
                margin: 0;
            }
            
            QLabel#file1PathLabel, QLabel#file2PathLabel, QLabel#selectedPdfFolderLabel {
                color: #FFFFFF;
                font-size: 14px;
                padding-left: 16px;
                opacity: 0.9;
            }
            
            QLabel#pdfFolderLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }
            
            QLabel#pageTitle {
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 20px;
                background-color: #1A1B26;
                border-bottom: 1px solid #2F3242;
            }
            
            QLabel#progressLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            
            QLabel#searchResultsLabel {
                color: #8F96B3;
                font-size: 14px;
                padding: 0 8px;
                min-width: 80px;
            }
            
            QPushButton#navButton {
                background-color: transparent;
                color: #8F96B3;
                border: none;
                border-radius: 16px;
                font-size: 14px;
                font-weight: bold;
            }
            
            QPushButton#navButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            QPushButton#navButton:disabled {
                color: #3D4258;
            }
            
            QProgressBar {
                background-color: #1A1B26;
                border: 1px solid #2F3242;
                border-radius: 4px;
                color: white;
                text-align: center;
            }
            
            QProgressBar::chunk {
                background-color: #7B5AF4;
                border-radius: 3px;
            }
            
            QPushButton#clearDbButton {
                background-color: #F87381;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            
            QPushButton#clearDbButton:hover {
                background-color: #FF8C98;
            }
            
            QLineEdit#consoleSearch {
                background-color: #2F3242;
                color: white;
                border: 1px solid #3D4258;
                border-radius: 16px;
                padding: 8px 16px;
                font-size: 14px;
            }
            
            QLineEdit#consoleSearch:focus {
                border: 1px solid #7B5AF4;
            }
            
            QPushButton#clearSearchButton {
                background-color: transparent;
                color: #8F96B3;
                border: none;
                border-radius: 16px;
                font-size: 16px;
                font-weight: bold;
            }
            
            QPushButton#clearSearchButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
    def setup_title_bar(self):
        self.titleBar = QWidget()
        self.titleBar.setObjectName("titleBar")
        self.titleBar.setFixedHeight(32)
        
        layout = QHBoxLayout(self.titleBar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        
        title = QLabel("AnnyProgram")
        title.setStyleSheet("color: white; font-size: 12px;")
        
        self.minimizeButton = QPushButton("─")
        self.maximizeButton = QPushButton("□")
        self.closeButton = QPushButton("×")
        
        self.minimizeButton.setObjectName("minimizeButton")
        self.maximizeButton.setObjectName("maximizeButton")
        self.closeButton.setObjectName("closeButton")
        
        self.minimizeButton.setFixedSize(24, 24)
        self.maximizeButton.setFixedSize(24, 24)
        self.closeButton.setFixedSize(24, 24)
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.minimizeButton)
        layout.addWidget(self.maximizeButton)
        layout.addWidget(self.closeButton)
        
    def setup_side_menu(self):
        self.sideMenu = QWidget()
        self.sideMenu.setObjectName("sideMenu")
        self.sideMenu.setMinimumWidth(50)
        self.sideMenu.setMaximumWidth(250)
        
        layout = QVBoxLayout(self.sideMenu)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)
        
        self.menuButton = QPushButton("☰")
        self.menuButton.setMinimumSize(34, 34)
        
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        
        self.homeButton = QPushButton("🏠")
        self.homeButton.setMinimumSize(34, 34)
        
        self.settingsButton = QPushButton("⚙")
        self.settingsButton.setMinimumSize(34, 34)
        
        layout.addWidget(self.menuButton)
        layout.addWidget(line)
        layout.addWidget(self.homeButton)
        layout.addWidget(self.settingsButton)
        layout.addStretch()
        
    def setup_home_page(self):
        home_page = QWidget()
        layout = QVBoxLayout(home_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Создаем фрейм для кнопок и лейблов
        files_frame = QFrame()
        files_frame.setObjectName("filesFrame")
        files_frame.setStyleSheet("""
            QFrame#filesFrame {
                background-color: #2F3242;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        
        # Создаем grid layout для кнопок и лейблов
        files_layout = QGridLayout(files_frame)
        files_layout.setContentsMargins(20, 20, 20, 20)
        files_layout.setSpacing(15)
        
        # Первая строка: кнопка 1 и лейбл 1
        self.select_file1_button = QPushButton("Октрыть данные из бд")
        self.select_file1_button.setObjectName("selectFile1Button")
        
        
        files_layout.addWidget(self.select_file1_button, 0, 1)
        
        
        # Вторая строка: кнопка 2 и лейбл 2
       
        
        # Настраиваем растяжение колонок
        files_layout.setColumnStretch(1, 1)  # Лейблы будут растягиваться
        
        # Добавляем фрейм в основной layout
        layout.addWidget(files_frame)
        
        # Центрируем виджет статистики
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 20, 0, 20)  # Устанавливаем только вертикальные отступы
        
        self.stats_widget = StatsWidget()
        self.stats_widget.setObjectName("statsWidget")
        
        stats_layout.addWidget(self.stats_widget)
        
        layout.addLayout(stats_layout)
        
        # Центрируем кнопку "Начать"
        start_button_layout = QHBoxLayout()
        start_button_layout.addStretch()
        
        # self.start_button = QPushButton("Начать")
        # self.start_button.setObjectName("startButton")
        # self.start_button.setFixedWidth(200)
        
        # start_button_layout.addWidget(self.start_button)
        # start_button_layout.addStretch()
        
        layout.addLayout(start_button_layout)
        layout.addStretch()
        
        return home_page
        
    def setup_console(self):
        self.consoleWidget = QWidget()
        self.consoleWidget.setMinimumHeight(100)
        self.consoleWidget.setMaximumHeight(800)
        
        layout = QVBoxLayout(self.consoleWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Добавляем верхнюю панель для консоли
        console_header = QWidget()
        console_header_layout = QHBoxLayout(console_header)
        console_header_layout.setContentsMargins(0, 0, 0, 0)
        console_header_layout.setSpacing(8)
        
        # Кнопка сворачивания/разворачивания
        self.toggleConsoleButton = QPushButton("▼")
        self.toggleConsoleButton.setMinimumSize(32, 32)
        self.toggleConsoleButton.setMaximumSize(32, 32)
        self.toggleConsoleButton.setObjectName("toggleConsoleButton")
        
        # Строка поиска
        self.console_search = QtWidgets.QLineEdit()
        self.console_search.setPlaceholderText("🔍 Поиск в консоли...")
        self.console_search.setObjectName("consoleSearch")
        self.console_search.textChanged.connect(self.search_console)
        
        # Счетчик результатов
        self.search_results_label = QLabel("")
        self.search_results_label.setObjectName("searchResultsLabel")
        self.search_results_label.hide()
        
        # Кнопки навигации
        self.prev_result_button = QPushButton("▲")
        self.prev_result_button.setObjectName("navButton")
        self.prev_result_button.setFixedSize(32, 32)
        self.prev_result_button.clicked.connect(self.goto_prev_result)
        self.prev_result_button.hide()
        
        self.next_result_button = QPushButton("▼")
        self.next_result_button.setObjectName("navButton")
        self.next_result_button.setFixedSize(32, 32)
        self.next_result_button.clicked.connect(self.goto_next_result)
        self.next_result_button.hide()
        
        # Кнопка очистки поиска
        self.clear_search_button = QPushButton("×")
        self.clear_search_button.setObjectName("clearSearchButton")
        self.clear_search_button.setFixedSize(32, 32)
        self.clear_search_button.clicked.connect(self.clear_console_search)
        self.clear_search_button.hide()
        
        console_header_layout.addWidget(self.toggleConsoleButton)
        console_header_layout.addWidget(self.console_search)
        console_header_layout.addWidget(self.search_results_label)
        console_header_layout.addWidget(self.prev_result_button)
        console_header_layout.addWidget(self.next_result_button)
        console_header_layout.addWidget(self.clear_search_button)
        
        # Консоль
        self.console = QtWidgets.QTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        
        layout.addWidget(console_header)
        layout.addWidget(self.console)
        
        # Добавляем начальные сообщения
        self.console.append("✨ Приложение запущено")
        self.console.append("📌 Используйте боковое меню для навигации")
        self.console.append("💡 Нажмите на кнопку сверху для сворачивания/разворачивания консоли")
        self.console.append("🔍 Используйте поиск для фильтрации сообщений")
        
        # Сохраняем оригинальный текст консоли
        self.original_console_text = self.console.toPlainText()
        
        # Инициализация переменных для поиска
        self.current_search_index = -1
        self.search_results = []

    def search_console(self, text):
        # Очищаем предыдущие результаты
        cursor = self.console.textCursor()
        cursor.select(QtGui.QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QtGui.QTextCharFormat())
        cursor.clearSelection()
        
        if not text:
            self.clear_search_button.hide()
            self.search_results_label.hide()
            self.prev_result_button.hide()
            self.next_result_button.hide()
            self.current_search_index = -1
            self.search_results = []
            return
            
        self.clear_search_button.show()
        
        # Ищем все совпадения
        cursor = self.console.document().find(text, 0)
        self.search_results = []
        format = QtGui.QTextCharFormat()
        format.setBackground(QColor("#3B3F51"))
        
        while not cursor.isNull():
            self.search_results.append(cursor)
            cursor.setCharFormat(format)
            cursor = self.console.document().find(text, cursor)
        
        # Обновляем UI
        if self.search_results:
            self.search_results_label.show()
            self.prev_result_button.show()
            self.next_result_button.show()
            self.current_search_index = 0
            self.highlight_current_result()
        else:
            self.search_results_label.show()
            self.prev_result_button.hide()
            self.next_result_button.hide()
            self.current_search_index = -1
            
        self.update_search_counter()
        
    def highlight_current_result(self):
        if not self.search_results or self.current_search_index < 0:
            return
            
        # Сначала сбрасываем выделение текущего результата
        for cursor in self.search_results:
            format = QtGui.QTextCharFormat()
            format.setBackground(QColor("#3B3F51"))
            cursor.setCharFormat(format)
        
        # Выделяем текущий результат
        current_cursor = self.search_results[self.current_search_index]
        format = QtGui.QTextCharFormat()
        format.setBackground(QColor("#7B5AF4"))
        current_cursor.setCharFormat(format)
        
        # Прокручиваем к текущему результату
        self.console.setTextCursor(current_cursor)
        self.console.ensureCursorVisible()
        
    def update_search_counter(self):
        if not self.search_results:
            self.search_results_label.setText("Нет результатов")
        else:
            self.search_results_label.setText(f"{self.current_search_index + 1} из {len(self.search_results)}")
            
    def goto_next_result(self):
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            self.highlight_current_result()
            self.update_search_counter()
            
    def goto_prev_result(self):
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            self.highlight_current_result()
            self.update_search_counter()
            
    def clear_console_search(self):
        self.console_search.clear()
        cursor = self.console.textCursor()
        cursor.select(QtGui.QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QtGui.QTextCharFormat())
        cursor.clearSelection()
        self.clear_search_button.hide()
        self.search_results_label.hide()
        self.prev_result_button.hide()
        self.next_result_button.hide()
        self.current_search_index = -1
        self.search_results = []
        
    def append_to_console(self, text):
        """Новый метод для добавления текста в консоль с обновлением оригинального текста"""
        self.console.append(text)
        self.original_console_text = self.console.toPlainText()
        
        # Если есть текст в поиске, применяем фильтр
        if self.console_search.text():
            self.search_console(self.console_search.text())
        
    def setup_settings_page(self):
        settings_page = QWidget()
        main_layout = QVBoxLayout(settings_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)  # Устанавливаем минимальную высоту
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1A1B26;
            }
            QScrollBar:vertical {
                border: none;
                background: #1A1B26;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #7B5AF4;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #8D6FF5;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Создаем контейнер для содержимого
        content_widget = QWidget()
        content_widget.setObjectName("settingsContent")
        content_widget.setStyleSheet("""
            QWidget#settingsContent {
                background-color: #1A1B26;
            }
        """)
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Создаем фрейм для выбора папки с PDF
        pdf_frame = QFrame()
        pdf_frame.setObjectName("pdfFrame")
        pdf_frame.setStyleSheet("""
            QFrame#pdfFrame {
                background-color: #2F3242;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        
        # Создаем grid layout для элементов
        pdf_layout = QGridLayout(pdf_frame)
        pdf_layout.setContentsMargins(20, 20, 20, 20)
        pdf_layout.setSpacing(15)
        
        # Добавляем элементы
        self.pdf_folder_label = QLabel("Выберите папку с PDF файлами")
        self.pdf_folder_label.setObjectName("pdfFolderLabel")
        
        self.select_pdf_folder_button = QPushButton("Выбрать папку")
        self.select_pdf_folder_button.setObjectName("selectPdfFolderButton")
        
        self.selected_pdf_folder_label = QLabel("Папка не выбрана")
        self.selected_pdf_folder_label.setObjectName("selectedPdfFolderLabel")
        
        pdf_layout.addWidget(self.pdf_folder_label, 0, 0)
        pdf_layout.addWidget(self.select_pdf_folder_button, 0, 1)
        pdf_layout.addWidget(self.selected_pdf_folder_label, 1, 0, 1, 2)
        
        # Добавляем кнопку "Загрузить" внизу фрейма
        load_button_layout = QHBoxLayout()
        load_button_layout.addStretch()
        
        self.load_pdf_button = QPushButton("Загрузить")
        self.load_pdf_button.setObjectName("loadPdfButton")
        self.load_pdf_button.setFixedWidth(200)
        
        load_button_layout.addWidget(self.load_pdf_button)
        load_button_layout.addStretch()
        
        pdf_layout.addLayout(load_button_layout, 2, 0, 1, 2)
        
        # Настраиваем растяжение колонок
        pdf_layout.setColumnStretch(0, 1)  # Лейблы будут растягиваться
        
        # Добавляем фрейм в основной layout
        layout.addWidget(pdf_frame)
        
        # Создаем фрейм для прогресс-бара и кнопки очистки БД
        db_frame = QFrame()
        db_frame.setObjectName("dbFrame")
        db_frame.setStyleSheet("""
            QFrame#dbFrame {
                background-color: #2F3242;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        
        db_layout = QVBoxLayout(db_frame)
        db_layout.setContentsMargins(20, 20, 20, 20)
        db_layout.setSpacing(15)
        
        # Добавляем заголовок для прогресс-бара
        progress_label = QLabel("Прогресс обработки")
        progress_label.setObjectName("progressLabel")
        db_layout.addWidget(progress_label)
        
        # Добавляем прогресс-бар
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        db_layout.addWidget(self.progress_bar)
        
        # Добавляем кнопку очистки БД
        clear_button_layout = QHBoxLayout()
        clear_button_layout.addStretch()
        
        self.clear_db_button = QPushButton("Очистить БД")
        self.clear_db_button.setObjectName("clearDbButton")
        self.clear_db_button.setFixedWidth(200)
        
        clear_button_layout.addWidget(self.clear_db_button)
        clear_button_layout.addStretch()
        
        db_layout.addLayout(clear_button_layout)
        
        # Добавляем фрейм в основной layout
        layout.addWidget(db_frame)

        # Создаем фрейм для выбора Excel файлов
        excel_frame = QFrame()
        excel_frame.setObjectName("excelFrame")
        excel_frame.setStyleSheet("""
            QFrame#excelFrame {
                background-color: #2F3242;
                border-radius: 15px;
                padding: 20px;
            }
        """)

        excel_layout = QGridLayout(excel_frame)
        excel_layout.setContentsMargins(20, 20, 20, 20)
        excel_layout.setSpacing(15)

        # Добавляем элементы для первого Excel файла
        self.excel1_button = QPushButton("Excel c погодой")
        self.excel1_button.setObjectName("selectExcelButton")
        self.excel1_label = QLabel("Файл не выбран")
        self.excel1_label.setObjectName("excelPathLabel")

        # Добавляем элементы для второго Excel файла
        self.excel2_button = QPushButton("Excel с СБКТС")
        self.excel2_button.setObjectName("selectExcelButton")
        self.excel2_label = QLabel("Файл не выбран")
        self.excel2_label.setObjectName("excelPathLabel")

        # Размещаем элементы в сетке
        excel_layout.addWidget(self.excel1_button, 0, 0)
        excel_layout.addWidget(self.excel1_label, 0, 1)
        excel_layout.addWidget(self.excel2_button, 1, 0)
        excel_layout.addWidget(self.excel2_label, 1, 1)

        # Добавляем поля для ввода названий листов
        sheet_label = QLabel("Название листа в Excel:")
        sheet_label.setObjectName("sheetLabel")
        excel_layout.addWidget(sheet_label, 2, 0, 1, 2)

        # Только для второго Excel файла
        self.sheet2_label = QLabel("Лист с СБКТС:")
        self.sheet2_label.setObjectName("sheetNameLabel")
        self.sheet2_input = QLineEdit()
        self.sheet2_input.setObjectName("sheetInput")
        self.sheet2_input.setPlaceholderText("Введите название листа")
        excel_layout.addWidget(self.sheet2_label, 3, 0)
        excel_layout.addWidget(self.sheet2_input, 3, 1)

        # Добавляем стили для новых элементов
        excel_frame.setStyleSheet(excel_frame.styleSheet() + """
            QLabel#sheetLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                margin-top: 15px;
            }
            
            QLabel#sheetNameLabel {
                color: #FFFFFF;
                font-size: 14px;
            }
            
            QLineEdit#sheetInput {
                background-color: #2F3242;
                color: white;
                border: 1px solid #3D4258;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 14px;
            }
            
            QLineEdit#sheetInput:focus {
                border: 1px solid #7B5AF4;
            }
            
            QLineEdit#sheetInput::placeholder {
                color: #8F96B3;
            }
        """)

        # Настраиваем растяжение колонок
        excel_layout.setColumnStretch(1, 1)  # Лейблы будут растягиваться

        # Добавляем фрейм в основной layout
        layout.addWidget(excel_frame)
        
        # Добавляем растягивающийся спейсер в конец
        layout.addStretch()
        
        # Добавляем стили для новых элементов
        settings_page.setStyleSheet(settings_page.styleSheet() + """
            QPushButton#selectExcelButton {
                background-color: #7B5AF4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                min-width: 150px;
            }
            
            QPushButton#selectExcelButton:hover {
                background-color: #8D6FF5;
            }
            
            QLabel#excelPathLabel {
                color: #FFFFFF;
                font-size: 14px;
                padding-left: 16px;
                opacity: 0.9;
            }
        """)

        # Устанавливаем виджет с содержимым в QScrollArea
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        return settings_page

    def select_excel_file(self, button_num: int):
        """Метод для выбора Excel файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Выберите Excel файл {button_num}",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if file_path:
            if button_num == 1:
                self.excel1_path = file_path
                self.excel1_label.setText(file_path)
                self.append_to_console(f"[ИНФО] Выбран Excel файл 1: {file_path}")
            else:
                self.excel2_path = file_path
                self.excel2_label.setText(file_path)
                self.append_to_console(f"[ИНФО] Выбран Excel файл 2: {file_path}")

    def setup_animations(self):
        self.menu_animation = QPropertyAnimation(self.sideMenu, b'minimumWidth')
        self.menu_animation.setDuration(300)
        self.menu_animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        self.console_animation = QPropertyAnimation(self.consoleWidget, b'maximumHeight')
        self.console_animation.setDuration(300)
        self.console_animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
    def setup_connections(self):
        self.minimizeButton.clicked.connect(self.showMinimized)
        self.maximizeButton.clicked.connect(self.toggle_maximize)
        self.closeButton.clicked.connect(self.close)
        
        self.menuButton.clicked.connect(self.toggle_menu)
        self.homeButton.clicked.connect(lambda: self.switch_page(0, "Главная"))
        self.settingsButton.clicked.connect(lambda: self.switch_page(1, "Настройки"))
        self.toggleConsoleButton.clicked.connect(self.toggle_console)
        
        # self.start_button.clicked.connect(self.start_processing)
        self.select_file1_button.clicked.connect(self.open_db)
        
        self.select_pdf_folder_button.clicked.connect(self.select_pdf_folder)
        self.load_pdf_button.clicked.connect(self.load_pdf)
        self.clear_db_button.clicked.connect(self.clear_database)
        
        # Добавляем подключение сигналов для кнопок выбора Excel файлов
        self.excel1_button.clicked.connect(lambda: self.select_excel_file(1))
        self.excel2_button.clicked.connect(lambda: self.select_excel_file(2))
    
    def open_db(self):
        try:
            
            self.db_window = TableWindow()
            
            self.db_window.show()
        except Exception as e:
            print(f"[CRITICAL ERROR MAIN] Критическая ошибка: {str(e)}")
            import traceback
            print(traceback.format_exc())
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла критическая ошибка:\n{str(e)}")
        
    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.maximizeButton.setText("❐")
        else:
            self.showMaximized()
            self.maximizeButton.setText("□")
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.rect()
        # Обновляем положение элементов для изменения размера
        self.left_grip.setGeometry(0, 5, 10, rect.height() - 10)
        self.right_grip.setGeometry(rect.width() - 10, 5, 10, rect.height() - 10)
        self.top_grip.setGeometry(5, 0, rect.width() - 10, 10)
        self.bottom_grip.setGeometry(5, rect.height() - 10, rect.width() - 10, 10)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() <= self.titleBar.height():
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos'):
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'oldPos'):
            del self.oldPos
        
    def toggle_menu(self):
        width = self.menu_min_width if self.is_menu_expanded else self.menu_max_width
        self.menu_animation.setStartValue(self.sideMenu.width())
        self.menu_animation.setEndValue(width)
        self.menu_animation.start()
        
        idx = 0 if self.is_menu_expanded else 1
        self.homeButton.setText(self.button_texts['home'][idx])
        self.settingsButton.setText(self.button_texts['settings'][idx])
        
        self.is_menu_expanded = not self.is_menu_expanded
        
    def toggle_console(self, event=None):
        height = self.console_min_height if self.is_console_expanded else self.console_max_height
        self.console_animation.setStartValue(self.consoleWidget.height())
        self.console_animation.setEndValue(height)
        self.console_animation.start()
        self.is_console_expanded = not self.is_console_expanded
        
        self.toggleConsoleButton.setText('▼' if self.is_console_expanded else '▲')
        
    def select_file(self, file_num):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Выберите файл {file_num}", "", "All Files (*)")
        if file_path:
            if file_num == 1:
                self.file1_path = file_path
                self.file1_label.setText(f"Выбран файл: {os.path.basename(file_path)}")
            else:
                self.file2_path = file_path
                self.file2_label.setText(f"Выбран файл: {os.path.basename(file_path)}")
                
    def start_processing(self):
        if not hasattr(self, 'file1_path') or not hasattr(self, 'file2_path'):
            self.append_to_console("❌ Пожалуйста, выберите оба файла перед началом обработки")
            return
        
        self.append_to_console(f"✅ Начинаем обработку файлов:")
        self.append_to_console(f"📄 Файл 1: {self.file1_path}")
        self.append_to_console(f"📄 Файл 2: {self.file2_path}")
        
        # Здесь будет логика обработки файлов
        # После обработки обновляем статистику
        self.stats_widget.update_stats(75, 25)  # Пример: 75% успешных, 25% неуспешных

    def switch_page(self, index, title):
        self.stackedWidget.setCurrentIndex(index)
        self.page_title.setText(title)

    def select_pdf_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку с PDF файлами")
        if folder_path:
            self.selected_pdf_folder_label.setText(f"Выбрана папка: {folder_path}")

    def load_pdf(self):
        """Загрузка и обработка PDF файлов"""
        try:
            # Получаем путь к папке с PDF файлами
            folder_path = self.selected_pdf_folder_label.text().replace("Выбрана папка: ", "")
            if not folder_path or not os.path.exists(folder_path):
                QMessageBox.warning(self, "Предупреждение", "Выберите существующую папку с PDF файлами")
                return
                
            # Очищаем прогресс
            self.progress_bar.setValue(0)
            
            # Создаем и запускаем поток
            self.pdf_thread = PDFProcessThread(
                folder_path=folder_path,
                excel_path=self.excel1_path,  # Excel с погодой
                sheet_name=None,  # Лист по умолчанию
                sbkts_excel_path=self.excel2_path,  # Excel с СБКТС
                sbkts_sheet_name=self.sheet2_input.text()  # Название листа из поля ввода
            )
            
            # Подключаем сигналы
            self.pdf_thread.progress_updated.connect(self.update_progress)
            self.pdf_thread.file_processed.connect(self.handle_processed_file)
            self.pdf_thread.processing_finished.connect(self.handle_processing_finished)
            self.pdf_thread.error_occurred.connect(self.handle_error)
            self.pdf_thread.stats_updated.connect(self.update_stats_from_thread)
            # Блокируем кнопки
            self.load_pdf_button.setEnabled(False)
            self.load_pdf_button.setText("Обработка...")
            self.clear_db_button.setEnabled(False)
            self.select_pdf_folder_button.setEnabled(False)
            
            # Запускаем поток
            self.pdf_thread.start()
            
        except Exception as e:
            print(f"[CRITICAL ERROR MAIN] Критическая ошибка: {str(e)}")
            import traceback
            print(traceback.format_exc())
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла критическая ошибка:\n{str(e)}")
            self.handle_processing_finished()  # Восстанавливаем UI

    def handle_processed_file(self, filename, data):
        """Обработка сигнала о завершении обработки файла"""
        self.append_to_console(f"\n{'='*50}")
        self.append_to_console(f"📄 Обработан файл: {filename}")
        self.append_to_console(f"{'='*50}")
        
        # Выводим результаты в консоль
        for key, value in data.items():
            if isinstance(value, dict):
                self.append_to_console(f"\n• {key}:")
                for subkey, subvalue in value.items():
                    if subvalue:  # Выводим только непустые значения
                        self.append_to_console(f"    ‣ {subkey}: {subvalue}")
            elif value:  # Выводим только непустые значения
                self.append_to_console(f"• {key}: {value}")
                
    def handle_processing_finished(self):
        """Обработка сигнала о завершении всей обработки"""
        # Разблокируем кнопки
        self.load_pdf_button.setEnabled(True)
        self.load_pdf_button.setText("Загрузить")
        self.clear_db_button.setEnabled(True)
        self.select_pdf_folder_button.setEnabled(True)
        
        # Добавляем сообщение в консоль
        self.append_to_console("\n✅ Обработка файлов завершена")
        
    def handle_error(self, error_message):
        """Обработка сигнала об ошибке"""
        self.append_to_console(f"\n❌ {error_message}")
        
    def update_progress(self, value):
        """Обновление прогресс-бара"""
        self.progress_bar.setValue(value)

    def clear_database(self):
        try:
            # Создаем диалог подтверждения
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Подтверждение")
            msg_box.setText("Вы уверены, что хотите очистить базу данных?")
            msg_box.setInformativeText("Это действие нельзя отменить!")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            # Устанавливаем стиль для диалога
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #1A1B26;
                }
                QMessageBox QLabel {
                    color: white;
                }
                QPushButton {
                    background-color: #7B5AF4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 15px;
                    min-width: 60px;
                }
                QPushButton:hover {
                    background-color: #8D6FF5;
                }
            """)

            reply = msg_box.exec()

            if reply == QMessageBox.StandardButton.Yes:
                # Создаем и запускаем поток для очистки БД
                self.db_thread = DatabaseThread()
                self.db_thread.success.connect(self.append_to_console)
                self.db_thread.error.connect(self.handle_error)
                self.db_thread.finished.connect(self._on_tables_deleted)
                self.db_thread.start()

                # Блокируем кнопки на время очистки
                self.load_pdf_button.setEnabled(False)
                self.clear_db_button.setEnabled(False)

        except Exception as e:
            print(f"[CRITICAL ERROR MAIN] Критическая ошибка при очистке БД: {str(e)}")
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла критическая ошибка при очистке БД:\n{str(e)}")
        
    def _on_tables_deleted(self):
        """Обработчик завершения очистки БД"""
        # Разблокируем кнопки
        self.load_pdf_button.setEnabled(True)
        self.clear_db_button.setEnabled(True)
        
        # Обновляем интерфейс
        self.append_to_console("[ИНФО] Очистка базы данных завершена")
    def update_stats_from_thread(self, success_count, total_count):
        """Обновляет виджет статистики на основе данных из потока"""
        if total_count > 0:
            success_rate = (success_count / total_count) * 100
            fail_rate = ((total_count - success_count) / total_count) * 100
            self.stats_widget.update_stats(success_rate, fail_rate)
class StatsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)  # Устанавливаем только минимальную высоту
        self.success_rate = 0
        self.fail_rate = 0
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Рисуем фоновый прямоугольник с закругленными углами
        background_rect = QRectF(0, 0, width, height)
        path = QPainterPath()
        path.addRoundedRect(background_rect, 15, 15)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2F3242"))
        painter.drawPath(path)
        
        # Вычисляем размер диаграммы относительно высоты виджета
        pie_size = min(height - 40, 160)  # Возвращаем прежний размер
        
        # Центрируем диаграмму по вертикали и смещаем влево
        rect = QRectF(60, (height - pie_size) / 2, pie_size, pie_size)  # Возвращаем прежний отступ слева
        
        # Рисуем фоновый круг
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1A1B26"))
        painter.drawEllipse(rect)
        
        start_angle = 90  # Начинаем с 90 градусов (сверху)
        center = rect.center()
        
        # Рисуем успешные операции (новый цвет)
        if self.success_rate > 0:
            painter.setBrush(QColor("#947CF5"))
            success_span = int(360 * self.success_rate / 100)
            painter.drawPie(rect, start_angle * 16, -success_span * 16)
            
            # Рисуем процент для успешных операций
            if self.success_rate >= 5:
                success_angle = start_angle - (success_span / 2)
                radius = rect.width() * 0.42  # Увеличиваем радиус для текста
                angle_rad = math.radians(success_angle)
                x = center.x() + radius * math.cos(angle_rad)
                y = center.y() - radius * math.sin(angle_rad)
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(QRectF(x-20, y-10, 40, 20), Qt.AlignmentFlag.AlignCenter, f"{int(self.success_rate)}%")
            
            start_angle -= success_span
        
        # Рисуем неуспешные операции (новый цвет)
        if self.fail_rate > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#F87381"))
            fail_span = int(360 * self.fail_rate / 100)
            painter.drawPie(rect, start_angle * 16, -fail_span * 16)
            
            # Рисуем процент для неуспешных операций
            if self.fail_rate >= 5:
                fail_angle = start_angle - (fail_span / 2)
                radius = rect.width() * 0.42  # Увеличиваем радиус для текста
                angle_rad = math.radians(fail_angle)
                x = center.x() + radius * math.cos(angle_rad)
                y = center.y() - radius * math.sin(angle_rad)
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(QRectF(x-20, y-10, 40, 20), Qt.AlignmentFlag.AlignCenter, f"{int(self.fail_rate)}%")
        
        # Рисуем внутренний круг для создания кольца
        inner_size = pie_size * 0.65  # Уменьшаем размер внутреннего круга
        inner_rect = QRectF(
            rect.center().x() - inner_size/2,
            rect.center().y() - inner_size/2,
            inner_size,
            inner_size
        )
        painter.setPen(Qt.PenStyle.NoPen)  # Убираем границу
        painter.setBrush(QColor("#1A1B26"))
        painter.drawEllipse(inner_rect)
        
        # Рисуем легенду
        legend_x = rect.right() + 30
        legend_y = rect.center().y() - 30
        
        # Успешные операции в легенде (новый цвет)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#947CF5"))
        painter.drawRect(int(legend_x), int(legend_y), 16, 16)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(legend_x + 24, legend_y - 2, 100, 20), "Успешно")
        
        # Неуспешные операции в легенде (новый цвет)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#F87381"))
        painter.drawRect(int(legend_x), int(legend_y + 30), 16, 16)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(legend_x + 24, legend_y + 28, 100, 20), "Ошибки")
        
    def update_stats(self, success_rate, fail_rate):
        self.success_rate = success_rate
        self.fail_rate = fail_rate
        self.update()

class DatabaseThread(QThread):
    success = pyqtSignal(str)  # Сигнал для успешных операций
    error = pyqtSignal(str)    # Сигнал для ошибок
    finished = pyqtSignal()    # Сигнал завершения работы

    def __init__(self):
        super().__init__()
        self.db = None

    def run(self):
        try:
            # Создаем подключение к БД в текущем потоке
            self.db = Database()
            
            # Очищаем таблицу vehicles
            self.db._execute_query("DELETE FROM vehicles")
            self.success.emit("[ИНФО] Таблица vehicles очищена")
            self.success.emit("[ИНФО] База данных успешно очищена")
            
        except Exception as e:
            self.error.emit(f"[ОШИБКА] Не удалось очистить базу данных: {str(e)}")
        finally:
            if self.db:
                self.db.close()
            self.finished.emit()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 