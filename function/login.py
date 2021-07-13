import requests
import re
import random
import cv2
import numpy as np
import time
import pickle
import os


class Login:
    session_var = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/87.0.4280.141 Safari/537.36 '
    }

    def get_token(self):
        '''
        获取本次登录token
        :return: pt_local_token, pt_login_sig: (str)本次登录token
        '''
        response = self.__session.get('https://xui.ptlogin2.qq.com/cgi-bin/xlogin?daid=5&&hide_title_bar=1&low_login'
                                      '=0&qlogin_auto_login=1&no_verifyimg=1&link_target=blank&appid=549000912&style'
                                      '=22&target=self&s_url=http%3A%2F%2Fgameapp.qq.com%2F353%3Fvia%3DCANVAS.MY-APPS'
                                      , headers=self.headers)
        self.headers['referer'] = 'https://xui.ptlogin2.qq.com/'
        pt_local_token = self.__session.cookies.get('pt_local_token')
        self.session_var['pt_local_token'] = pt_local_token
        pt_login_sig = self.__session.cookies.get('pt_login_sig')
        self.session_var['pt_login_sig'] = pt_login_sig
        print('获取本次登录Token成功')
        return pt_local_token

    def get_logined_account(self):
        '''
        获取本机已登录的账户，用于快捷登录选择
        :return: all_account: (dict)本机已登录的账户
        '''
        response = self.__session.get(f'https://localhost.ptlogin2.qq.com:4301/pt_get_uins?callback=ptui_getuins_CB&r'
                                      f'=0.5260028619901231&pt_local_tk={self.session_var["pt_local_token"]}'
                                      , headers=self.headers, verify=False)
        raw_account = re.findall(r'var var_sso_uin_list=(.*);ptui_getuins_CB\(var_sso_uin_list\);', response.text)[0]
        raw_account = eval(raw_account)
        all_account = {}
        for each in raw_account:
            all_account[each['account']] = each
        print('获取本机已登录账号成功')
        return all_account

    def fast_login(self, clientuin):
        '''
        执行快速登陆
        :return: session_var: (dict)本次登录变量
        '''
        self.session_var['clientuin'] = clientuin
        # Get clientkey
        response = self.__session.get(f'https://localhost.ptlogin2.qq.com:4301/pt_get_st?clientuin={clientuin}&callback'
                                      f'=ptui_getst_CB&r=0.3818555904960179&pt_local_tk='
                                      f'{self.session_var["pt_local_token"]}', headers=self.headers)
        clientkey = self.__session.cookies.get('clientkey')
        self.session_var['clientkey'] = clientkey

        # Get skey, uin
        response = self.__session.get(f'https://ssl.ptlogin2.qq.com/jump?clientuin={clientuin}&keyindex=9&pt_aid'
                                      f'=549000912&daid=5&u1=http%3A%2F%2Fgameapp.qq.com%2F353%3Fvia%3DCANVAS.MY-APPS'
                                      f'&pt_local_tk={self.session_var["pt_local_token"]}'
                                      f'&pt_3rd_aid=0&ptopt=1&style=40', headers=self.headers)
        skey = self.__session.cookies.get('skey')
        self.session_var['skey'] = skey
        uin = self.__session.cookies.get('uin')
        self.session_var['uin'] = uin

        # Get p_skey
        url = re.findall(r"ptui_qlogin_CB\('0', '(.*)', ''\)", response.text)[0]
        response = self.__session.get(url, headers=self.headers)
        p_skey = self.__session.cookies.get('p_skey')
        self.session_var['p_skey'] = p_skey
        self.save_cookies()
        print('快速登录完成')
        return self.session_var

    def qrcode_login_get_image(self):
        '''
        获取二维码图片
        :return: qrcode: (ndarray)二维码图片
        '''
        t = str(random.random())
        response = self.__session.get(f'https://ssl.ptlogin2.qq.com/ptqrshow?appid=549000912&e=2&l=M&s=3&d=72&v=4&t={t}'
                                      f'&daid=5&pt_3rd_aid=0', headers=self.headers)
        qrsig = self.__session.cookies.get('qrsig')
        self.session_var['qrsig'] = qrsig
        ret = 0
        for each in qrsig:
            ret = ret + (ret << 5)
            ret = ret + ord(each)
        ptqrtoken = str(2147483647 & ret)
        self.session_var['ptqrtoken'] = ptqrtoken
        qrcode = np.asarray(bytearray(response.content), dtype="uint8")
        qrcode = cv2.imdecode(qrcode, cv2.IMREAD_COLOR)
        # cv2.imshow('qrcode', qrcode)
        # cv2.waitKey(0)
        print('二维码图片获取完成')
        return qrcode

    def qrcode_login_get_status(self):
        '''
        检查二维码是否已登录成功
        :return: status_code, status_des: (str)状态码，状态描述
        '''
        action = '0-0-' + str(int(time.time() * 1000))
        response = self.__session.get(f'https://ssl.ptlogin2.qq.com/ptqrlogin?u1=https%3A%2F%2Fgameapp.qq.com'
                                      f'%2F353%3Fvia%3DCANVAS.MY-APPS&ptqrtoken={self.session_var["ptqrtoken"]}'
                                      f'&ptredirect=0&h=1&t=1&g=1&from_ui=1&ptlang=2052&action={action}&js_ver=21010623'
                                      f'&js_type=1&login_sig={self.session_var["pt_login_sig"]}&pt_uistyle=40'
                                      f'&aid=549000912&daid=5&', headers=self.headers)
        status = re.findall(r'ptuiCB(.*)', response.text)[0]
        status = eval(status)
        if status[0] == '65':
            # 已失效
            pass
        elif status[0] == '66':
            # 未失效
            pass
        elif status[0] == '67':
            # 确认中
            pass
        elif status[0] == '0':
            # 确认成功
            response = self.__session.get(status[2])
            skey = self.__session.cookies.get('skey')
            self.session_var['skey'] = skey
            uin = self.__session.cookies.get('uin')
            self.session_var['uin'] = uin
            p_skey = self.__session.cookies.get('p_skey')
            self.session_var['p_skey'] = p_skey
            self.save_cookies()
        print('二维码状态[%s]' % status[4])
        return status[0], status[4]

    def save_cookies(self):
        with open('cookies.dat', 'wb') as f:
            pickle.dump(self.__session.cookies, f)

    def load_cookies(self):
        if not os.path.exists('cookies.dat'):
            return -1
        with open('cookies.dat', 'rb') as f:
            self.__session.cookies.update(pickle.load(f))
            return 0

    def check_load_status(self):
        '''
        检查是否登录成功
        :return: 0: 成功  -1: 失败
        '''
        uin = self.__session.cookies.get('uin')[1:]
        response = self.__session.get(f'https://user.qzone.qq.com/{uin}', headers=self.headers)
        if '全部动态' in response.text:
            return 0
        return -1

    def get_session(self):
        return self.__session

    def __init__(self, session):
        self.__session = session


def debug():
    login = Login(requests.Session())
    # login.load_cookies()
    # login.check_load_status()
    login.get_token()
    login.get_logined_account()
    # login.fast_login('')
    # login.check_load_status()
    login.qrcode_login_get_image()
    while True:
        login.qrcode_login_get_status()
        time.sleep(2)


if __name__ == '__main__':
    debug()
