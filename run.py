from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import sys
import math
import time
import datetime
import requests
import cv2
import random
from PIL import Image, ImageQt

from ui.mainui import Ui_MainWindow
from ui.login import Ui_Form

from function.login import Login
from function.dummy_function import DummySystem
from function.common_function import *

from script.farm_scipt import OperationThread
from script.login_script import LoginThread


class LoginUi(QMainWindow, Ui_Form):
    def handle_qrcode(self, data):
        self.qrcode = data
        self.display_qrcode()

    def qrcode_success(self, msg):
        self.done()
        pass

    def open(self):
        self.show()

    def done(self):
        print('登录成功')
        self.parent.login_complete(self.login.get_session())
        self.loginthread.terminate()
        self.destroy()

    def select_quick_login(self, data):
        self.login.fast_login(self.account[data.row()])
        self.done()
        pass

    def display_qrcode(self):
        qrcode = Image.fromarray(cv2.cvtColor(self.qrcode, cv2.COLOR_BGR2RGB))
        qrcode = ImageQt.ImageQt(qrcode)
        self.pix = QPixmap.fromImage(qrcode)
        self.item = QGraphicsPixmapItem(self.pix)
        self.scene = QGraphicsScene()
        self.scene.addItem(self.item)
        self.qrcode_view.setScene(self.scene)

    def init(self):
        self.account_table.setEditTriggers(QTableView.NoEditTriggers)
        self.account_table.setColumnCount(2)
        self.account_table.setHorizontalHeaderLabels(['qq', '昵称'])
        self.account_table.verticalHeader().setVisible(False)
        self.account_table.setColumnWidth(0, 120)
        self.account_table.setColumnWidth(1, 250)

        self.login.get_token()
        all_account = self.login.get_logined_account()
        self.account = []
        self.account_table.setRowCount(len(all_account))
        idx = 0
        for key, value in all_account.items():
            self.account.append(key)
            oneItem = QTableWidgetItem(str(value['account']))
            self.account_table.setItem(idx, 0, oneItem)
            oneItem = QTableWidgetItem(str(value['nickname']))
            self.account_table.setItem(idx, 1, oneItem)
            idx += 1

    def __init__(self, parent=None, session=None):
        self.parent = parent
        self.session = session
        super(LoginUi, self).__init__()
        self.setupUi(self)

        self.login = Login(session)
        self.qrcode = None

        self.loginthread = LoginThread(self, self.login)
        self.loginthread.qrcode.connect(self.handle_qrcode)
        self.loginthread.msg.connect(self.qrcode_success)

        load_flag = self.login.load_cookies()
        if load_flag == 0 and self.login.check_load_status() == 0:
            print('文件登录成功')
            self.done()
            return

        self.init()

        self.account_table.itemClicked.connect(self.select_quick_login)

        self.loginthread.start()
        self.open()


class MainThread(QThread):
    statusbar_update = pyqtSignal(list)
    send_data = pyqtSignal(dict)
    serverTimeDelta = 0
    nextOperationTime = 0
    serverTime = 0
    is_pause = False

    def __init__(self, parent=None, session=None):
        super(MainThread, self).__init__(parent)
        self.__session = session

    def statusbar_updator(self):
        self.serverTime = time.time() - self.serverTimeDelta
        statusbar_update = [time.time(), self.serverTime, self.nextOperationTime]
        self.statusbar_update.emit(statusbar_update)

    def update_session(self, data):
        self.__session = data

    def auto_operation(self):
        print('开始自动处理')
        self.nextOperationTime = time.time() + 1200 + random.randint(-300, 300)
        bot = OperationThread(self, self.dummy)
        bot.completeMsg.connect(self.auto_operation_complete)
        bot.start()

    def auto_operation_complete(self):
        print('自动处理完成')

    def run(self):
        self.dummy = DummySystem(self.__session)
        while True:
            code = self.dummy.get_farm_info()
            statcode = self.dummy.get_nickname()
            if code == 0 and statcode == 0:
                break
            else:
                print('信息获取失败，20秒后重试')
                time.sleep(20)
        self.data = self.dummy.data
        self.serverTimeDelta = self.dummy.serverTimeDelta
        self.nextOperationTime = time.time() - 1000
        self.dummy.simulate()
        while True:
            if self.is_pause == False:
                self.statusbar_updator()
                if time.time() > self.nextOperationTime:
                    self.dummy.get_farm_info()
                    self.dummy.simulate()
                    self.data = self.dummy.data
                    self.auto_operation()
                else:
                    self.dummy.simulate()
                self.send_data.emit(self.data)
            time.sleep(0.5)


class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))
        QApplication.processEvents()


class MainUi(QMainWindow, Ui_MainWindow):
    def init_ui(self):
        # 右侧label块
        sequence = [25, 19, 13, 7, 1, 26, 20, 14, 8, 2, 27, 21, 15, 9, 3, 28, 22, 16, 10, 4, 29, 23, 17, 11, 5, 30, 24,
                    18, 12, 6]
        labels = ['crop', 'season', 'timestamp', 'operation']

        self.farm_land_table.setEditTriggers(QTableView.NoEditTriggers)
        self.farm_land_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.farm_land_table.setRowCount(6)
        self.farm_land_table.setColumnCount(5)
        self.farm_land_table.horizontalHeader().setVisible(False)
        self.farm_land_table.verticalHeader().setVisible(False)

        self.farm_land_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.farm_land_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for it, value in enumerate(sequence):
            oneItem = QTableWidgetItem(f'土地{value}')
            oneItem.setTextAlignment(Qt.AlignHCenter)

            self.farm_land_table.setItem(it // 5, it % 5, oneItem)

        # 下方status_bar
        self.nowtime_title = QLabel()
        self.nowtime_title.setText('当前时间：')
        self.nowtime_content = QLabel()
        self.nowtime_content.setText(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.statusbar.addWidget(self.nowtime_title)
        self.statusbar.addWidget(self.nowtime_content)

        self.servertime_title = QLabel()
        self.servertime_title.setText('服务器时间：')
        self.servertime_content = QLabel()
        self.servertime_content.setText(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.statusbar.addWidget(self.servertime_title)
        self.statusbar.addWidget(self.servertime_content)

        self.nexttime_title = QLabel()
        self.nexttime_title.setText('下次更新时间：')
        self.nexttime_content = QLabel()
        self.nexttime_content.setText(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.statusbar.addWidget(self.nexttime_title)
        self.statusbar.addWidget(self.nexttime_content)

        # 上方menu_bar
        self.actionLogin.triggered.connect(self.show_login)

        # 功能按键
        self.fn_refresh.clicked.connect(self.fn_refreshinfo)
        self.wishtree_refresh_wish.clicked.connect(self.fn_wishtree_refresh_wish)
        self.wishtree_submit_wish.clicked.connect(self.fn_wishtree_submit_wish)

    def show_login(self):
        self.session = requests.Session()
        self.mainthread.terminate()
        self.login_window = LoginUi(self, self.session)

    def login_complete(self, session):
        self.mainthread.update_session(session)
        self.mainthread.start()

    def console_writer(self, text):
        if text != '\n':
            text = '[%s]：%s' % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), text)
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()

    def handle_statusbar(self, data):
        self.nowtime_content.setText(time.strftime("%Y-%m-%d %H:%M:%S     ", time.localtime(data[0])))
        self.servertime_content.setText(time.strftime("%Y-%m-%d %H:%M:%S     ", time.localtime(data[1])))
        self.nexttime_content.setText(time.strftime("%Y-%m-%d %H:%M:%S     ", time.localtime(data[2])))

    def format_time(self, seconds):
        seconds = int(seconds)
        symbol = '+'
        if seconds < 0:
            symbol = '-'
            seconds *= -1
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return '%s%02d:%02d:%02d' % (symbol, h, m, s)

    def display_land_info(self):
        sequence = [4, 3, 2, 9, 8, 7, 14, 13, 12, 19, 18, 17, 24, 23, 22, 29, 28, 27, 1, 6, 11, 16, 21, 26, 0, 5, 10,
                    15, 20, 25]
        land_level = [{'desc': '普', 'back': '#FFFFFF', 'backstyle': Qt.SolidPattern, 'fore': '#000000'},
                      {'desc': '红', 'back': '#FFCCCC', 'backstyle': Qt.SolidPattern, 'fore': '#000000'},
                      {'desc': '黑', 'back': '#DEDEDE', 'backstyle': Qt.SolidPattern, 'fore': '#000000'},
                      {'desc': '金', 'back': '#FFFFCC', 'backstyle': Qt.SolidPattern, 'fore': '#000000'},
                      {'desc': '紫晶', 'back': '#FFCCE6', 'backstyle': Qt.Dense2Pattern, 'fore': '#000000'},
                      {'desc': '蓝晶', 'back': '#CCE6FF', 'backstyle': Qt.Dense2Pattern, 'fore': '#000000'},
                      {'desc': '黑晶', 'back': '#DEDEDE', 'backstyle': Qt.Dense2Pattern, 'fore': '#000000'}]
        for it, value in enumerate(self.data['land_info'][:30]):
            if value['crop_id'] == 0:
                oneItem = QTableWidgetItem("空地")
            else:
                name = value['crop_name']
                status = value['crop_status_name']
                remained = self.format_time(self.mainthread.serverTime - value['target_time'])
                op = []
                if value['weed']:
                    op.append('除草')
                if value['pest']:
                    op.append('除虫')
                if value['water']:
                    op.append('浇水')
                if len(op) == 0:
                    op = '无需操作'
                else:
                    op = '需要' + '、'.join(op)
                oneItem = QTableWidgetItem(f"{name}\n"
                                           f"{status}[第{value['now_season']}/{value['total_season']}季]\n"
                                           f"{remained}\n"
                                           f"{op}")
            oneItem.setTextAlignment(Qt.AlignHCenter)
            brush = QBrush(QColor(land_level[value['land_level']]['back']))
            brush.setStyle(land_level[value['land_level']]['backstyle'])
            oneItem.setBackground(brush)
            oneItem.setForeground(QColor(land_level[value['land_level']]['fore']))

            self.farm_land_table.setItem(sequence[it] // 5, sequence[it] % 5, oneItem)

    def display_basic_info(self):
        self.username_val.setText(str(self.data['basic_info']['nickname']))
        self.gold_val.setText(str(self.data['basic_info']['money']))
        self.money_val.setText(str(self.data['basic_info']['coupon']))
        self.level_val.setText(str(self.data['basic_info']['level']))
        self.exp_val.setText('%d/%d' %
                             (self.data['basic_info']['real_exp'], self.data['basic_info']['level'] * 200 + 200))
        self.exp_progress.setValue(self.data['basic_info']['exp_percent'])
        self.dog_val.setText(self.data['basic_info']['dog_name'])
        self.dogfood_val.setText('%d小时' % self.data['basic_info']['dogfood'])

    def display_rank_info(self):
        self.farm_score_val.setText(str(self.data['rank_info']['score']))
        self.farm_rank_val.setText(self.data['rank_info']['level_desc'])

    def display_essence_info(self):
        self.essence_num_val.setText(str(self.data['essence_info']['num']))
        self.essence_countdown_val.setText(self.format_time(self.mainthread.serverTime
                                                            - self.data['essence_info']['slot'][0]['timestamp']))

    def display_bag_info(self):
        row_count = len(self.data['bag_info']['crop'])

        self.farm_bag_seed.setEditTriggers(QTableView.NoEditTriggers)
        self.farm_bag_seed.setColumnCount(5)
        self.farm_bag_seed.setHorizontalHeaderLabels(['名称', '数量', '已收获', '等级', '种植总时间'])
        self.farm_bag_seed.verticalHeader().setVisible(False)
        self.farm_bag_seed.setRowCount(row_count)

        col_index = ['cName', 'amount', 'harvestNumber', 'level', 'lifecycle']
        idx = 0
        for key, value in self.data['bag_info']['crop'].items():
            for it, col in enumerate(col_index):
                oneItem = QTableWidgetItem(str(value[col]))
                self.farm_bag_seed.setItem(idx, it, oneItem)
            idx += 1

        row_count = len(self.data['bag_info']['item'])

        self.farm_bag_item.setEditTriggers(QTableView.NoEditTriggers)
        self.farm_bag_item.setColumnCount(3)
        self.farm_bag_item.setHorizontalHeaderLabels(['名称', '数量', '描述'])
        self.farm_bag_item.verticalHeader().setVisible(False)
        self.farm_bag_item.setRowCount(row_count)

        idx = 0
        for key, value in self.data['bag_info']['item'].items():
            if value['type'] in [3, 10, 24]:
                oneItem = QTableWidgetItem(str(value['tName']))
                self.farm_bag_item.setItem(idx, 0, oneItem)
                oneItem = QTableWidgetItem(str(value['amount']))
                self.farm_bag_item.setItem(idx, 1, oneItem)
                oneItem = QTableWidgetItem(str(value['depict']))
                self.farm_bag_item.setItem(idx, 2, oneItem)
            else:
                oneItem = QTableWidgetItem(str(value['name']))
                self.farm_bag_item.setItem(idx, 0, oneItem)
                oneItem = QTableWidgetItem(str(value['num']))
                self.farm_bag_item.setItem(idx, 1, oneItem)
                oneItem = QTableWidgetItem(str(value['desc']))
                self.farm_bag_item.setItem(idx, 2, oneItem)
            idx += 1

        row_count = len(self.data['bag_info']['fish'])

        self.farm_bag_fish.setEditTriggers(QTableView.NoEditTriggers)
        self.farm_bag_fish.setColumnCount(2)
        self.farm_bag_fish.setHorizontalHeaderLabels(['名称', '数量'])
        self.farm_bag_fish.verticalHeader().setVisible(False)
        self.farm_bag_fish.setRowCount(row_count)

        col_index = ['tName', 'amount']
        idx = 0
        for key, value in self.data['bag_info']['fish'].items():
            for it, col in enumerate(col_index):
                oneItem = QTableWidgetItem(str(value[col]))
                self.farm_bag_fish.setItem(idx, it, oneItem)
            idx += 1

    def display_hive_info(self):
        remained = self.format_time(self.mainthread.serverTime - self.data['hive_info']['target_time'])
        self.hive_level_val.setText(str(self.data['hive_info']['level']))
        self.hive_jelly_val.setText(str(self.data['hive_info']['jelly']))
        self.hive_honey_val.setText(str(self.data['hive_info']['honey']))
        self.hive_pollen_val.setText('%d+%d' % (self.data['hive_info']['free_pollen'], self.data['hive_info']['pay_pollen']))
        self.hive_status_val.setText('工作中' if self.data['hive_info']['status'] == 1 else '休息中')
        self.hive_countdown_val.setText(remained)

    def display_wishtree_info(self):
        star_remained = self.format_time(self.mainthread.serverTime - self.data['wishtree_info']['star_timestamp'] - 28800)
        wish_remained = self.format_time(self.mainthread.serverTime - self.data['wishtree_info']['wish_timestamp'])
        self.wishtree_level_val.setText(
            '%d(%d)' % (self.data['wishtree_info']['level'], self.data['wishtree_info']['wish_level']))
        self.wishtree_star_countdown_val.setText(star_remained)
        self.wishtree_wish_countdown_val.setText(wish_remained)
        wishtree_wish = [self.wishtree_wish1, self.wishtree_wish2, self.wishtree_wish3, self.wishtree_wish4]
        if not self.wishtree_refresh_wish.isEnabled() and self.data['wishtree_info']['wish_status'] == 0:
            self.wishtree_refresh_wish.setEnabled(True)
            self.wishtree_submit_wish.setEnabled(True)
            for each_checkbox in wishtree_wish:
                each_checkbox.setEnabled(True)
                each_checkbox.setChecked(False)
        elif self.wishtree_refresh_wish.isEnabled() and self.data['wishtree_info']['wish_status'] != 0:
            self.wishtree_refresh_wish.setEnabled(False)
            self.wishtree_submit_wish.setEnabled(False)
            for each_checkbox in wishtree_wish:
                each_checkbox.setEnabled(False)
                each_checkbox.setText('')
        for it, value in enumerate(self.data['wishtree_info']['wish_item']):
            if self.data['wishtree_info']['wish_status'] != 0:
                wishtree_wish[it].setChecked(True)
            wishtree_wish[it].setText('%sx%d' % (value['name'], value['num']))

    def display_marine_info(self):
        self.marine_lv_val.setText(str(self.data['marine_info']['level']))
        self.marine_coin_val.setText(str(self.data['marine_info']['coin']))
        self.marine_exp_val.setText(str(self.data['marine_info']['exp']))
        self.marine_fuel_val.setText(str(self.data['marine_info']['oil']))
        self.marine_unlock_val.setText(str(self.data['marine_info']['unlock_area']))

        self.marine_list.setEditTriggers(QTableView.NoEditTriggers)
        self.marine_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.marine_list.setColumnCount(7)
        self.marine_list.setHorizontalHeaderLabels(['名称', '等级', '经验', '深度', '状态', '探索区域', '倒计时'])
        self.marine_list.setRowCount(len(self.data['marine_info']['marine']))

        status_remapper = {0: '空闲', 1: '探险中', 2: '返回中'}

        col_index = ['name', 'level', 'exp', 'depth', 'status_trans', 'areaid', 'timestamp_trans']
        for it, val in enumerate(self.data['marine_info']['marine']):
            self.data['marine_info']['marine'][it]['status_trans'] = \
                status_remapper[self.data['marine_info']['marine'][it]['status']]
            if self.data['marine_info']['marine'][it]['timestamp'] < int(time.time()):
                self.data['marine_info']['marine'][it]['status_trans'] += '（已完成）'
            self.data['marine_info']['marine'][it]['timestamp_trans'] = \
                self.format_time(self.mainthread.serverTime - self.data['marine_info']['marine'][it]['timestamp'])
            for idx, col in enumerate(col_index):
                oneItem = QTableWidgetItem(str(self.data['marine_info']['marine'][it][col]))
                self.marine_list.setItem(it, idx, oneItem)

        self.marine_order.setEditTriggers(QTableView.NoEditTriggers)
        self.marine_order.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.marine_order.setColumnCount(5)
        self.marine_order.setHorizontalHeaderLabels(['金币', '经验', '需求物品', '倒计时', '状态'])
        self.marine_order.setRowCount(len(self.data['marine_info']['order']))

        col_index = ['coin', 'exp', 'items', 'timestamp']
        for it, val in enumerate(self.data['marine_info']['order']):
            self.data['marine_info']['order'][it]['timestamp_trans'] = \
                self.format_time(self.mainthread.serverTime - self.data['marine_info']['order'][it]['timestamp'])
            for idx, col in enumerate(col_index):
                oneItem = QTableWidgetItem(str(self.data['marine_info']['order'][it][col]))
                self.marine_order.setItem(it, idx, oneItem)
            oneItem = QTableWidgetItem(
                '就绪' if self.data['marine_info']['order'][it]['timestamp'] < int(time.time()) else '等待')
            self.marine_order.setItem(it, len(col_index), oneItem)

    def handle_data(self, data):
        self.data = data.copy()

        self.display_land_info()
        self.display_basic_info()
        self.display_rank_info()
        self.display_essence_info()
        self.display_bag_info()
        self.display_hive_info()
        self.display_wishtree_info()
        self.display_marine_info()

    def fn_refreshinfo(self):
        self.mainthread.is_pause = True
        self.mainthread.dummy.get_farm_info()
        self.mainthread.dummy.simulate()
        self.mainthread.is_pause = False

    def fn_wishtree_refresh_wish(self):
        self.mainthread.dummy.get_wishtree()

    def fn_wishtree_submit_wish(self):
        item_list = []
        if self.wishtree_wish1.isChecked():
            item_list.append(self.data['wishtree_info']['wish_item'][0]['id'])
        if self.wishtree_wish2.isChecked():
            item_list.append(self.data['wishtree_info']['wish_item'][1]['id'])
        if self.wishtree_wish3.isChecked():
            item_list.append(self.data['wishtree_info']['wish_item'][2]['id'])
        if self.wishtree_wish4.isChecked():
            item_list.append(self.data['wishtree_info']['wish_item'][3]['id'])
        available = min(3, (self.data['wishtree_info']['wish_level'] + 1) // 2)
        if len(item_list) != available:
            print('[%s]：提交愿望错误，请选择%d个物品' % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), available))
        else:
            response = self.mainthread.dummy.wishtree_new_wish(item_list)

    def __init__(self, parent=None):
        super(MainUi, self).__init__(parent)
        self.setupUi(self)
        self.init_ui()

        self.session = requests.Session()
        self.mainthread = MainThread(self, self.session)

        self.mainthread.statusbar_update.connect(self.handle_statusbar)
        self.mainthread.send_data.connect(self.handle_data)
        sys.stdout = Stream(newText=self.console_writer)

        # self.mainthread.start()


def run():
    app = QApplication(sys.argv)
    main = MainUi()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
