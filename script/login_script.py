from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import numpy as np
import time


class LoginThread(QThread):
    qrcode = pyqtSignal(np.ndarray)
    msg = pyqtSignal(str)

    def __init__(self, parent=None, login=None):
        self.status = True
        super(LoginThread, self).__init__(parent)
        self.login = login

    def run(self):
        qrcode = self.login.qrcode_login_get_image()
        while self.status:
            code, msg = self.login.qrcode_login_get_status()
            if code == '0':
                self.msg.emit('Success')
                self.status = False
            elif code == '65':
                qrcode = self.login.qrcode_login_get_image()
            self.qrcode.emit(qrcode)
            time.sleep(2)

