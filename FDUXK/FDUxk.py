import json, time, random, sys, traceback, requests, re
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from lxml import etree
config, Manager, log, lock = 0,0,0,0 #保存宿主传递的环境 分别为配置文件， 模块管理器，日志，全局线程锁
def _default_config(root, name): #返回默认配置文件 载入时被调用 root为数据文件根目录 name为当前模块名称
    return {
        'modInformation':{ #该模块的信息
            'Name': 'Core fucthion mod of this',
            'Author': 'Limour @limour.top',
            'Version': '1.2',
            'description': 'Core fucthion mod of this project'
        },
        "proxy": "",
        "proxy说明": "格式为 http://user:password@host:port",
        "选课URL": "https://xk.fudan.edu.cn/",
        "Host": "0",
        "轮询间隔": 5,
        "一轮最大选课尝试次数": 3,
        "连接超时时间": 30,
        "随机抖动缩放": 10,

    }

def _init(m_name, _config, _Manager, _log): #载入时被调用
    global config, Manager, log, lock, db, OCR
    config, Manager, log, lock = _config, _Manager, _log, _Manager.threading_lock #保存宿主传递的环境

    # 全局变量表
    _db = Manager.getMod('database').db # 调用BaseMod database
    db = _db.create(m_name, 'globalVar TEXT PRIMARY KEY, value TEXT')

    # OCR模块
    _ocr = Manager.getMod('Captcha_break')
    OCR = _ocr.torchOCR

    # 创建轮询
    Manager.getMod("crontab").submit(m_name, config["轮询间隔"], _crontab) # 调用BaseMod crontab

def _crontab():
    pass

def getVar(name, dvalue=None):
    value = db.select_("value", f"globalVar='{name}'")
    if value:
        value = value[0][0]
    else:
        value = dvalue
    return value
def setVar(name, value):
    db.replace("globalVar,value", "?,?", (name, value), commit=True)

def setCookie(value):
    setVar("cookie", value)

def getJson(name, dvalue="{}"):
    return json.loads(getVar(name, dvalue))

def setJson(name, value):
    setVar(name, json.dumps(value, indent=4, ensure_ascii=False))

def sleep(a=5, b=25):
    time.sleep(random.randint(a, b)/config["随机抖动缩放"])
def jsonfy(s:str)->object:
    #此函数将不带双引号的json的key标准化
    if s[0] not in ('{','['): return {}
    try:
        obj = eval(s, type('js', (dict,), dict(__getitem__=lambda s, n: n))())
        return obj
    except Exception:
        if s[0] == "{": return {}
        return []
def getScLc(d):
    return (int(d['sc']), int(d['lc']))
def getTimestamp(size = 1000):
    t = time.time()
    return int(round(t * size))

space = re.compile(r'\s+')
htag = re.compile(r'<[^>]+>')
jsp = re.compile(r'if\(window.electCourseTable\)\{.*\}\s+')

