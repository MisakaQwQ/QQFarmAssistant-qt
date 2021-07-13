from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import time
import random


class OperationThread(QThread):
    completeMsg = pyqtSignal(str)

    def __init__(self, parent=None, bot=None):
        super(OperationThread, self).__init__(parent)
        self.__dummy = bot
        self.parent = parent

    def get_next_seed(self, id):
        if 0 <= id <= 2:
            # 柔紫千红
            return 747
        elif 3 <= id <= 5:
            # 月宴
            return 966
        elif 6 <= id <= 7:
            # 荷花玉兰
            return 1060
        elif 20 <= id <= 23:
            # 荷花玉兰
            return 40
        else:
            return -1

    def auto_opt(self):
        # 种地
        for it, value in enumerate(self.__dummy.data['land_info']):
            if self.__dummy.data['land_info'][it]['weed']:
                self.__dummy.farm_opt(it, 'clearWeed')
                time.sleep(random.randint(1, 3))
            if self.__dummy.data['land_info'][it]['pest']:
                self.__dummy.farm_opt(it, 'spraying')
                time.sleep(random.randint(1, 3))
            if self.__dummy.data['land_info'][it]['water']:
                self.__dummy.farm_opt(it, 'water')
                time.sleep(random.randint(1, 3))
            if self.__dummy.data['land_info'][it]['crop_status'] == 6:
                self.__dummy.farm_plant_operation(it, 'harvest')
                time.sleep(random.randint(1, 3))
            if self.__dummy.data['land_info'][it]['crop_status'] == 7:
                self.__dummy.farm_plant_operation(it, 'scarify')
                time.sleep(random.randint(1, 3))
            if self.__dummy.data['land_info'][it]['crop_status'] == 0:
                next_crop = self.get_next_seed(it)
                if next_crop == -1:
                    continue
                if next_crop not in self.__dummy.data['bag_info']['crop'].keys() \
                        or self.__dummy.data['bag_info']['crop'][next_crop]['amount'] == 0:
                    self.__dummy.buy_seed(next_crop)
                    time.sleep(random.randint(1, 3))
                self.__dummy.farm_plant_operation(it, 'planting', next_crop)
                time.sleep(random.randint(1, 3))

    def rank_draw(self):
        if False and self.__dummy.data['rank_info']['reward']:
            self.__dummy.rank_draw()

    def essence_opt(self):
        if self.__dummy.data['essence_info']['slot'][0]['timestamp'] != 0 \
                and self.__dummy.data['essence_info']['slot'][0]['timestamp'] < self.parent.serverTime:
            self.__dummy.essence_harvest(1)
        if self.__dummy.data['essence_info']['slot'][0]['timestamp'] == 0 \
                and 4472 in self.__dummy.data['bag_info']['crop'].keys() \
                and self.__dummy.data['bag_info']['crop'][4472]['amount'] > 0:
            self.__dummy.essence_plant(1, 4472)

    def hive_opt(self):
        if self.__dummy.data['hive_info']['target_time'] < self.parent.serverTime:
            if self.__dummy.data['hive_info']['status'] == 1:
                self.__dummy.hive_harvest()
            elif self.__dummy.data['hive_info']['status'] == 2:
                self.__dummy.hive_work()
            time.sleep(random.randint(1, 3))

    def wishtree_opt(self):
        if self.__dummy.data['wishtree_info']['star_timestamp'] + 28800 < self.parent.serverTime:
            if len(self.__dummy.data['wishtree_info']['star_list']) == 10:
                print('摘星失败，今日已摘完')
            else:
                starid = random.randint(1, 10)
                while starid in self.__dummy.data['wishtree_info']['star_list']:
                    starid = random.randint(1, 10)
                self.__dummy.wishtree_star(starid)
                time.sleep(random.randint(1, 3))
        if self.__dummy.data['wishtree_info']['wish_timestamp'] < self.parent.serverTime:
            if self.__dummy.data['wishtree_info']['wish_count'] < 10:
                if self.__dummy.data['wishtree_info']['wish_today_count'] < 10:
                    if self.__dummy.data['wishtree_info']['wish_status'] in [2, 3]:
                        self.__dummy.wishtree_wish()
                    else:
                        print('当前状态不能许愿')
                else:
                    print('今日许愿已满10次')
            else:
                self.__dummy.wishtree_wish_harvest()
            time.sleep(random.randint(1, 3))

    def marine_opt(self):
        for it, value in enumerate(self.__dummy.data['marine_info']['marine']):
            if self.__dummy.data['marine_info']['marine'][it]['timestamp'] < self.parent.serverTime:
                if self.__dummy.data['marine_info']['marine'][it]['status'] == 2:
                    self.__dummy.marine_harvest(it + 1)
                if self.__dummy.data['marine_info']['marine'][it]['status'] == 0:
                    if it == 0:
                        self.__dummy.marine_go(it + 1, 3)
                    elif 0 and it == 1:
                        self.__dummy.marine_go(it + 1, 1)
                    elif it == 2:
                        self.__dummy.marine_go(it + 1, 5)
                elif self.__dummy.data['marine_info']['marine'][it]['status'] == 1:
                    self.__dummy.marine_draw(it + 1)

    def farm2_opt(self):
        self.hive_opt()
        self.wishtree_opt()
        self.rank_draw()
        self.essence_opt()
        self.marine_opt()

    def run(self):
        self.auto_opt()
        self.farm2_opt()
        self.completeMsg.emit('Success')
