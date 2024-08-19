import sys
from PyQt5.QtWidgets import QMessageBox, QDialog, QStatusBar, QComboBox, QTextEdit, QCheckBox, QFileDialog, QApplication, QMainWindow,QPushButton, QWidget,QGridLayout,QHBoxLayout,QSpacerItem,QSizePolicy,QLabel,QSpinBox
from PyQt5.QtCore import QCoreApplication,QMetaObject, QSettings, QThread, pyqtSignal, pyqtSlot
from PyQt5 import QtGui
import os
from datetime import datetime
import speech_recognition as sr
import sqlite3
from deep_translator import GoogleTranslator, LingueeTranslator, PonsTranslator
from yandex_recognize import yd_recognize
from pathlib import Path
from connect import connect_to_postgres
#from voice_to_file import listen_init
from voice_to_file_thr import listen_init
import gpt_help
import clipboard



class ReadThread(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, read_method):
        super().__init__()
        self._read_method = read_method
        self._running = True

    def run(self):
        self._read_method()  # Call the read_queue method
        self.finished_signal.emit()

    def stop(self):
        self._running = False
        self.wait()

class Queue:

    def __init__(self):
        #self.connection = sqlite3.connect("voise_data.db", check_same_thread=False)
        pass


    def is_empty(self):
        try:
            connection = connect_to_postgres()
            cursor = connection.cursor()
            cursor.execute("select count(*) FROM files_queue")
            count = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return count == 0
        except Exception as e:
            if str(e).find('no such table: files_queue') > -1:
                print(f"count=err")
                return True
            else:
                raise

    def time_record(self):
        connection = connect_to_postgres()
        cursor = connection.cursor()
        cursor.execute("select time_record FROM time_record")
        tr = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        return tr

    def enqueue(self, item):
        # self.items.append(item)
        pass

    def dequeue(self):
        try:
            connection = connect_to_postgres()
            cursor = connection.cursor()
            cursor.execute("select id, name, start_time FROM files_queue ORDER BY id LIMIT 1")
            self.cur_id, self.cur_file, self.start_time = cursor.fetchone()
            cursor.close()
            connection.close()
            return (self.cur_id, self.cur_file, self.start_time)
        except Exception as err:
            print(err)
            raise

    def del_file(self, id, file_path):
        try:
            connection = connect_to_postgres()
            cursor = connection.cursor()
            cursor.execute(f"delete FROM files_queue where id={id}")
            connection.commit()
            cursor.close()
            connection.close()
            os.remove(file_path)
        except Exception as err:
            print(err)
            raise

    def del_off(self):
        connection = connect_to_postgres()
        cursor = connection.cursor()
        cursor.execute("select id, name FROM files_queue")
        data = cursor.fetchall()
        connection.close()
        for rec in data:
            if os.path.exists(rec[1]):
                self.del_file(rec[0], rec[1])



class Ui_MainWindow(QWidget):
    run = False
    run_read = False
    count = 0
    appQueue = Queue()
    total_text = ''
    hear_text = ''

    def user_init(self, MainWindow):
        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)
        self.add_actions()
        self.settings = QSettings('jarik', 'RealVoise')
        try:
            data1 = self.settings.value('val_pathlabel', defaultValue='')
            data2 = self.settings.value('val_duration_spinBox', defaultValue='10')
            self.checkBox_translate.setChecked(self.settings.value('checkBox_translate', False, type=bool))
            self.checkBoxShowSorce.setChecked(self.settings.value('checkBoxShowSorce', False, type=bool))
            self.checkBoxOnlyText.setChecked(self.settings.value('checkBoxOnlyText', False, type=bool))
            data3 = self.settings.value('comboBoxLanguage', defaultValue = 'English')
            self.comboBoxLanguage.setCurrentText(data3)
            self.pathlabel.setText(data1)
            self.duration_spinBox.setValue(int(data2))
            self.text_browser = self.settings.value('text_browser', defaultValue=None)
        except Exception as e2:
            print('Нет данных о настройках')
            print(e2)

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(801, 602)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pathButton = QPushButton(self.centralwidget)
        self.pathButton.setObjectName("pathButton")
        self.horizontalLayout.addWidget(self.pathButton)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pathlabel = QLabel(self.centralwidget)
        self.pathlabel.setText("")
        self.pathlabel.setObjectName("pathlabel")
        self.horizontalLayout.addWidget(self.pathlabel)
        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 4)
        self.time_label = QLabel(self.centralwidget)
        self.time_label.setObjectName("time_label")
        self.gridLayout_2.addWidget(self.time_label, 1, 0, 1, 1)
        spacerItem1 = QSpacerItem(499, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 1, 1, 1, 1)
        self.label_duration = QLabel(self.centralwidget)
        self.label_duration.setObjectName("label_duration")
        self.gridLayout_2.addWidget(self.label_duration, 1, 2, 1, 1)
        self.duration_spinBox = QSpinBox(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.duration_spinBox.setFont(font)
        self.duration_spinBox.setProperty("value", 10)
        self.duration_spinBox.setObjectName("duration_spinBox")
        self.gridLayout_2.addWidget(self.duration_spinBox, 1, 3, 1, 1)
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.pushButtonSave = QPushButton(self.centralwidget)
        self.pushButtonSave.setToolTipDuration(1)
        self.pushButtonSave.setObjectName("pushButtonSave")
        self.gridLayout.addWidget(self.pushButtonSave, 3, 4, 1, 1)
        self.checkBoxShowSorce = QCheckBox(self.centralwidget)
        self.checkBoxShowSorce.setObjectName("checkBoxShowSorce")
        self.gridLayout.addWidget(self.checkBoxShowSorce, 3, 1, 1, 1)
        self.checkBox_translate = QCheckBox(self.centralwidget)
        self.checkBox_translate.setObjectName("checkBox_translate")
        self.gridLayout.addWidget(self.checkBox_translate, 3, 0, 1, 1)
        self.ExitButton = QPushButton(self.centralwidget)
        self.ExitButton.setObjectName("ExitButton")
        self.gridLayout.addWidget(self.ExitButton, 4, 6, 1, 1)
        self.pushButtonRefresh = QPushButton(self.centralwidget)
        self.pushButtonRefresh.setObjectName("pushButtonRefresh")
        self.gridLayout.addWidget(self.pushButtonRefresh, 4, 1, 1, 1)
        spacerItem2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 3, 5, 1, 1)
        self.listenButton = QPushButton(self.centralwidget)
        self.listenButton.setObjectName("listenButton")
        self.gridLayout.addWidget(self.listenButton, 0, 0, 1, 1)
        self.StopButton = QPushButton(self.centralwidget)
        self.StopButton.setObjectName("StopButton")
        self.gridLayout.addWidget(self.StopButton, 0, 2, 1, 1)
        self.pushButtonS2Txt = QPushButton(self.centralwidget)
        self.pushButtonS2Txt.setObjectName("pushButtonS2Txt")
        self.gridLayout.addWidget(self.pushButtonS2Txt, 0, 1, 1, 1)
        self.pushButtonClear = QPushButton(self.centralwidget)
        self.pushButtonClear.setObjectName("pushButtonClear")
        self.gridLayout.addWidget(self.pushButtonClear, 3, 3, 1, 1)
        #self.textfromVoice = QTextBrowser(self.centralwidget)
        self.textfromVoice = QTextEdit(self.centralwidget)
        #self.textfromVoice.setReadOnly(True)
        #self.textfromVoice = QtWidgets(self.centralwidget)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textfromVoice.sizePolicy().hasHeightForWidth())
        self.textfromVoice.setSizePolicy(sizePolicy)
        self.textfromVoice.setObjectName("textfromVoice")
        self.gridLayout.addWidget(self.textfromVoice, 6, 0, 1, 7)
        self.checkBoxOnlyText = QCheckBox(self.centralwidget)
        self.checkBoxOnlyText.setObjectName("checkBoxOnlyText")
        self.gridLayout.addWidget(self.checkBoxOnlyText, 3, 2, 1, 1)
        spacerItem3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem3, 0, 4, 1, 3)
        self.comboBoxLanguage = QComboBox(self.centralwidget)
        self.comboBoxLanguage.setCurrentText("")
        self.comboBoxLanguage.setObjectName("comboBoxLanguage")
        self.gridLayout.addWidget(self.comboBoxLanguage, 0, 3, 1, 2)
        self.pushButtonHint = QPushButton(self.centralwidget)
        self.pushButtonHint.setObjectName("pushButtonHint")
        self.gridLayout.addWidget(self.pushButtonHint, 4, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 2, 0, 1, 4)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)

        self.checkBox_translate.setTristate(False)
        self.checkBoxShowSorce.setTristate(False)
        self.checkBoxOnlyText.setTristate(False)

        self.comboBoxLanguage.addItem("English")
        self.comboBoxLanguage.addItem("Русский")
        self.comboBoxLanguage.setCurrentText("English")

        self.read_thread = ReadThread(self.read_queue)
        self.read_thread.update_signal.connect(self.update_text)
        self.read_thread.finished_signal.connect(self.on_thread_finished)

        self.listener = None

        self.user_init(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Звук в текст"))
        self.pathButton.setText(_translate("MainWindow", "Выбрать путь"))
        self.time_label.setText(_translate("MainWindow", "Время записи"))
        self.label_duration.setText(_translate("MainWindow", "Размер файлов в секундах"))
        self.listenButton.setText(_translate("MainWindow", "Слушать"))
        self.StopButton.setText(_translate("MainWindow", "Остановить"))
        self.ExitButton.setText(_translate("MainWindow", "Выход"))
        self.pushButtonClear.setText(_translate("MainWindow", "Очистить"))
        self.checkBox_translate.setText(_translate("MainWindow", "Переводить"))
        self.checkBoxShowSorce.setText(_translate("MainWindow", "Показывать оригинал текста"))
        self.pushButtonSave.setText(_translate("MainWindow", "Сохранить"))
        self.checkBoxOnlyText.setText(_translate("MainWindow", "Просто текст"))
        self.pushButtonHint.setText(_translate("MainWindow", "Вызвать подсказку"))
        self.pushButtonRefresh.setText(_translate("MainWindow", "Обновить"))
        self.pushButtonS2Txt.setText(_translate("MainWindow", "слова в текст"))

    def fterminate(self):
        self.centralwidget.hide()
        self.stop()
        QApplication.closeAllWindows()  # <- Crashes here, if I comment this app closes but doesnt kill process nor release terminal
        quit()

    def stop(self):
        self.run = False
        self.run_read = False
        self.save_settings()
        self.time_label.setText('Время записи')
        if self.listener:
            self.listener.stop_threads()
        if self.read_thread:
            self.stop_read_thread()
        self.listenButton.setEnabled(True)
        self.pushButtonS2Txt.setEnabled(True)


    def save_to_file(self):
        date_string = datetime.now().strftime("%Y%m%d%H%M%S")
        fn = f'{self.pathlabel.text()}/v2t_{date_string}_{self.count}.Html'
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(self.textfromVoice.toHtml())

    def delete_all_files_in_folder(self, folder_path):
        folder = Path(folder_path)
        for file in folder.glob('*'):  # You can also use '**/*' for recursive deletion
            try:
                if file.is_file():
                    file.unlink()
                    print(f"Deleted: {file}")
                else:
                    print(f"Skipped: {file} (not a file)")
            except Exception as e:
                print(f"Error deleting file {file}: {e}")

    def clear(self):
        self.textfromVoice.clear()
        self.hear_text = ''
        #self.delete_all_files_in_folder(self.pathlabel.text())


    def translate(self, text):
        try:
            translator = GoogleTranslator(source="auto", target="russian")
            translation = translator.translate(text=text)
            # detected_source_language = translator.detect(text).lang
            return translation
        except Exception as rtEx:
            print(rtEx)
            print(text)

    def convert_wav_to_text_offline(self, file_path):
        if self.comboBoxLanguage.currentText() == 'Русский':
            text = yd_recognize(file_path)
            return text
        else:
            recognizer = sr.Recognizer()
            with sr.AudioFile(file_path) as audio_file:
                audio_data = recognizer.record(audio_file)
                try:
                    text = recognizer.recognize_sphinx(audio_data)
                    return text
                except sr.UnknownValueError:
                    print("Sphinx could not understand audio.")
                    return None
                except sr.RequestError as e:
                    print(f"Error with the speech recognition service; {e}")
                    return None

    def split_and_save(self, text):
        output_file = self.pathlabel.text() + '/dict.txt'
        old_words = []
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                old_words = f.read().splitlines()
        words = text.split()
        unique_words = set(words + old_words)
        unique_words_list = list(unique_words)
        unique_words_list.sort()
        with open(output_file, 'w') as file:
            for word in unique_words_list:
                file.write(word + '\n')

    def show_message_dialog(self):
        selected_text = self.textfromVoice.textCursor().selectedText()
        if selected_text:
            # clipboard = QApplication.clipboard()
            # clipboard.setText(selected_text)
            # dialog = gpt_help.ModalForm('Ответы на вопросы', f'Расскажи кратко об {selected_text}')
            # QDialog.Accepted = dialog.exec_()
            # clipboard.setText(f'Расскажи кратко об {selected_text}')
            clipboard.copy(f'Расскажи кратко об {selected_text}')
            print(selected_text)
        else:
            warning_msg = QMessageBox(self)
            warning_msg.setIcon(QMessageBox.Warning)
            warning_msg.setWindowTitle('Внимание')
            warning_msg.setText("Не выделен текст")
            warning_msg.setStandardButtons(QMessageBox.Ok)
            warning_msg.setDefaultButton(QMessageBox.Ok)
            # Show the message box and capture the user's response
            result = warning_msg.exec_()

    def read_queue(self):
        date_string = datetime.now().strftime("%Y%m%d%H%M%S")
        fn = f'{self.pathlabel.text()}/res_{date_string}.txt'
        self.text_browser = f'{self.pathlabel.text()}/beauty_res_{date_string}.txt'
        self.settings.setValue('text_browser', self.text_browser)
        while self.run_read or not self.appQueue.is_empty():
            try:
                self.statusbar.showMessage(datetime.now().strftime("%H:%M:%S"))
                if not self.appQueue.is_empty():
                    id, read_file, st = self.appQueue.dequeue()
                    # self.total_text=f'{self.total_text}\n{read_file}'
                    # self.textfromVoice.append(read_file)
                    tr = self.appQueue.time_record()
                    self.time_label.setText(f'Время записи {tr}')
                    if os.path.exists(read_file):
                        self.total_text = self.convert_wav_to_text_offline(read_file)
                        if self.checkBoxOnlyText.isChecked():
                            #self.hear_text+=self.total_text+' '
                            name_f = os.path.basename(read_file)[0:2]
                            color = "#8B0000" if name_f=='mc' else "#4A44C1"
                            formatted_text = '<span style="font-size:12px;color:%s">%s</span>' % ( color, self.total_text)
                            self.read_thread.update_signal.emit(formatted_text)
                            #self.total_text =
                            with open(self.text_browser, 'a', encoding='utf-8') as f:
                                f.write('<span style="font-size:12px;color:%s">%s</span><br>' % (color,self.total_text) )

                            # self.textfromVoice.append(
                            #          '<span style="font-size:12px;color:%s">%s</span>' % (color,self.total_text))
                            # self.textfromVoice.setText(self.hear_text)
                            # if self.checkBox_translate.isChecked():
                            #     self.textfromVoice.append(
                            #         '<span style="font-size:12px;color:#cc0066">%s</span>' % self.translate(
                            #             self.hear_text))
                        else:
                            if self.checkBoxShowSorce.isChecked():
                                self.textfromVoice.append(
                                    '<span style="font-size:12px;color:#000000">%s</span>' % f'{st} - {self.total_text}')
                                self.split_and_save(self.total_text)
                            if self.checkBox_translate.isChecked():
                                self.textfromVoice.append(
                                    '<span style="font-size:14px;color:#cc0066">%s</span>' % '    ' + self.translate(
                                        self.total_text))
                        self.appQueue.del_file(id, read_file)
                        print (f'удалили файл {read_file}')

                        with open(fn, 'a', encoding='utf-8') as f:
                            f.write(self.total_text+'\n')
                    else:
                        print(f'Не найден файл {read_file}')
                    # os.remove(read_file)
                #time.sleep(self.duration_spinBox.value())
                #print('читатель ok')
            except Exception as e1:
                print(e1)
        self.appQueue.del_off()

    def save_settings_to_db(self, param_name, param_value):
        # Database connection parameters
        # SQL query to insert or update settings
        query_insert = """
        INSERT INTO voise_settings (param_name, param_value)
        VALUES (%s, %s)
        ON CONFLICT (param_name) DO UPDATE SET
            param_value = EXCLUDED.param_value;
        """

        try:
            conn =connect_to_postgres()
            cursor = conn.cursor()
            cursor.execute(query_insert, (param_name, str(param_value)))
            conn.commit()
            print(f'Настройки {param_name} сохранены в базу данных')
        except Exception as e:
            print(f'Ошибка при сохранении настроек {param_name}: {e}')
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()

    def save_settings(self):
        self.settings.setValue('run', self.run)
        self.settings.setValue('run_read', self.run_read)
        self.settings.setValue('val_duration_spinBox', int(self.duration_spinBox.value()))
        self.settings.setValue('val_pathlabel', self.pathlabel.text())
        self.settings.setValue('checkBox_translate', self.checkBox_translate.isChecked())
        self.settings.setValue('checkBoxShowSorce', self.checkBoxShowSorce.isChecked())
        self.settings.setValue('checkBoxOnlyText', self.checkBoxOnlyText.isChecked())
        lang = self.comboBoxLanguage.currentText()
        self.settings.setValue('comboBoxLanguage', lang)
        # file_path = r'voise_settings.yml'
        # settings = {
        #     'run': self.run,
            #     'duration_spinBox': int(self.duration_spinBox.value()),
        #     'pathlabel': self.pathlabel.text(),
        #     'checkBox_translate': self.checkBox_translate.isChecked(),
        #     'checkBoxShowSorce': self.checkBoxShowSorce.isChecked()
        # }
        # with open(file_path, 'w') as file:
        #     yaml.dump(settings, file, default_flow_style=False)
        self.save_settings_to_db('run',self.run);
        self.save_settings_to_db('duration_spinBox', self.duration_spinBox.value());
        self.save_settings_to_db('pathlabel', self.pathlabel.text());
        self.save_settings_to_db('checkBox_translate', self.checkBox_translate.isChecked());
        self.save_settings_to_db('checkBoxShowSorce', self.checkBoxShowSorce.isChecked());
        print('Настройки сохранены')


    def listen_to_files(self):
        if self.run:
            print('Слушатель уже запущен')
            return
        file_path = self.pathlabel.text()
        if file_path == '':
            self.textfromVoice.setText('Необходимо выбрать папку для звуковых файлов')
        if os.path.exists(file_path) == False:
            self.textfromVoice.setText(f'Не существует пути {file_path}')
        self.run = True
        self.save_settings()
        self.listenButton.setEnabled(False)
        self.listener = listen_init()
        self.listener.start_threads()
        #proc = Popen([r"C:\Users\user\PycharmProjects\lifeTRanslater\venv\Scripts\python.exe", r"C:\Users\user\PycharmProjects\lifeTRanslater\voice_to_file.py"])
        print('запущена запись')

    def read_voise_files(self):
        if self.run_read:
            print('Читатель уже запущен')
            return
        file_path = self.pathlabel.text()
        if file_path == '':
            self.textfromVoice.setText('Необходимо выбрать папку для звуковых файлов')
        if os.path.exists(file_path) == False:
            self.textfromVoice.setText(f'Не существует пути {file_path}')
        self.textfromVoice.setText('')
        self.run_read = True
        self.save_settings()
        self.pushButtonS2Txt.setEnabled(False)
        if self.read_thread is None or not self.read_thread.isRunning():
            self.start_read_thread()
        # self.read_thread = threading.Thread(target=self.read_queue)
        # self.read_thread.start()
        print('запущено чтение')


    @pyqtSlot()
    def start_read_thread(self):
        if not self.read_thread.isRunning():
            self.read_thread.start()

    @pyqtSlot()
    def stop_read_thread(self):
        if self.read_thread.isRunning():
            self.read_thread.stop()

    @pyqtSlot(str)  # The slot that receives the string
    def update_text(self, stext):
        self.textfromVoice.append(stext)

    @pyqtSlot()
    def on_thread_finished(self):
        print("Поток перевода звука в текст остановлен")

    def refresh_browser(self):
        if self.text_browser and os.path.exists(self.text_browser):
            with open(self.text_browser, 'r', encoding='utf-8') as f:
                data = f.read()
                self.textfromVoice.setText(data)

    def add_actions(self):
        self.ExitButton.clicked.connect(self.fterminate)
        self.StopButton.clicked.connect(self.stop)
        self.listenButton.clicked.connect(self.listen_to_files)
        self.pathButton.clicked.connect(self.choose_path)
        #self.duration_spinBox.valueChanged.connect(self.save_settings)
        self.pushButtonClear.clicked.connect(self.clear)
        self.pushButtonSave.clicked.connect(self.save_to_file)
        self.pushButtonHint.clicked.connect(self.show_message_dialog)
        self.pushButtonRefresh.clicked.connect(self.refresh_browser)
        self.pushButtonRefresh.clicked.connect(self.refresh_browser)
        self.pushButtonS2Txt.clicked.connect(self.read_voise_files)


    def choose_path(self):
        try:
            options = QFileDialog.Options()
            options |= QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
            folderpath = QFileDialog.getExistingDirectory(self.centralwidget, 'Выберите путь для временных файлов', "",
                                                          options=options)
            self.pathlabel.setText(folderpath)
        except Exception as e:
            print(e)


def start_app():
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    # list_devices()
    # listen_comp_work(20)
    start_app()
