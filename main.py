import pyaudio
import wave
import sounddevice
from scipy.io.wavfile import write
import sys
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QApplication
from PyQt5.QtCore import QSettings, QMetaObject,QCoreApplication
import os
import threading
from datetime import datetime
import time
import speech_recognition as sr
import yaml
from subprocess import Popen, PIPE
import sqlite3
from deep_translator import GoogleTranslator, LingueeTranslator, PonsTranslator

class Queue:

    def __init__(self):
        self.connection = sqlite3.connect("voise_data.db", check_same_thread=False)

    def is_empty(self):
        try:
            self.cursor = self.connection.cursor()
            self.cursor.execute("select count(*) FROM files_queue")
            count = self.cursor.fetchone()[0]
            self.cursor.close()
            return count == 0
        except Exception as e:
            if str(e).find('no such table: files_queue')>-1:
                print(f"count=err")
                return True
            else:
                raise

    def time_record(self):
        self.cursor = self.connection.cursor()
        self.cursor.execute("select time_record FROM time_record")
        tr = self.cursor.fetchone()[0]
        self.cursor.close()
        return tr

    def enqueue(self, item):
        #self.items.append(item)
        pass


    def dequeue(self):
        try:
            self.cursor = self.connection.cursor()
            self.cursor.execute("select id, name, start_time FROM files_queue ORDER BY id LIMIT 1")
            self.cur_id, self.cur_file, self.start_time =self.cursor.fetchone()
            self.cursor.execute(f"delete FROM files_queue where id={self.cur_id}")
            self.connection.commit()
            self.cursor.close()
            return (self.cur_id, self.cur_file, self.start_time)
        except Exception as err:
            print(err)
            raise

    def del_off(self):
        self.cursor = self.connection.cursor()
        self.cursor.execute("select id, name FROM files_queue")
        data = self.cursor.fetchall()
        for rec in data:
            if os.path.exists(rec[1]):
                os.remove(rec[1])
        self.cursor.execute(f"delete FROM files_queue")
        self.connection.commit()
        self.cursor.close()


class Ui_MainWindow(object):
    run = False
    count = 0
    appQueue = Queue()
    total_text = ''

    def user_init(self,MainWindow):
        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)
        self.add_actions()
        self.settings = QSettings('jarik', 'RealVoise')
        try:
            data1 = self.settings.value('val_pathlabel', defaultValue='')
            data2 = self.settings.value('val_duration_spinBox', defaultValue='10')
            self.checkBox_translate.setCheckState(self.settings.value('checkBox_translate', defaultValue=2))
            self.checkBoxShowSorce.setCheckState(self.settings.value('checkBoxShowSorce', defaultValue=2))
            self.pathlabel.setText(data1)
            self.duration_spinBox.setValue(int(data2))
        except Exception as e2:
            print('Нет данных о настройках')
            print(e2)

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(801, 602)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pathButton = QtWidgets.QPushButton(self.centralwidget)
        self.pathButton.setObjectName("pathButton")
        self.horizontalLayout.addWidget(self.pathButton)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pathlabel = QtWidgets.QLabel(self.centralwidget)
        self.pathlabel.setText("")
        self.pathlabel.setObjectName("pathlabel")
        self.horizontalLayout.addWidget(self.pathlabel)
        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 4)
        self.time_label = QtWidgets.QLabel(self.centralwidget)
        self.time_label.setObjectName("time_label")
        self.gridLayout_2.addWidget(self.time_label, 1, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(499, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 1, 1, 1, 1)
        self.label_duration = QtWidgets.QLabel(self.centralwidget)
        self.label_duration.setObjectName("label_duration")
        self.gridLayout_2.addWidget(self.label_duration, 1, 2, 1, 1)
        self.duration_spinBox = QtWidgets.QSpinBox(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.duration_spinBox.setFont(font)
        self.duration_spinBox.setProperty("value", 10)
        self.duration_spinBox.setObjectName("duration_spinBox")
        self.gridLayout_2.addWidget(self.duration_spinBox, 1, 3, 1, 1)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.listenButton = QtWidgets.QPushButton(self.centralwidget)
        self.listenButton.setObjectName("listenButton")
        self.gridLayout.addWidget(self.listenButton, 0, 0, 1, 1)
        self.StopButton = QtWidgets.QPushButton(self.centralwidget)
        self.StopButton.setObjectName("StopButton")
        self.gridLayout.addWidget(self.StopButton, 0, 1, 1, 1)
        self.ExitButton = QtWidgets.QPushButton(self.centralwidget)
        self.ExitButton.setObjectName("ExitButton")
        self.gridLayout.addWidget(self.ExitButton, 0, 5, 1, 1)
        self.pushButtonClear = QtWidgets.QPushButton(self.centralwidget)
        self.pushButtonClear.setObjectName("pushButtonClear")
        self.gridLayout.addWidget(self.pushButtonClear, 1, 2, 1, 1)
        self.checkBox_translate = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_translate.setTristate(False)
        self.checkBox_translate.setObjectName("checkBox_translate")
        self.gridLayout.addWidget(self.checkBox_translate, 1, 0, 1, 1)
        self.checkBoxShowSorce = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBoxShowSorce.setObjectName("checkBoxShowSorce")
        self.checkBoxShowSorce.setTristate(False)
        self.gridLayout.addWidget(self.checkBoxShowSorce, 1, 1, 1, 1)
        self.pushButtonSave = QtWidgets.QPushButton(self.centralwidget)
        self.pushButtonSave.setToolTipDuration(1)
        self.pushButtonSave.setObjectName("pushButtonSave")
        self.gridLayout.addWidget(self.pushButtonSave, 1, 3, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 0, 2, 1, 3)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem3, 1, 4, 1, 2)
        self.textfromVoice = QtWidgets.QTextBrowser(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textfromVoice.sizePolicy().hasHeightForWidth())
        self.textfromVoice.setSizePolicy(sizePolicy)
        self.textfromVoice.setObjectName("textfromVoice")
        self.gridLayout.addWidget(self.textfromVoice, 3, 0, 1, 6)
        self.gridLayout_2.addLayout(self.gridLayout, 2, 0, 1, 4)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)

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

    def fterminate(self):
        self.centralwidget.hide()
        self.stop()
        QApplication.closeAllWindows()  # <- Crashes here, if I comment this app closes but doesnt kill process nor release terminal
        quit()



    def stop(self):
        self.run = False
        self.save_settings()
        self.time_label.setText('Время записи')
        self.clear()

    def save_to_file(self):
        date_string = datetime.now().strftime("%Y%m%d%H%M%S")
        fn =  f'{self.pathlabel.text()}/v2t_{date_string}_{self.count}.Html'
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(self.textfromVoice.toHtml())

    def clear(self):
        self.textfromVoice.clear()

    def translate(self, text):
        try:
            translator = GoogleTranslator(source="auto", target="russian")
            translation = translator.translate(text=text)
            #detected_source_language = translator.detect(text).lang
            return translation
        except Exception as rtEx:
            print(rtEx)
            print(text)

    def convert_wav_to_text_offline(self, file_path):
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
        output_file = self.pathlabel.text()+'/dict.txt'
        old_words = []
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                old_words = f.read().splitlines()
        words = text.split()
        unique_words = set(words+old_words)
        unique_words_list = list(unique_words)
        unique_words_list.sort()
        with open(output_file, 'w') as file:
            for word in unique_words_list:
                file.write(word + '\n')

                
    def read_queue(self):
        while self.run:
            try:
                self.statusbar.showMessage(datetime.now().strftime("%H:%M:%S"))
                if not self.appQueue.is_empty():
                    id, read_file, st = self.appQueue.dequeue()
                    #self.total_text=f'{self.total_text}\n{read_file}'
                    #self.textfromVoice.append(read_file)
                    tr = self.appQueue.time_record()
                    self.time_label.setText(f'Время записи {tr}')
                    if os.path.exists(read_file):
                        self.total_text = self.convert_wav_to_text_offline(read_file)
                        if self.checkBoxShowSorce.isChecked():
                            self.textfromVoice.append('<span style="font-size:12px;color:#000000">%s</span>' % f'{st} - {self.total_text}')
                            self.split_and_save(self.total_text)
                        if self.checkBox_translate.isChecked():
                            self.textfromVoice.append('<span style="font-size:14px;color:#cc0066">%s</span>' % '    '+self.translate(self.total_text))
                        os.remove(read_file)
                    else:
                        print(f'Не найден файл {read_file}')
                    #os.remove(read_file)
            except Exception as e1:
                print(e1)
        self.appQueue.del_off()

    def save_settings(self):
        file_path = r'voise_settings.yml'
        settings = {
            'run': self.run,
            'duration_spinBox': int(self.duration_spinBox.value()),
            'pathlabel': self.pathlabel.text(),
            'checkBox_translate': self.checkBox_translate.isChecked(),
            'checkBoxShowSorce': self.checkBoxShowSorce.isChecked()
        }
        with open(file_path, 'w') as file:
            yaml.dump(settings, file, default_flow_style=False)

    def listen_to_files(self):
        if self.run:
            print ('Слушатель уже запущен')
            return
        self.settings.setValue('val_pathlabel', self.pathlabel.text())
        self.settings.setValue('val_duration_spinBox', str(self.duration_spinBox.value()))
        file_path = self.pathlabel.text()
        if file_path == '':
             self.textfromVoice.setText('Необходимо выбрать папку для звуковых файлов')
        if os.path.exists(file_path) == False:
             self.textfromVoice.setText(f'Не существует пути {file_path}')
        self.textfromVoice.setText('')
        self.run = True
        self.save_settings( )
        proc = Popen([r"C:\Users\user\PycharmProjects\lifeTRanslater\venv\Scripts\python.exe", "voice_to_file.py"])
        print('запущена запись')
        read_thread = threading.Thread(target=self.read_queue)
        read_thread.start()
        print('запущено чтение')


    def add_actions(self):
        self.ExitButton.clicked.connect(self.fterminate)
        self.StopButton.clicked.connect(self.stop)
        self.listenButton.clicked.connect(self.listen_to_files)
        self.pathButton.clicked.connect(self.choose_path)
        self.duration_spinBox.valueChanged.connect(self.save_settings)
        self.pushButtonClear.clicked.connect(self.clear)
        self.pushButtonSave.clicked.connect(self.save_to_file)

    def choose_path(self):
        try:
            options = QFileDialog.Options()
            options |= QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
            folderpath = QFileDialog.getExistingDirectory(self.centralwidget, 'Выберите путь для временных файлов', "", options=options)
            self.pathlabel.setText(folderpath)
        except Exception as e:
            print(e)

def start_app():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    #list_devices()
    #listen_comp_work(20)
    start_app()


