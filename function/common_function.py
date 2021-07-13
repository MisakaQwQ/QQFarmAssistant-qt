import hashlib
import time
import math


def generate_farmkey():
    key = ['OPdfqwn^&*w(281flebnd1##roplaq', '(UuqQ=Ze93spP*:s1E/kkGt-:s^|Su']
    farmTime = int(time.time())
    farmKey = hashlib.md5()
    farmKey.update((str(farmTime) + key[0][farmTime % 10:]).encode('utf-8'))
    farmKey2 = hashlib.md5()
    farmKey2.update((str(farmTime) + key[1][farmTime % 10:]).encode('utf-8'))
    return farmTime, farmKey.hexdigest(), farmKey2.hexdigest()


def generate_gtk(skey):
    hash_tmp = 5381
    for each in skey:
        hash_tmp += (hash_tmp << 5) + ord(each)
    return hash_tmp & 0x7fffffff


def calculate_level(exp):
    d = -70000 + 400 * exp
    level = int((-100 + math.sqrt(d)) / 200)
    realexp = exp - 200 - (400 + level * 200) * (level - 1) // 2
    return level, realexp
