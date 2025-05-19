import sys
import json
import os
from datetime import datetime, timezone
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMenu, QAction, 
                           QWidgetAction, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QLineEdit)
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile
from PyQt5.QtGui import QCursor
from widget_templates import DEFAULT_TEMPLATE, ALTERNATIVE_TEMPLATE

class NonClosingMenu(QMenu):
    def mouseReleaseEvent(self, e):
        action = self.activeAction()
        if action and action.isEnabled():
            action.trigger()
        else:
            e.ignore()

class TransparentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.debug_border = False
        self.settings_file = "widget_settings.json"
        self.settings = self.load_settings()
        
        self.scale = self.settings.get('scale', 100)
        self.base_width = 150
        self.base_height = 57
        
        self.key_sequence = []
        self.use_alternative_template = self.settings.get('use_alternative_template', False)
        self.animation = None
        
        self.initUI()
        self.oldPos = self.pos()
        
        pos = self.settings.get('position', {'x': 100, 'y': 100})
        self.move(pos['x'], pos['y'])

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_settings(self):
        settings = {
            'position': {
                'x': self.x(),
                'y': self.y()
            },
            'scale': self.scale,
            'use_alternative_template': self.use_alternative_template
        }
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def initUI(self):
        self.updateWindowStyle()
            
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        
        self.setGeometry(100, 100, self.base_width, self.base_height)
        self.setFixedSize(self.base_width, self.base_height)

        if hasattr(self, 'webView'):
            self.webView.deleteLater()

        self.webView = QWebEngineView(self)
        
        # Оптимизация WebEngine
        settings = self.webView.settings()
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, False)
        settings.setAttribute(QWebEngineSettings.AutoLoadIconsForPage, False)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, False)
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, False)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)

        # Оптимизация профиля
        profile = QWebEngineProfile.defaultProfile()
        profile.clearHttpCache()
        profile.setCachePath("")
        profile.setPersistentStoragePath("")
        profile.setHttpCacheType(QWebEngineProfile.NoCache)
        profile.setHttpCacheMaximumSize(0)

        self.webView.setFixedSize(self.base_width, self.base_height)
        self.webView.setGeometry(0, 0, self.base_width, self.base_height)
        
        current_template = ALTERNATIVE_TEMPLATE if self.use_alternative_template else DEFAULT_TEMPLATE
        html_content = current_template.format(
            current_time="2025-05-19 12:45:16",
            current_user="Glebsin"
        )
        
        self.webView.page().setBackgroundColor(Qt.transparent)
        self.webView.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.webView.setHtml(html_content)
        
        if self.scale != 100:
            self.setScale(self.scale)
            
        self.show()

    def updateSize(self):
        if hasattr(self, 'animation') and self.animation and self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
            
        # Сохраняем текущий центр окна перед изменением
        current_center = self.geometry().center()
        
        # Вычисляем новые размеры
        new_width = int(self.base_width * (self.scale / 100))
        new_height = int(self.base_height * (self.scale / 100))
        
        # Вычисляем новые координаты, чтобы сохранить положение центра
        new_x = max(0, current_center.x() - (new_width // 2))
        new_y = max(0, current_center.y() - (new_height // 2))
        
        # Создаем новую геометрию
        new_geometry = QRect(new_x, new_y, new_width, new_height)
        
        # Создаем и настраиваем анимацию
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(100)
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(new_geometry)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Обновляем webView сразу
        self.webView.setFixedSize(new_width, new_height)
        self.webView.setZoomFactor(self.scale / 100)
        
        # Обработчик завершения анимации
        def onAnimationFinished():
            self.setFixedSize(new_width, new_height)
            if hasattr(self, 'animation'):
                self.animation.finished.disconnect()
                self.animation = None
        
        self.animation.finished.connect(onAnimationFinished)
        self.animation.start()

    def setScale(self, scale):
        self.scale = scale
        self.updateSize()

    def updateWindowStyle(self):
        self.setAttribute(Qt.WA_TranslucentBackground, not self.debug_border)
        if self.debug_border:
            self.setStyleSheet("""
                QMainWindow {
                    border: 2px solid red;
                    background-color: rgba(0, 0, 0, 10);
                }
            """)
        else:
            self.setStyleSheet("")

    def toggleDebugBorder(self):
        self.debug_border = not self.debug_border
        self.updateWindowStyle()

    def toggle_template(self):
        current_pos = self.pos()
        current_scale = self.scale
        self.use_alternative_template = not self.use_alternative_template
        
        if hasattr(self, 'webView'):
            self.webView.setHtml("")
            self.webView.deleteLater()
        
        self.webView = QWebEngineView(self)
        
        settings = self.webView.settings()
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, False)
        settings.setAttribute(QWebEngineSettings.AutoLoadIconsForPage, False)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, False)
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, False)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        
        self.webView.setFixedSize(self.base_width, self.base_height)
        self.webView.setGeometry(0, 0, self.base_width, self.base_height)
        
        current_template = ALTERNATIVE_TEMPLATE if self.use_alternative_template else DEFAULT_TEMPLATE
        html_content = current_template.format(
            current_time="2025-05-19 12:45:16",
            current_user="Glebsin"
        )
        
        self.webView.page().setBackgroundColor(Qt.transparent)
        self.webView.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.webView.setHtml(html_content)
        
        if current_scale != 100:
            self.setScale(current_scale)
        
        self.webView.show()
        self.move(current_pos)
        self.save_settings()

    def keyPressEvent(self, event):
        self.key_sequence.append(event.key())
        
        if len(self.key_sequence) > 3:
            self.key_sequence = self.key_sequence[-3:]
        
        if len(self.key_sequence) == 3:
            if self.key_sequence == [Qt.Key_7, Qt.Key_2, Qt.Key_7]:
                self.toggleDebugBorder()
                print(f"Debug border toggled: {'ON' if self.debug_border else 'OFF'}")
            self.key_sequence = []

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.createContextMenu()
        else:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()
        self.save_settings()

    def createContextMenu(self):
        menu = NonClosingMenu(self)
        
        # Создаем виджет для поля ввода
        scaleWidget = QWidget()
        scaleLayout = QVBoxLayout(scaleWidget)
        
        # Добавляем метку со значениями
        scaleLabel = QLabel('Scale, % (100-500)')
        scaleLabel.setStyleSheet("color: white; padding: 2px 0;")
        
        # Создаем поле ввода
        scaleInput = QLineEdit()
        scaleInput.setText(str(self.scale))
        scaleInput.setFixedWidth(100)
        scaleInput.setStyleSheet("""
            QLineEdit {
                background-color: #3D3D3D;
                color: white;
                border: 1px solid #4D4D4D;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)
        
        # Обработчик изменения масштаба
        def updateScale():
            try:
                value = int(scaleInput.text())
                if 100 <= value <= 500:
                    self.setScale(value)
                else:
                    scaleInput.setText(str(self.scale))
            except ValueError:
                scaleInput.setText(str(self.scale))
        
        # Подключаем сигнал
        scaleInput.returnPressed.connect(updateScale)
        
        # Добавляем виджеты в layout
        scaleLayout.addWidget(scaleLabel)
        scaleLayout.addWidget(scaleInput)
        
        # Создаем действие для добавления виджета в меню
        scaleAction = QWidgetAction(menu)
        scaleAction.setDefaultWidget(scaleWidget)
        menu.addAction(scaleAction)
        
        menu.addSeparator()

        templateAction = QAction('Use Alternative Template', self)
        templateAction.setCheckable(True)
        templateAction.setChecked(self.use_alternative_template)
        templateAction.triggered.connect(self.toggle_template)
        menu.addAction(templateAction)
        
        menu.addSeparator()
        
        timeAction = QAction('Updated: 2025-05-19 12:45:16', self)
        timeAction.setEnabled(False)
        menu.addAction(timeAction)
        
        userAction = QAction('User: Glebsin', self)
        userAction.setEnabled(False)
        menu.addAction(userAction)
        
        menu.addSeparator()
        exitAction = menu.addAction('Exit')
        exitAction.triggered.connect(self.closeApp)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                color: white;
                border: 1px solid #3D3D3D;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3D3D3D;
            }
            QMenu::item:disabled {
                color: #808080;
            }
            QMenu::indicator {
                width: 15px;
                height: 15px;
            }
            QMenu::indicator:checked {
                background: #4CAF50;
            }
            QLabel {
                color: white;
                padding: 2px 0;
            }
            QWidget {
                background-color: #2D2D2D;
            }
        """)
        
        pos = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        menu_size = menu.sizeHint()
        
        if pos.x() + menu_size.width() > screen.right():
            pos.setX(pos.x() - menu_size.width())
        
        menu.exec_(pos)

    def closeApp(self):
        self.save_settings()
        self.webView.setHtml("")
        self.webView.page().profile().clearAllVisitedLinks()
        self.webView.close()
        self.webView.deleteLater()
        QApplication.instance().quit()

    def closeEvent(self, event):
        self.save_settings()
        self.webView.setHtml("")
        self.webView.page().profile().clearAllVisitedLinks()
        self.webView.close()
        self.webView.deleteLater()
        event.accept()

if __name__ == '__main__':
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-logging --disable-gpu --disable-software-rasterizer --disable-dev-shm-usage'
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    
    ex = TransparentWindow()
    sys.exit(app.exec_())