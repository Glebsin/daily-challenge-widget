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
        if action and isinstance(action, QWidgetAction):
            # Для QWidgetAction (поле Scale) игнорируем событие
            e.ignore()
        elif action and action.isEnabled():
            action.trigger()
        else:
            e.ignore()
            
    def keyPressEvent(self, e):
        # Предотвращаем закрытие меню при нажатии Enter
        if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
            e.ignore()
        else:
            super().keyPressEvent(e)

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
        self.always_on_top = self.settings.get('always_on_top', True)
        self.animation = None
        
        # Настройки для примагничивания и перемещения стрелками
        self.snap_distance = 10  # Расстояние притягивания в пикселях
        self.arrow_step = 2      # Шаг перемещения стрелками в пикселях
        
        self.initUI()
        self.oldPos = self.pos()
        
        # Загружаем и проверяем сохраненную позицию
        pos = self.settings.get('position', {'x': 100, 'y': 100})
        screens = QApplication.screens()
        valid_position = False

        # Увеличиваем зону валидности позиции с учетом текущего масштаба
        current_width = int(self.base_width * (self.scale / 100))
        current_height = int(self.base_height * (self.scale / 100))
        
        for screen in screens:
            screen_geo = screen.geometry()
            x, y = pos.get('x', 0), pos.get('y', 0)
            if (x >= screen_geo.x() - current_width and 
                x <= screen_geo.x() + screen_geo.width() and
                y >= screen_geo.y() - current_height and
                y <= screen_geo.y() + screen_geo.height()):
                valid_position = True
                break

        if valid_position:
            self.move(pos['x'], pos['y'])
        else:
            # Размещаем окно в центре основного экрана
            center = QApplication.primaryScreen().geometry().center()
            self.move(center.x() - current_width // 2, center.y() - current_height // 2)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # После загрузки настроек устанавливаем состояние always_on_top
                    if 'always_on_top' in settings:
                        self.always_on_top = settings['always_on_top']
                        if not self.always_on_top:
                            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
                    return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
                return {}
        return {}

    def save_settings(self):
        try:
            # Получаем актуальную позицию
            current_pos = {
                'x': int(self.geometry().x()),
                'y': int(self.geometry().y())
            }
            
            settings = {
                'position': current_pos,
                'scale': self.scale,
                'use_alternative_template': self.use_alternative_template,
                'always_on_top': self.always_on_top
            }
            
            # Записываем во временный файл
            temp_file = self.settings_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            # Атомарно заменяем файл
            if sys.platform == 'win32':
                if os.path.exists(self.settings_file):
                    os.replace(temp_file, self.settings_file)
                else:
                    os.rename(temp_file, self.settings_file)
            else:
                os.rename(temp_file, self.settings_file)
                
            # Обновляем кэшированные настройки
            self.settings = settings
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            # В случае ошибки пытаемся сохранить напрямую
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f)
            except Exception as e:
                print(f"Fatal error saving settings: {e}")

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        flags = self.windowFlags()
        if self.always_on_top:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()  # Нужно пересоздать окно после изменения флагов
        self.save_settings()

    def initUI(self):
        self.updateWindowStyle()
            
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        # Устанавливаем размер в соответствии с текущим масштабом
        current_width = int(self.base_width * (self.scale / 100))
        current_height = int(self.base_height * (self.scale / 100))
        
        # Загружаем сохраненную позицию или используем значения по умолчанию
        pos = self.settings.get('position', {'x': 100, 'y': 100})
        
        # Устанавливаем геометрию с учетом масштаба
        self.setGeometry(pos['x'], pos['y'], current_width, current_height)
        self.setFixedSize(current_width, current_height)

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

        self.webView.setFixedSize(current_width, current_height)
        self.webView.setGeometry(0, 0, current_width, current_height)
        
        current_template = ALTERNATIVE_TEMPLATE if self.use_alternative_template else DEFAULT_TEMPLATE
        html_content = current_template.format(
            current_time="2025-05-19 22:22:35",
            current_user="Glebsin"
        )
        
        self.webView.page().setBackgroundColor(Qt.transparent)
        self.webView.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.webView.setHtml(html_content)
        
        if self.scale != 100:
            self.webView.setZoomFactor(self.scale / 100)
            
        self.show()

    def updateSize(self):
        if hasattr(self, 'animation') and self.animation and self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
            
        # Сохраняем текущую позицию левого верхнего угла
        current_pos = self.geometry().topLeft()
        
        # Вычисляем новые размеры
        new_width = int(self.base_width * (self.scale / 100))
        new_height = int(self.base_height * (self.scale / 100))
        
        # Создаем новую геометрию, сохраняя позицию левого верхнего угла
        new_geometry = QRect(current_pos.x(), current_pos.y(), new_width, new_height)
        
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
            # Сохраняем позицию после изменения размера
            QApplication.processEvents()
            self.settings['position'] = {
                'x': int(self.geometry().x()),
                'y': int(self.geometry().y())
            }
            self.save_settings()
        
        self.animation.finished.connect(onAnimationFinished)
        self.animation.start()

    def setScale(self, scale):
        old_pos = self.geometry().topLeft()  # Сохраняем текущую позицию
        self.scale = scale
        # Сразу сохраняем новый масштаб в настройках
        self.settings['scale'] = scale
        self.save_settings()
        self.updateSize()
        # После изменения размера возвращаем позицию
        self.move(old_pos)

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
        
        # Устанавливаем размер с учетом текущего масштаба
        current_width = int(self.base_width * (self.scale / 100))
        current_height = int(self.base_height * (self.scale / 100))
        
        self.webView.setFixedSize(current_width, current_height)
        self.webView.setGeometry(0, 0, current_width, current_height)
        
        current_template = ALTERNATIVE_TEMPLATE if self.use_alternative_template else DEFAULT_TEMPLATE
        html_content = current_template.format(
            current_time="2025-05-19 22:22:35",
            current_user="Glebsin"
        )
        
        self.webView.page().setBackgroundColor(Qt.transparent)
        self.webView.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.webView.setHtml(html_content)
        
        if current_scale != 100:
            self.webView.setZoomFactor(current_scale / 100)
        
        self.webView.show()
        self.move(current_pos)
        self.save_settings()

    def keyPressEvent(self, event):
        # Сохраняем существующую обработку комбинации клавиш
        self.key_sequence.append(event.key())
        if len(self.key_sequence) > 3:
            self.key_sequence = self.key_sequence[-3:]
        
        if len(self.key_sequence) == 3:
            if self.key_sequence == [Qt.Key_7, Qt.Key_2, Qt.Key_7]:
                self.toggleDebugBorder()
                print(f"Debug border toggled: {'ON' if self.debug_border else 'OFF'}")
            self.key_sequence = []

        moved = False
        # Обработка стрелок без ограничений
        if event.key() == Qt.Key_Left:
            self.move(self.x() - self.arrow_step, self.y())
            moved = True
        elif event.key() == Qt.Key_Right:
            self.move(self.x() + self.arrow_step, self.y())
            moved = True
        elif event.key() == Qt.Key_Up:
            self.move(self.x(), self.y() - self.arrow_step)
            moved = True
        elif event.key() == Qt.Key_Down:
            self.move(self.x(), self.y() + self.arrow_step)
            moved = True

        if moved:
            # Даем окну время обновить свою позицию
            QApplication.processEvents()
            self.settings['position'] = {
                'x': int(self.geometry().x()),
                'y': int(self.geometry().y())
            }
            self.save_settings()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.createContextMenu()
        else:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        new_pos = QPoint(self.x() + delta.x(), self.y() + delta.y())
        
        # Получаем все экраны
        screens = QApplication.screens()
        current_screen = None
        
        # Определяем, на каком экране находится курсор
        for screen in screens:
            if screen.geometry().contains(event.globalPos()):
                current_screen = screen
                break
        
        if not current_screen:
            current_screen = QApplication.primaryScreen()
        
        # Проверяем близость к краям экрана только если двигаемся медленно
        if abs(delta.x()) < 5 and abs(delta.y()) < 5:
            screen_geo = current_screen.geometry()
            
            # Проверяем близость к краям экрана с учетом геометрии текущего экрана
            if abs(new_pos.x() - screen_geo.x()) < self.snap_distance:
                new_pos.setX(screen_geo.x())
            elif abs((screen_geo.x() + screen_geo.width()) - (new_pos.x() + self.width())) < self.snap_distance:
                new_pos.setX(screen_geo.x() + screen_geo.width() - self.width())
                
            if abs(new_pos.y() - screen_geo.y()) < self.snap_distance:
                new_pos.setY(screen_geo.y())
            elif abs((screen_geo.y() + screen_geo.height()) - (new_pos.y() + self.height())) < self.snap_distance:
                new_pos.setY(screen_geo.y() + screen_geo.height() - self.height())
        
        self.move(new_pos)
        self.oldPos = event.globalPos()
        
        # Сохраняем позицию только при медленном движении
        if abs(delta.x()) < 5 and abs(delta.y()) < 5:
            # Обновляем сохраненную позицию
            self.settings['position'] = {
                'x': int(self.geometry().x()),
                'y': int(self.geometry().y())
            }
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
                if value > 500:
                    value = 500
                    scaleInput.setText(str(value))
                if value < 100:
                    value = 100
                    scaleInput.setText(str(value))
                self.setScale(value)
            except ValueError:
                scaleInput.setText(str(self.scale))
            finally:
                # Устанавливаем фокус обратно на поле ввода и выделяем текст
                scaleInput.setFocus()
                scaleInput.selectAll()
        
        # Изменяем обработку события returnPressed
        def handleReturnPressed():
            updateScale()
        
        # Подключаем сигнал
        scaleInput.returnPressed.connect(handleReturnPressed)
        
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
        
        alwaysOnTopAction = QAction('Always on Top', self)
        alwaysOnTopAction.setCheckable(True)
        alwaysOnTopAction.setChecked(self.always_on_top)
        alwaysOnTopAction.triggered.connect(self.toggle_always_on_top)
        menu.addAction(alwaysOnTopAction)
        
        menu.addSeparator()
        
        timeAction = QAction('Updated: 2025-05-19 22:22:35', self)
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
        
        # Устанавливаем фокус на поле ввода при открытии меню
        scaleInput.setFocus()
        scaleInput.selectAll()

    def closeApp(self):
        # Сохраняем текущую позицию
        current_pos = {
            'x': int(self.geometry().x()),
            'y': int(self.geometry().y())
        }
        self.settings['position'] = current_pos
        
        # Сначала сохраняем настройки
        self.save_settings()
        
        # Обрабатываем оставшиеся события
        QApplication.processEvents()
        
        # Затем очищаем и закрываем
        if hasattr(self, 'webView'):
            self.webView.setHtml("")
            self.webView.page().profile().clearAllVisitedLinks()
            self.webView.close()
            self.webView.deleteLater()
        QApplication.instance().quit()

    def closeEvent(self, event):
        # Сохраняем текущую позицию
        current_pos = {
            'x': int(self.geometry().x()),
            'y': int(self.geometry().y())
        }
        self.settings['position'] = current_pos
        
        # Сначала сохраняем настройки
        self.save_settings()
        
        # Обрабатываем оставшиеся события
        QApplication.processEvents()
        
        # Затем очищаем и закрываем
        if hasattr(self, 'webView'):
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