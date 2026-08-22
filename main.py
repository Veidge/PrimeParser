import os.path
import sys
from json import JSONDecodeError
from PyQt5.QtGui import QCursor, QPixmap, QDesktopServices, QIcon
import functions
import json
from PyQt5.QtWidgets import QApplication, QComboBox, QPushButton, QTableWidgetItem, QSpinBox, QMainWindow, QLineEdit, \
    QWidget, QVBoxLayout, QLabel, QMessageBox, QDialog, QHBoxLayout
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QTimer
from gui.main_gui import Ui_MainWindow
from gui.second_gui import Ui_SettingsWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.settings_window = SettingsWindow()

        self.ui.setupUi(self)
        self.requests = []

        self.name = "My name"
        self.platform = "pc"
        self.crossplay = True
        self.refresh_interval = "20 минут"

        # self.platform = settings["platform"]
        # self.crossplay = settings["crossplatform"]

        self.ui.marketTable.viewport().installEventFilter(self)
        # self.ui.buy_btn.clicked.connect(self.message_text())
        self.ui.search_btn.clicked.connect(self.search)
        self.ui.search_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ui.add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ui.add_btn.clicked.connect(self.save_requests)
        self.ui.delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ui.delete_btn.clicked.connect(self.delete_requests)
        self.ui.settings_btn.clicked.connect(self.open_settings)
        self.refresh_button()

        if self.ui.marketTable.rowCount() == 0:
            self.ui.buy_btn.hide()
            self.ui.search_btn.setGeometry(QtCore.QRect(1130, 230, 111, 38))

        try:
            self.apply_settings()
        except:
            SettingsWindow()

        try:
            self.apply_requests()
        except:
            pass

        self.refreshing_requests()

    def eventFilter(self, obj, event):
        if obj == self.ui.marketTable.viewport():
            if event.type() == QtCore.QEvent.MouseButtonPress:
                index = self.ui.marketTable.indexAt(event.pos())
                if not index.isValid():
                    self.ui.marketTable.clearSelection()
        return super().eventFilter(obj, event)

    def open_settings(self):
        settings_window = SettingsWindow()
        if settings_window.exec_() == QDialog.Accepted:
            self.apply_settings()

    # @staticmethod
    # def create_scaled_pixmap(image_data: bytes, size=35):
    #     pixmap = QPixmap()
    #     pixmap.loadFromData(image_data)
    #
    #     return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def search(self):
        self.search_window = SearchWindow(self.platform, self.crossplay)
        self.search_window.submitted.connect(self.handle_search)
        self.search_window.show()

    def handle_search(self, data):
        result = functions.collect_data_parts(
            data["name"],
            data["type"],
            self.platform,
            data["quantity"],
            data["wishedPrice"],
            self.crossplay
        )

        self.requests.append({
            "name": data["name"],
            "type": data["type"],
            "quantity": data["quantity"],
            "wishedPrice": data["wishedPrice"]
        })

        # with open("saved_requests.json", "w", encoding="UTF-8") as file:
        #     json.dump(self.requests, file)

        if not result:
            info_message = QMessageBox(window)
            info_message.setWindowTitle("Ошибка")
            info_message.setText(
                f"Заказ ' {data['name']} ' стоимостью {data['wishedPrice']} ед. платины не найден.")
            info_message.exec_()
            return

        icon_url = functions.get_api_icon(data["name"])
        image_bytes = functions.download_icon_bytes(icon_url)

        self.ui.marketTable.setSortingEnabled(False)

        for i in result:
            stats_url = functions.get_statistics_url(i["name"])

            row = self.ui.marketTable.rowCount()
            self.ui.marketTable.insertRow(row)
            self.ui.marketTable.setRowHeight(row, 50)

            graph_icon = QIcon()
            graph_icon.addPixmap(QPixmap("icons/stats_icon.svg"), QIcon.Normal, QIcon.Off)

            graph_btn = QPushButton("График")
            graph_btn.setStyleSheet("color: #18252a;"
                                    "background-color: #418fa5;"
                                    "font-weight: bold;")
            graph_btn.setIcon(graph_icon)
            graph_btn.setFixedSize(135, 45)
            graph_btn.setToolTip(f"График цен {i['name'].replace('_', ' ').title()}")
            graph_btn.setCursor(QCursor(Qt.PointingHandCursor))
            graph_btn.clicked.connect(lambda _, url=stats_url: QDesktopServices.openUrl(QUrl(url)))

            cell_widget = QWidget()
            layout = QHBoxLayout(cell_widget)
            layout.addWidget(graph_btn)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            cell_widget.setLayout(layout)

            self.ui.marketTable.setCellWidget(row, 7, cell_widget)

            if image_bytes is not None:
                pixmap = functions.bytes_to_image(image_bytes)
                pixmap = pixmap.scaled(
                    45, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label = QLabel()
                label.setPixmap(pixmap)
                label.setAlignment(Qt.AlignCenter)
                self.ui.marketTable.setCellWidget(
                    row, 0, label)
            else:
                self.ui.marketTable.setItem(
                    row, 0, QTableWidgetItem("No Image"))

            self.ui.marketTable.setItem(
                row, 1, QTableWidgetItem(i["ingameName"]))
            self.ui.marketTable.setItem(
                row, 2, QTableWidgetItem(i["name"].replace("_", " ").title()))
            self.ui.marketTable.setItem(
                row, 3, QTableWidgetItem(i["type"]))
            self.ui.marketTable.setItem(
                row, 4, QTableWidgetItem(str(i["quantity"])))
            self.ui.marketTable.setItem(
                row, 5, QTableWidgetItem(str(i["price"])))
            self.ui.marketTable.setItem(
                row, 6, QTableWidgetItem(str(data["wishedPrice"])))

            self.buy_button_copy(row)

            if row < 1:
                y_buy_btn = self.ui.search_btn.y() + 45
            else:
                y_buy_btn = self.ui.search_btn.y() + 50

            self.ui.search_btn.setGeometry(
                QtCore.QRect(1130, y_buy_btn, 111, 38))

        self.ui.marketTable.setSortingEnabled(True)

    def buy_button_copy(self, row):
        x = self.ui.buy_btn.x()
        y = self.ui.buy_btn.y() + 50 * row
        width = self.ui.buy_btn.width()
        height = self.ui.buy_btn.height() + 10

        button = QtWidgets.QPushButton(self.centralWidget())
        button.setGeometry(QtCore.QRect(x, y, width, height))
        button.setStyleSheet(self.ui.buy_btn.styleSheet())
        button.setIcon(self.ui.buy_btn.icon())
        button.setText(self.ui.buy_btn.text())
        button.setObjectName(f"buy_btn_{row}")
        button.setCursor(QCursor(Qt.PointingHandCursor))

        button.clicked.connect(lambda x, r=row: self.message_text(r))
        button.show()

    def refresh_button(self):
        refresh_icon = QIcon()
        refresh_icon.addPixmap(QPixmap("icons/refresh_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"),
                               QIcon.Normal, QIcon.Off)

        refresh_btn = QtWidgets.QPushButton(self.centralWidget())
        refresh_btn.setGeometry(QtCore.QRect(5, 175, 33, 45))
        refresh_btn.setStyleSheet(self.ui.search_btn.styleSheet())
        refresh_btn.setIcon(refresh_icon)
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.clicked.connect(self.refreshing)
        # self.refresh_button.clicked.connect(
        # threading.Thread(target=self.refreshing, daemon=True).start())

    def refreshing(self):
        # запомнить поля (записи). Временное хранилище (все записи для поиска / файл + после файла)
        # очистить все поля, что есть
        # заново вызвать все записи через handle_search.

        if not self.requests:
            return

        old_requests = self.requests.copy()
        search_btn_geometry = self.ui.search_btn.geometry()

        self.ui.marketTable.clearContents()
        self.ui.marketTable.setRowCount(0)
        buttons = [b for b in self.findChildren(QtWidgets.QPushButton)
                   if b.objectName().startswith("buy_btn_")]
        for button in buttons:
            button.deleteLater()
        self.requests = []

        for request in old_requests:
            self.handle_search(request)

        self.ui.search_btn.setGeometry(search_btn_geometry)

    def message_text(self, row):
        ingameName = self.ui.marketTable.item(row, 1).text()
        name = self.ui.marketTable.item(row, 2).text()
        price = self.ui.marketTable.item(row, 5).text()

        message = f"/w {ingameName} Hi! I want to buy: '{name}' for {price} platinum. (warframe.market)"
        QApplication.clipboard().setText(message)
        print(f"Сообщение для {ingameName} скопировано")

        copy_message = QMessageBox(window)
        copy_message.setWindowTitle("Сообщение")
        copy_message.setText(
            f"Сообщение для связи с игроком {ingameName} скопировано!")
        copy_message.exec_()

    def apply_settings(self):
        if not os.path.exists("settings.json"):
            return

        with open("settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)

        self.ui.lbl_current_name.setText(settings["username"])

        platform_map = {
            "pc": "ПК",
            "ps4": "PlayStation",
            "xbox": "Xbox",
            "switch": "Switch",
            "mobile": "Мобильные"
        }

        crossplay_map = {
            True: "Да",
            False: "Нет"
        }

        self.ui.lbl_current_platform.setText(
            platform_map.get(settings["platform"])
        )

        self.ui.lbl_current_crossplat.setText(
            crossplay_map.get(settings["crossplay"])
        )

        self.refresh_interval = settings["refresh_interval"]


    def apply_requests(self):
        if not os.path.exists("saved_requests.json"):
            return
        with open("saved_requests.json", "r", encoding="UTF-8") as file:
            r = json.load(file)
            for i in r:
                self.handle_search(i)

    def save_requests(self):
        row = self.ui.marketTable.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Ошибка", "Необходимо выбрать запись")
            return

        with open("saved_requests.json", "w", encoding="UTF-8") as file:
            json.dump(self.requests, file, ensure_ascii=False, indent=4)
            QMessageBox.about(window, "Сообщение",
                              "Ваш заказ успешно сохранён!")

    def delete_requests(self):
        row = self.ui.marketTable.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Ошибка", "Необходимо выбрать заказ")
            return

        self.requests.pop(row)

        buttons = [
            b for b in self.findChildren(QtWidgets.QPushButton)
            if b.objectName().startswith("buy_btn_")
        ]

        if buttons:
            buttons[-1].deleteLater()

        with open("saved_requests.json", "w", encoding="UTF-8") as file:
            json.dump(self.requests, file, indent=4, ensure_ascii=False)

        self.ui.marketTable.removeRow(row)
        QMessageBox.information(
            self, "Сообщение", "Запись успешно удалена")
        y_buy_btn = self.ui.search_btn.y() - 55
        self.ui.search_btn.setGeometry(
            QtCore.QRect(1130, y_buy_btn, 111, 38))

    def get_interval_number(self):
        interval = self.refresh_interval
        number = int(interval.split()[0])

        if 'час' in interval:
            return number * 3600
        else:
            return number * 60

    def refreshing_requests(self):
        interval = self.get_interval_number()
        timer = QTimer(self)
        timer.timeout.connect(self.refreshing)
        timer.start(interval * 1000)


class SearchWindow(QWidget):
    submitted = pyqtSignal(dict)

    def __init__(self, platform: str = "pc", crossplay: bool = True):
        super().__init__()
        layout = QVBoxLayout()

        self.platform = platform
        self.crossplay = crossplay

        label1 = QLabel("Название предмета")
        label2 = QLabel("Желаемая цена")
        label3 = QLabel("Количество")

        layout.addWidget(label1)

        self.name = QLineEdit()
        layout.addWidget(self.name)

        layout.addWidget(label2)

        self.max_price = QSpinBox()
        self.max_price.setRange(1, 99999)
        self.max_price.setSingleStep(1)
        layout.addWidget(self.max_price)

        layout.addWidget(label3)

        self.quantity = QSpinBox()
        self.quantity.setMinimum(1)
        self.quantity.setMaximum(99999)
        self.quantity.setSingleStep(1)
        layout.addWidget(self.quantity)

        self.combo = QComboBox()
        self.combo.addItems(["Купить", "Продать"])
        self.combo.setItemData(0, "sell")
        self.combo.setItemData(1, "buy")
        self.combo.setCurrentIndex(0)
        layout.addWidget(self.combo)

        self.submit = QPushButton()
        self.submit.setText("Подтвердить")
        self.submit.clicked.connect(self.sub)
        layout.addWidget(self.submit)

        self.setLayout(layout)

    def sub(self):
        try:
            data = {
                "name": self.name.text(),
                "wishedPrice": int(self.max_price.text()),
                "type": self.combo.currentData(),
                "quantity": int(self.quantity.text())
            }
            self.submitted.emit(data)
            self.close()
        except Exception as e:
            self.w = PopupWindow(str(e))
            self.w.show()


class PopupWindow(QWidget):
    def __init__(self, error_text: str):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel(error_text)
        layout.addWidget(label)

        self.setLayout(layout)


class SettingsWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.ui = Ui_SettingsWindow()
        self.ui.setupUi(self)
        self.ui.pushButton.clicked.connect(self.save_button_clicked)

        self.ui.comboBox.setItemData(0, "pc")
        self.ui.comboBox.setItemData(1, "ps4")
        self.ui.comboBox.setItemData(2, "xbox")
        self.ui.comboBox.setItemData(3, "switch")
        self.ui.comboBox.setItemData(4, "mobile")

        self.ui.comboBox_2.setItemData(0, True)
        self.ui.comboBox_2.setItemData(1, False)

        self.ui.comboBox_3.setItemData(0, "1 минута")
        self.ui.comboBox_3.setItemData(1, "5 минут")
        self.ui.comboBox_3.setItemData(2, "10 минут")
        self.ui.comboBox_3.setItemData(3, "30 минут")
        self.ui.comboBox_3.setItemData(4, "1 час")

        self.load_settings()

    def save_button_clicked(self):
        name = self.ui.lineEdit.text()
        platform = self.ui.comboBox.currentData()
        crossplay = self.ui.comboBox_2.currentData()
        refresh_interval = self.ui.comboBox_3.currentText()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Подтверждение")
        msg_box.setText("Изменить настройки?")

        yes_button = msg_box.addButton("Да", QMessageBox.YesRole)
        no_button = msg_box.addButton("Нет", QMessageBox.NoRole)

        msg_box.exec_()

        if msg_box.clickedButton() == yes_button:
            data = {
                "username": name,
                "platform": platform,
                "crossplay": crossplay,
                "refresh_interval": refresh_interval
            }

            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                window.name = data["username"]
                window.platform = data["platform"]
                window.crossplay = data["crossplay"]
            self.accept()
        else:
            self.reject()

    def load_settings(self):
        try:
            with open("settings.json", "r+", encoding="utf-8") as f:
                data = json.load(f)

                self.ui.lineEdit.setText(data["username"])

                index_platform = self.ui.comboBox.findData(data["platform"])
                self.ui.comboBox.setCurrentIndex(index_platform)

                index_crossplay = self.ui.comboBox_2.findData(
                    data["crossplay"])
                self.ui.comboBox_2.setCurrentIndex(index_crossplay)

                self.ui.comboBox_3.setCurrentText(data["refresh_interval"])

        except FileNotFoundError:
            pass

        # по умолчанию
        except JSONDecodeError:
            with open("settings.json", "r+", encoding="utf-8") as f:
                json.dump({"username": "",
                           "platform": "pc",
                           "crossplay": True}, f)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
