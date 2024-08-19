import sys
from PyQt5.QtWidgets import QApplication

def start_app():
    app = QApplication(sys.argv)
    app.clipboard().setText('12345674')
    # MainWindow = QMainWindow()
    # ui = Ui_MainWindow()
    # ui.setupUi(MainWindow)
    # MainWindow.show()
    # sys.exit(app.exec_())


if __name__ == '__main__':
    # list_devices()
    # listen_comp_work(20)
    app = QApplication(sys.argv)
    QApplication.clipboard().setText('12345674')
    start_app()