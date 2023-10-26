import requests
import re
import json
from xml.dom.minidom import parse
import tempfile
import os
import copy

from function.login import Login
from function.farm_item_const import *
from function.common_function import *


class DummySystem:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/87.0.4280.141 Safari/537.36 ',
        'origin': 'https://appimg.qq.com'
    }
    data = None

    def get_data(self):
        return copy.deepcopy(self.data)

    def generate_form(self, para=None):
        if para is None:
            para = {}
        farmTime, farmKey, farmKey2 = generate_farmkey()
        form = {
            'farmTime': farmTime,
            'uIdx': self.data['basic_info']['uId'],
            'uinY': self.data['basic_info']['uin'],
            'farmKey2': farmKey2,
            'farmKey': farmKey,
        }
        for key, value in para.items():
            form[key] = value
        return form

    def http_post_request(self, url, form, name, checkMode=0):
        retry_cnt = 0
        code = -1
        print('%s http请求中' % name)
        while retry_cnt < 5:
            try:
                response = self.__session.post(url, data=form, headers=self.headers, timeout=5)
            except requests.exceptions.RequestException as e:
                print('请求失败，网络连接超时')
                time.sleep(3)
                retry_cnt += 1
                continue
            if response.status_code == 200:
                data = json.loads(response.text)
                if checkMode == 2:
                    if type(data) == dict and 'code' in data.keys() and data['code'] == 0:
                        print('请求失败，服务器错误：%s' % (data['direction']))
                        time.sleep(3)
                    else:
                        return 0, data
                if checkMode == 0 and data['ecode'] == 0:
                    return 0, data
                elif checkMode == 1 and 'code' in data.keys() and data['code'] == 1:
                    return 0, data
                else:
                    print('请求失败，服务器错误：%s' % (data['direction']))
                    time.sleep(3)
            else:
                print('请求失败，状态码%d' % response.status_code)
                time.sleep(3)
            retry_cnt += 1
        return -1, None

    def get_item_name(self, type, itemId):
        type = str(type)
        itemId = str(itemId)
        if itemId == '9001':
            return '狗粮'
        if type == '4':
            return '农场狗'
        if type == '83':
            return '蜂蜜'
        if type == '2':
            return '装饰'
        if type == '30':
            return '经验'
        if type == '6':
            return '金币'
        if type == '39':
            return '点券'
        if type == '113':
            return '深海金币'
        if type == '89':
            return self.other_data['fish_info'][itemId]['crop_name'] + '碎片'
        if type == '88':
            return '珍珠'
        if not itemId:
            return '未知物品'
        if type == '1':
            return self.main_data['crops'][itemId]['name']
        if type == '23':
            return self.other_data['fish_info'][itemId]['crop_name']
        if type == '3':
            return toolNameMap[itemId]
        if type == '10':
            return weaponNameMap[itemId]
        if type == '24':
            return fishToolNameMap[itemId]
        if type == '37':
            return self.get_vt_item_name(itemId)
        if type == '81':
            return self.other_data['squareProduct'][itemId]['name']

    def get_vt_item_name(self, vtid):
        vtid = str(vtid)
        if vtid.startswith('vt'):
            vtid = vtid[2:]
        return self.other_data['virtual'][vtid]['name']

    def parse_other_setting(self, url):
        version = re.findall(r'others_v_(.*).xml', url)[0]
        self.other_data = {'version': version}
        if os.path.exists('./config/other_settings.json'):
            with open('./config/other_settings.json', 'r') as f:
                self.other_data = json.load(f)
                return
        xml_file = self.__session.get(url)

        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file.write(xml_file.content)
        tmp_file.flush()
        tmp_file.seek(0)

        domTree = parse(tmp_file)
        rootNode = domTree.documentElement

        json_index = [['waterPool', 'fish_info'], ['virtual', 'virtual'], ['ratingsNew', 'ratingsNew'],
                      ['hive', 'hive'], ['formula', 'formula'], ['square', 'square'],
                      ['squareProduct', 'squareProduct'], ['squareProduct', 'squareProduct'],
                      ['orderLevelCfg', 'orderLevelCfg'], ['orderCfg', 'orderCfg'],
                      ['xiaotanLevelCfg', 'xiaotanLevelCfg'], ['xiaotanNpcCfg', 'xiaotanNpcCfg'],
                      ['fishPoolConfig', 'fishPoolConfig'], ['pearlMussel', 'pearlMussel'], ['beeConfig', 'beeConfig'],
                      ['manaPoolConfig', 'manaPoolConfig'], ['magicSeed', 'magicSeed'], ['marine', 'marine'],
                      ['marineSkill', 'marineSkill'], ['marineExplore', 'marineExplore']]

        # 狗
        self.other_data['dogs'] = {}
        dogs = rootNode.getElementsByTagName("dog")
        for dog in dogs:
            did = dog.getAttribute('id')
            name = dog.getAttribute('name')
            desc = dog.getAttribute('dogDesc')
            self.other_data['dogs'][did] = {'id': did, 'name': name, 'desc': desc}

        for each in json_index:
            items = rootNode.getElementsByTagName(each[0])
            item = items[0].childNodes[1].data.strip().replace('\n', '')
            tmp = eval(item)[each[1]]
            if each[1] == 'virtual':
                tmp = tmp[0]
            self.other_data[each[1]] = {}
            for one_item in tmp:
                if each[1] == 'fishPoolConfig':
                    self.other_data[each[1]][one_item['level']] = one_item
                else:
                    self.other_data[each[1]][one_item['id']] = one_item
        with open('./config/other_settings.json', 'w') as f:
            json.dump(self.other_data, f)

    def parse_main_setting(self, url):
        version = re.findall(r'data_zh_CN_m_v_(.*).xml', url)[0]
        self.main_data = {'version': version}
        if os.path.exists('./config/main_settings.json'):
            with open('./config/main_settings.json', 'r') as f:
                self.main_data = json.load(f)
                return
        xml_file = self.__session.get(url)

        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file.write(xml_file.content)
        tmp_file.flush()
        tmp_file.seek(0)

        domTree = parse(tmp_file)
        rootNode = domTree.documentElement

        json_index = [['crops', 'crops']]

        for each in json_index:
            items = rootNode.getElementsByTagName(each[0])
            item = items[0].childNodes[1].data.strip().replace('\n', '')
            tmp = eval(item)[each[1]]
            self.main_data[each[1]] = {}
            for one_item in tmp:
                self.main_data[each[1]][one_item['id']] = one_item
        with open('./config/main_settings.json', 'w') as f:
            json.dump(self.main_data, f)

    def get_farm_resources(self):
        print('开始加载农场基础配置')
        response = self.__session.get('https://appbase.qzone.qq.com/cgi-bin/index/appbase_run_unity.cgi?appid=353')
        flash_var = re.findall('var FLASH_VARS = {\n(.*)\n', response.text)[0].strip()
        flash_var = eval('{' + flash_var + '}')

        self.parse_other_setting(flash_var['config_other'])
        self.parse_main_setting(flash_var['config_data_m'])
        print('加载农场基础配置完成')

    def parse_farmland(self, status):
        self.data['land_info'] = []
        for each in status:
            land_level = 0
            if each['bitmap'] == 0 or each['bitmap'] == 1:
                land_level = each['bitmap']
            elif each['bitmap'] == 2 and each['isGoldLand'] == 0:
                land_level = 2
            elif each['bitmap'] == 2 and each['isGoldLand'] == 1:
                land_level = 3
            elif each['bitmap'] == 8:
                land_level = 4
            elif each['bitmap'] == 16:
                land_level = 5
            elif each['bitmap'] == 32:
                land_level = 6
            if each['a'] == 0:
                self.data['land_info'].append({
                    'crop_id': 0,
                    'crop_status': 0,
                    'land_level': land_level,
                    'weed': 0,
                    'pest': 0,
                    'water': 0,
                    'now_season': 0
                })
            else:
                self.data['land_info'].append({
                    'crop_id': each['a'],
                    'crop_status': each['b'],
                    'land_level': land_level,
                    'weed': each['f'],
                    'pest': each['g'],
                    'water': 1 ^ each['h'],
                    'plant_time': each['q'],
                    'now_season': each['j'] + 1
                })
        return 0

    def query_farm_index(self):
        farmtime, farmkey, farmkey2 = generate_farmkey()
        form_data = {
            'farmTime': '0',
            'uIdx': '',
            'farmKey': farmtime,
            'uinY': ''
        }
        url = 'https://nc.qzone.qq.com/cgi-bin/cgi_farm_index?mod=user&act=run&wd=0'
        code, data = self.http_post_request(url, form_data, '用户基础信息', 2)
        if code == 0:
            print('获取用户基础信息成功')
            self.serverTimeDelta = int(time.time()) - data['serverTime']['time']
            self.data['basic_info']['uin'] = data['user']['uinLogin']
            self.data['basic_info']['money'] = data['user']['money']
            self.data['basic_info']['coupon'] = data['user']['coupon']
            self.data['basic_info']['exp'] = data['user']['exp']
            self.data['basic_info']['uId'] = data['user']['uId']
            self.data['basic_info']['dog'] = data['dog']['dogId']

            self.parse_farmland(data['farmlandStatus'])
        return code

    def get_nickname(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/query?act=2010029&g_tk={self.__g_tk}'
        form_data = self.generate_form({'uinlist': self.data['basic_info']['uin']})
        code, data = self.http_post_request(url, form_data, '用户昵称')
        if code == 0:
            print('获取用户昵称成功')
            self.data['basic_info']['nickname'] = data['name'][0]['nick']
        return code

    def get_farm_bag(self):
        url = f'https://farm.qzone.qq.com/cgi-bin/cgi_farm_getuserseed?mod=repertory&act=getUserSeed&g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code1, data = self.http_post_request(url, form_data, '用户种子背包', 2)
        self.data['bag_info'] = {
            'crop': {},
            'item': {},
            'fish': {},
        }
        if code1 == 0:
            for item in data:
                if item['type'] == 1:
                    self.data['bag_info']['crop'][item['cId']] = item
                elif item['type'] == 23:
                    self.data['bag_info']['fish'][item['fId']] = item
                elif item['type'] == 3:
                    self.data['bag_info']['item']['%d::%d' % (item['type'], item['tId'])] = item
                elif item['type'] == 10:
                    self.data['bag_info']['item']['%d::%d' % (item['type'], item['tId'])] = item
                elif item['type'] == 24:
                    self.data['bag_info']['item']['%d::%d' % (item['type'], item['fId'])] = item

        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_get_virtualtools?g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code2, data = self.http_post_request(url, form_data, '用户道具背包')
        if code2 == 0:
            for item in data['virtualtool']:
                if item['type'] == 37:
                    self.data['bag_info']['item']['%d::%d' % (item['type'], item['id'])] = item
        if code1 == 0 and code2 == 0:
            print('获取用户背包信息成功')
            return 0
        else:
            return -1

    def get_farm_dogfood(self):
        url = f'https://farm.qzone.qq.com/cgi-bin/cgi_farm_feedmoney?mod=dog&act=feedMoney&g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code, data = self.http_post_request(url, form_data, '狗粮', 2)
        if code == 0:
            print('获取狗粮倒计时成功')
            self.data['basic_info']['dogfood'] = data['hours']
        return code

    def get_farm_score(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_judge_score_index?g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code, data = self.http_post_request(url, form_data, '用户评级')
        if code == 0:
            print('获取用户评级信息成功')
            is_sameday = ((data['draw']) // 86400 - (int(time.time()) - self.serverTimeDelta) // 86400) != 0
            self.data['rank_info']['land'] = data['land']
            self.data['rank_info']['crop'] = data['crop']
            self.data['rank_info']['fish'] = data['fish']
            self.data['rank_info']['dog'] = data['dog']
            self.data['rank_info']['item'] = data['item']
            self.data['rank_info']['score'] = data['score']
            self.data['rank_info']['level'] = data['level']
            self.data['rank_info']['reward'] = is_sameday
            self.data['rank_info']['level_desc'] = self.other_data['ratingsNew'][str(data['level'])]['desc']
        return code

    def get_farm_info(self):
        code = self.query_farm_index()
        if code != 0:
            return -1
        code = self.get_farm_bag()
        if code != 0:
            return -1
        code = self.get_farm_score()
        if code != 0:
            return -1
        code = self.get_farm_dogfood()
        if code != 0:
            return -1
        code = self.get_farm_essence()
        if code != 0:
            return -1
        code = self.get_hive()
        if code != 0:
            return -1
        code = self.get_wishtree()
        if code != 0:
            return -1
        code = self.get_marine_info()
        if code != 0:
            return -1
        code = self.get_marine_order_info()
        if code != 0:
            return -1
        return 0

    def farm_opt(self, land, operation):
        form_data = self.generate_form({'place': land, 'ownerId': self.data['basic_info']['uId']})
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_opt?mod=farmlandstatus&act={operation}&g_tk={self.__g_tk}'
        translator = {'clearWeed': '除草', 'spraying': '除虫', 'water': '浇水'}
        code, data = self.http_post_request(url, form_data, translator[operation], 1)
        if code == 0:
            if operation == 'clearWeed':
                print('除草成功')
                self.data['land_info'][land]['weed'] ^= 1
            elif operation == 'spraying':
                self.data['land_info'][land]['pest'] ^= 1
            elif operation == 'water':
                self.data['land_info'][land]['water'] ^= 1
            self.data['basic_info']['exp'] += data['exp']
        return code

    def farm_plant_operation(self, land, operation, cid=0):
        form_data = self.generate_form({'place': land, 'ownerId': self.data['basic_info']['uId']})
        if operation == 'scarify':
            form_data['cropStatus'] = form_data['uIdx']
        elif operation == 'planting':
            form_data['cId'] = cid
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_plant?mod=farmlandstatus&act={operation}&g_tk={self.__g_tk}'
        translator = {'scarify': '铲地', 'harvest': '收获', 'planting': '种植'}
        code, data = self.http_post_request(url, form_data, translator[operation], 1)
        if code == 0:
            if operation == 'scarify':
                self.data['land_info'][land] = {
                    'crop_id': 0,
                    'crop_status': 0,
                    'land_level': self.data['land_info'][land]['land_level'],
                    'weed': 0,
                    'pest': 0,
                    'water': 0,
                    'now_season': 0
                }
                print('%s成功，增加经验%d点' % (translator[operation], data['exp']))
            elif operation == 'harvest':
                self.data['land_info'][land]['crop_status'] = data['status']['cropStatus']
                self.data['land_info'][land]['plant_time'] = data['status']['plantTime']
                self.data['land_info'][land]['now_season'] += 1
                print('收获成功，获得%s%d个，经验增加%d' % (self.data['land_info'][land]['crop_name'], data['harvest'], data['exp']))
            elif operation == 'planting':
                self.data['land_info'][land] = {
                    'crop_id': data['cId'],
                    'crop_status': 1,
                    'land_level': self.data['land_info'][land]['land_level'],
                    'weed': 0,
                    'pest': 0,
                    'water': 0,
                    'plant_time': int(time.time()) - self.serverTimeDelta,
                    'now_season': 1
                }
            self.data['basic_info']['exp'] += data['exp']
        return code

    def buy_seed(self, cid, number=1):
        url = f'https://farm.qzone.qq.com/cgi-bin/cgi_farm_buyseed?mod=repertory&act=buySeed&g_tk={self.__g_tk}'
        form_data = self.generate_form({'number': number, 'cId': cid})
        code, data = self.http_post_request(url, form_data, '购买种子')
        if code == 0:
            self.data['basic_info']['money'] += data['money']
        return code

    def rank_draw(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_judge_score_draw?g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code, data = self.http_post_request(url, form_data, '获得等级奖励')
        if code == 0:
            self.data['rank_info']['reward'] = False
            pkg = self.other_data['ratingsNew'][str(self.data['rank_info']['level'])]['gift']
            addTool = []
            for each in pkg:
                addTool.append('%sx%d' % (self.get_item_name(each['type'], each['item_id']), each['num']))
                pass
            if addTool:
                addTool = '，获得' + '、'.join(addTool)
            else:
                addTool = ''
            print('获取等级奖励成功%s' % addTool)
        return code

    def get_farm_essence(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_essence?act=index&g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code, data = self.http_post_request(url, form_data, '精华数据')
        if code == 0:
            self.data['essence_info']['num'] = data['num']
            self.data['essence_info']['slot'] = [{
                'id': data['list'][0]['box'],
                'timestamp': data['list'][0]['plant_time']
            }]
        return code

    def essence_harvest(self, box):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_essence?act=harvest&g_tk={self.__g_tk}'
        form_data = self.generate_form({'box': box})
        code, data = self.http_post_request(url, form_data, '精华收获')
        if code == 0:
            self.data['essence_info']['num'] += data['add']
            self.data['essence_info']['slot'][box - 1]['timestamp'] = 0
        return code

    def essence_plant(self, box, cid):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_essence?g_tk={self.__g_tk}'
        form_data = self.generate_form({'box': box, 'cid': cid, 'act': 'plant'})
        code, data = self.http_post_request(url, form_data, '提取精华')
        if code == 0:
            self.data['essence_info']['slot'][box - 1] = {
                    'id': cid,
                    'timestamp': int(time.time()) - self.serverTimeDelta + 8 * 60 * 60
                }
        return code

    def get_hive(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_hive_index?g_tk={self.__g_tk}'
        form_data = self.generate_form({'ownerId': self.data['basic_info']['uId']})
        code, data = self.http_post_request(url, form_data, '蜂巢信息')
        if code == 0:
            self.data['hive_info'] = {
                'level': data['level'],
                'free_pollen': data['freeCD'],
                'pay_pollen': data['payCD'],
                'jelly': data['fwj'],
                'honey': data['honey'],
                'status': data['status'],
                'timestamp': data['stamp'],
            }
        return code

    def hive_work(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_hive_work?g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code, data = self.http_post_request(url, form_data, '放蜂')
        if code == 0:
            self.data['hive_info']['timestamp'] = data['stamp']
            self.data['hive_info']['status'] = 1
        return code

    def hive_harvest(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_hive_harvest?g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code, data = self.http_post_request(url, form_data, '收获蜂蜜')
        if code == 0:
            addHoney = data['addHoney'] + self.data['hive_info']['level']
            addMoney = data['addMoney']
            pkg = data['pkg']
            addTool = []
            for each in pkg:
                addTool.append('%sx%d' % (self.get_item_name(each['itemtype'], each['itemid']), each['num']))
                pass
            if addTool:
                addTool = '，获得' + '、'.join(addTool)
            else:
                addTool = ''
            self.data['basic_info']['money'] += addMoney
            self.data['hive_info']['timestamp'] = data['stamp']
            self.data['hive_info']['honey'] += addHoney
            self.data['hive_info']['status'] = 2
            print('收获蜂蜜成功，获得金币%d，蜂蜜%d个%s' % (addMoney, addHoney, addTool))
        return code

    def get_wishtree(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_wish_index?g_tk={self.__g_tk}'
        form_data = self.generate_form({'ownerId': self.data['basic_info']['uId']})
        code, data = self.http_post_request(url, form_data, '愿望树信息')
        if code == 0:
            self.data['wishtree_info'] = {
                'level': data['lv'],
                'wish_status': data['status'],
                'wish_level': data['star_lv'],
                'wish_count': data['w_num'],
                'wish_timestamp': data['self_lasttime'],
                'wish_today_count': data['self'],
                'star_list': data['starlist'],
                'star_timestamp': data['freeStarTime'],
            }
            if data['status'] in [0, 1]:
                self.data['wishtree_info']['wish_item'] = data['gift_list']
            else:
                self.data['wishtree_info']['wish_item'] = data['gift_new']
            for each in self.data['wishtree_info']['wish_item']:
                each['name'] = self.get_item_name(each['type'], each['itemid'])
        return code

    def wishtree_wish(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_wish_help?g_tk={self.__g_tk}'
        form_data = self.generate_form({'ownerId': self.data['basic_info']['uId']})
        code, data = self.http_post_request(url, form_data, '愿望树许愿')
        if code == 0:
            self.get_wishtree()
        return code

    def wishtree_wish_harvest(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_wish_harvest?g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code, data = self.http_post_request(url, form_data, '愿望树收获')
        if code == 0:
            addTool = data['pkg']
            pkg = []
            for each in addTool:
                pkg.append('%sx%d' % (self.get_item_name(each['type'], each['id']), each['num']))
            if pkg:
                pkg = '，获得' + ','.join(pkg)
            else:
                pkg = ''
            print('收获愿望树愿望成功%s' % pkg)
            self.get_wishtree()
        return code

    def wishtree_new_wish(self, newwish):
        newwish.sort()
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_wish_plant?g_tk={self.__g_tk}'
        form_data = self.generate_form({'id': newwish[0], 'idlist': '_'.join(list(map(str, newwish)))})
        code, data = self.http_post_request(url, form_data, '愿望树重置')
        if code == 0:
            self.wishtree_wish()
        return code

    def wishtree_star(self, starid):
        url = f'https://nc.qzone.qq.com/cgi-bin/cgi_farm_wish_star?g_tk={self.__g_tk}'
        form_data = self.generate_form({'type': 0, 'id': starid})
        code, data = self.http_post_request(url, form_data, '愿望树摘星')
        if code == 0:
            addTool = '%sx%d' % (self.get_item_name(data['pkg'][0]['type'], data['pkg'][0]['id']),
                                 data['pkg'][0]['num'])
            print('愿望树摘星成功，获得%s' % addTool)
            self.data['wishtree_info']['star_list'].append(starid)
            self.data['wishtree_info']['star_timestamp'] += 28800
        return code

    def get_marine_info(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/query?act=2110001&g_tk={self.__g_tk}'
        form_data = self.generate_form({'uin': self.data['basic_info']['uin']})
        code, data = self.http_post_request(url, form_data, '深海探险信息')
        if code == 0:
            self.data['marine_info'] = {
                'level': data['level'],
                'exp': data['exp'],
                'unlock_area': data['unlockArea'],
                'oil': data['oil'],
                'coin': data['coin'],
                'inventory': [],
                'order': [],
                'marine': []
            }
            for key, value in data.items():
                if re.match(r'vt\d\d\d\d', key):
                    if value:
                        self.data['marine_info']['inventory'].append({
                            'id': key[2:],
                            'name': self.get_vt_item_name(key),
                            'num': value
                        })
            for it, marine in enumerate(data['vSubmarine']):
                self.data['marine_info']['marine'].append({
                    'id': it + 1,
                    'name': self.other_data['marine'][str(it + 1)]['name'],
                    'level': marine['level'],
                    'exp': marine['exp'],
                    'status': marine['status'],
                    'areaid': marine['areaid'],
                    'depth': marine['high'],
                    'timestamp': marine['stamp']
                })
        return code

    def get_marine_order_info(self):
        url = f'https://nc.qzone.qq.com/cgi-bin/exchange?act=2110008&cmd=index&g_tk={self.__g_tk}'
        form_data = self.generate_form()
        code, data = self.http_post_request(url, form_data, '深海探险订单')
        if code == 0:
            self.data['marine_info']['order'] = []
            for it, order in enumerate(data['order']):
                item_list = []
                for item in order['o']:
                    item_list.append('%s*%d' % (self.get_vt_item_name(item['id']), item['num']))
                self.data['marine_info']['order'].append({
                    'coin': order['addCoin'],
                    'exp': order['addExp'],
                    'timestamp': order['stamp'],
                    'items': ','.join(item_list)
                })
        return code

    def marine_go(self, index, areaid):
        url = f'https://nc.qzone.qq.com/cgi-bin/exchange?act=2110009&cmd=go&g_tk={self.__g_tk}'
        form_data = self.generate_form({'index': index, 'areaid': areaid})
        code, data = self.http_post_request(url, form_data, '深海探险探索')
        if code == 0:
            self.data['marine_info']['marine'][index - 1]['status'] = data['status']
            self.data['marine_info']['marine'][index - 1]['timestamp'] = data['stamp']
            self.data['marine_info']['marine'][index - 1]['areaid'] = data['areaid']
            self.data['marine_info']['oil'] = data['oil']
        return code

    def marine_draw(self, index):
        url = f'https://nc.qzone.qq.com/cgi-bin/exchange?act=2110009&cmd=end&g_tk={self.__g_tk}'
        form_data = self.generate_form({'index': index})
        code, data = self.http_post_request(url, form_data, '深海探险返航')
        if code == 0:
            self.data['marine_info']['marine'][index - 1]['status'] = data['status']
            self.data['marine_info']['marine'][index - 1]['timestamp'] = data['stamp']
        return code

    def marine_harvest(self, index):
        url = f'https://nc.qzone.qq.com/cgi-bin/exchange?act=2110009&cmd=draw&g_tk={self.__g_tk}'
        form_data = self.generate_form({'index': index})
        code, data = self.http_post_request(url, form_data, '深海探险收获')
        if code == 0:
            self.data['marine_info']['marine'][index - 1]['status'] = data['status']
            self.data['marine_info']['marine'][index - 1]['timestamp'] = data['stamp']
            self.data['marine_info']['marine'][index - 1]['areaid'] = 0
        return code

    def __init__(self, session):
        self.serverTimeDelta = 0
        self.data = {
            'basic_info': {},
            'land_info': [],
            'rank_info': {},
            'essence_info': {},
            'bag_info': {},
            'hive_info': {},
            'wishtree_info': {},
            'marine_info': {}
        }
        self.other_data = {}
        self.main_data = {}
        self.__session = session
        self.__g_tk = generate_gtk(self.__session.cookies.get('skey'))
        self.get_farm_resources()
        pass

    def calculate_basic_info(self):
        level, realexp = calculate_level(self.data['basic_info']['exp'])
        self.data['basic_info']['level'] = level
        self.data['basic_info']['real_exp'] = realexp
        self.data['basic_info']['exp_percent'] = realexp * 100 / (level * 200 + 200)
        self.data['basic_info']['dog_name'] = self.other_data['dogs'][str(self.data['basic_info']['dog'])]['name']

    def simulate_farmland(self):
        timeDiscount = [0, 0, 0.2, 0.2, 0.25, 0.28, 0.28]
        for it, value in enumerate(self.data['land_info']):
            if value['crop_id'] == 0:
                continue
            crop_id = str(value['crop_id'])
            self.data['land_info'][it]['total_season'] = self.main_data['crops'][crop_id]['harvestNum']
            self.data['land_info'][it]['crop_name'] = self.main_data['crops'][crop_id]['name']
            self.data['land_info'][it]['target_time'] = 32503651199
            if value['crop_status'] == 0:
                self.data['land_info'][it]['crop_status_name'] = '空地'
            elif value['crop_status'] == 7:
                self.data['land_info'][it]['crop_status_name'] = '枯萎'
            else:
                allStatStamp = [value['plant_time']]
                allStatTime = list(map(int, self.main_data['crops'][crop_id]['cropGrow'].split(',')))
                isRed = -1
                if 'isRed' in self.main_data['crops'][crop_id].keys():
                    isRed = self.main_data['crops'][crop_id]['isRed']
                for onestat in allStatTime:
                    discount = 1
                    if value['land_level'] > isRed:
                        discount -= timeDiscount[value['land_level']]
                    allStatStamp.append(int(discount * onestat) + allStatStamp[0])
                for statId, statStamp in enumerate(allStatStamp):
                    if statStamp > self.serverTime:
                        allStatDes = self.main_data['crops'][crop_id]['nextText'].split(',')
                        self.data['land_info'][it]['crop_status'] = statId
                        self.data['land_info'][it]['crop_status_name'] = allStatDes[statId - 1]
                        self.data['land_info'][it]['target_time'] = allStatStamp[-2]
                        if self.data['land_info'][it]['target_time'] < self.serverTime:
                            self.data['land_info'][it]['crop_status'] = 6
                        break

    def simulate_hive(self):
        if self.data['hive_info']['status'] == 1:
            workTime = self.other_data['hive'][str(self.data['hive_info']['level'])]['worktime']
            targetTime = self.data['hive_info']['timestamp'] + workTime
        elif self.data['hive_info']['status'] == 2:
            restTime = self.other_data['hive'][str(self.data['hive_info']['level'])]['resttime']
            targetTime = self.data['hive_info']['timestamp'] + restTime
        self.data['hive_info']['target_time'] = targetTime

    def simulate(self):
        self.serverTime = time.time() - self.serverTimeDelta
        self.calculate_basic_info()
        self.simulate_farmland()
        self.simulate_hive()


def debug():
    login = Login(requests.session())
    login.get_token()
    login.get_logined_account()
    login.fast_login('')
    session = login.get_session()
    dummy = DummySystem(session)
    dummy.get_farm_info()
    dummy.query_farm_index()
    dummy.get_farm_score()
    dummy.get_farm_bag()
    dummy.get_hive()
    dummy.get_wishtree()


if __name__ == '__main__':
    debug()
