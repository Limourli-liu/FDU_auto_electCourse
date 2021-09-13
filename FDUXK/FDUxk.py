import json, time, random, sys, traceback, requests, re
from typing import Text
from requests.api import head
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from lxml import etree
from flask import Blueprint, jsonify, render_template, request
import json, os

space = re.compile(r'\s+')
htag = re.compile(r'<[^>]+>')
jsp = re.compile(r'if\(window.electCourseTable\)\{.*\}\s+')

app = Blueprint('FDUxk', __name__, url_prefix='/mod/FDUxk',
                template_folder='FDUxk/templates',
                static_folder='FDUxk/static',
                static_url_path='/mod/FDUxk/static'
                )

@app.route('/')
def index():
    return render_template('FDUxk_index.html')
@app.route('/info/')
def getInfo():
    return getVar('xk_info', 'hello world')

@app.route('/xk_cookie/', methods=['GET'])
def getCookie():
    return getVar('cookie', '打开 https://xk.fudan.edu.cn/ 按F12以获取cookie')
@app.route("/xk_cookie/", methods=['POST'])
def setCookie():
    res = request.data
    setVar('cookie', res)
    return xk_getProfileId()
@app.route('/xk_getCourseTable/', methods=['GET'])
def getCourseTable():
    res = xk_getCourseTable()
    return jsonify(res)
@app.route('/xk_C/', methods=['GET'])
def getC():
    return jsonify(getJson('xk_coursegroups', '[]'))
@app.route('/xk_C/', methods=["DELETE"])
def delC():
    g = request.args.get('g', "default", type=str)
    n = request.args.get('n', "", type=str)
    xk_delC(g, n)
    return jsonify(getJson('xk_coursegroups', '[]'))
@app.route("/xk_C/", methods=['POST'])
def addC():
    g = request.args.get('g', "default", type=str)
    n = request.args.get('n', "", type=str)
    xk_addC(g, n)
    return jsonify(getJson('xk_coursegroups', '[]'))
@app.route('/info_p2/', methods=['GET'])
def getP2():
    return jsonify(getJson('xk_p2', '[]'))
@app.route('/no_captcha/', methods=['GET'])
def no_captcha():
    setVar('xk_no_captcha', "T")
    return f"no_captcha {getVar('xk_no_captcha')}"
@app.route('/enforce/', methods=['GET'])
def enforce(): 
    id = request.args.get('id', 0, type=int)
    if id == 0: return "请选择有效内容！"
    g = request.args.get('g', "default", type=str)
    with lock: # 验证码需要保持单线程
        res = xk_electCourse(id)
        if '选课成功' in res:
            xk_delC(g, None)
    return res

def xk_addC(g, n):
    coursegroups = getJson('xk_coursegroups', '[]')
    for group in coursegroups:
        if group[0] == g:
            for item in group[1]:
                if item[1] == n:
                    break
            else:
                group[1].append(['', n,'','','',''])
            break
    else:
        coursegroups.append((g, [['', n,'','','','']]))
    setJson('xk_coursegroups', coursegroups)
def xk_delC(g, n):
    coursegroups = getJson('xk_coursegroups', '[]')
    for i,group in enumerate(coursegroups):
        if group[0] == g:
            if n is None:
                coursegroups.pop(i)
                break
            for j,item in enumerate(group[1]):
                if item[1] == n:
                    if len(group[1]) == 1:
                        coursegroups.pop(i)
                    else:
                        group[1].pop(j)
                    break
            break
    setJson('xk_coursegroups', coursegroups)
def xk_setC(g, n, newC):
    coursegroups = getJson('xk_coursegroups', '[]')
    for i,group in enumerate(coursegroups):
        if group[0] == g:
            for j,item in enumerate(group[1]):
                if item[1] == n:
                    coursegroups[i][1][j] = newC
                    break
            break
    setJson('xk_coursegroups', coursegroups)

def xk_init():
    global proxies, xk_s
    proxies = {
            "http": config['proxy'],
            "https": config['proxy']
    }
    xk_s = requests.Session()
    setVar('xk_info', '初始化完成\n')

def xk_headers(headers):
    headers['Cookie'] = getVar('cookie', '')
    if config['Host'] != '0': 
        headers['Host'] = config['Host']
    headers["User-Agent"] = config["User-Agent"]
    headers.update({
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Sec-Fetch-Site": "same-origin",
    })
    return headers

def xk_get(url, headers):
    return xk_s.get(url, headers = xk_headers(headers), proxies=proxies, timeout=config['连接超时时间'], verify=False)

def xk_post(url, headers, data):
    return xk_s.post(url, data=data, headers = xk_headers(headers), proxies=proxies, timeout=config['连接超时时间'], verify=False)

def xk_try(f, *arg, **kw):
    for i in range(config["一轮最大选课尝试次数"]):
        try:
            return f(*arg, **kw)
        except:
            xk_info(traceback.format_exc())
    raise RuntimeError('已达最大尝试次数')

def xk_getUrl(path, set_profileId=False):
    if set_profileId:
        return f"{config['选课URL']}{path}?profileId={getVar('xk_profileId')}"
    else:
        return f"{config['选课URL']}{path}"

def xk_getNotice(items): # 曾经不熟练lxml时写的，不想改了，就放这里了
    res = ''.join(items[0].xpath('./text()')) + '\n'
    tl = items[1].xpath('./text()')
    res += ('\n'.join(space.sub(' ',t) for t in tl)) + '\n'
    tl = items[2].xpath('.//text()')
    res += ('\n'.join(space.sub(' ',t) for t in tl))
    return res

def xk_getProfileId():
    headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": xk_getUrl("xk/login.action"),
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    }
    r = xk_try(xk_get, xk_getUrl('xk/stdElectCourse.action'), headers)
    html = etree.HTML(r.text)
    Notice0 = html.xpath('//div[@id="electIndexNotice0"]')
    if len(Notice0) != 1:
        xk_info(f'{r.text}\nxk_getProfileId 找不到electIndexNotice0, 可能登录已失效')
        return '找不到electIndexNotice0, 可能登录已失效'
    Notice0 = Notice0[0]
    items = Notice0.xpath('./*')
    if len(items) != 4:
        xk_info(f'{r.text}\nxk_getProfileId Notice0元素个数不为4, 可能选课尚未开放')
        return 'Notice0元素个数不为4, 可能选课尚未开放'
    xk_info(xk_getNotice(items))
    tl = items[3].xpath('./form/input/@value')
    if len(tl) !=1 or not tl[0].isnumeric():
        xk_info(f'{r.text}\nxk_getProfileId 未找到profileId, 可能选课尚未开放')
        return '未找到profileId, 可能选课尚未开放'
    profileId = tl[0]
    setVar('xk_profileId', profileId)
    xk_info(f'xk_profileId is {profileId}')
    return "success"

def xk_info(text):
    tmp = getVar('xk_info', '')
    if tmp.count('\n') > config["控制台最大输出行数"]:
        tmp = '\n'.join(tmp.split('\n')[config["控制台最大输出行数"]>>1:])
    tmp += '\n' + text
    setVar('xk_info', tmp)

def xk_getCourse(key):
    j1 = j2 = {}
    while not j1 or not j2:
        a = b = c = -1
        while b==-1 or c==-1:
            r = key()
            if isinstance(r, str): return r
            a = r.text.find('[')
            b = r.text.find(r';/*sc 当前人数, lc 人数上限*/')
            c = r.text.find('{', b)
            xk_info(f'getXkList {a} {b} {c}')
            if  b==-1 or c==-1:
                if '请不要过快点击' in r.text:
                    xk_info('请求过快, 稍后自动重试...')
                    sleep()
                else:
                    xk_info(f'未知错误,请尝试点击一次选课界面的>>>进入选课\n\n{r.text}')
                    return  '未知错误,请尝试点击一次选课界面的>>>进入选课'
        j1 = jsonfy(r.text[a:b])
        j2 = jsonfy(r.text[c:])
        if j1 == [] and j2 == {} : break
    return [(one['id'], one['no'], one['name'], getScLc(j2[str(one['id'])])) for one in j1]

def xk_getCourseTable():
    headers = {
    "Accept": "*/*",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": xk_getUrl("xk/stdElectCourse!defaultPage.action"),
    "Sec-Fetch-Dest": "script",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-origin"
    }
    url = xk_getUrl('xk/stdElectCourse!queryLesson.action', True)
    def _getLesson():
        return xk_try(xk_get, url, headers)
    sCourse = xk_getCourse(_getLesson)
    setJson('xk_p2', sCourse)
    return sCourse

def xk_inquireCoure(No):
    Form = {
    "lessonNo": No,
    "courseCode": "",
    "courseName": ""
    }
    headers = {
    "Accept": "*/*",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Origin": config['选课URL'],
    "Referer": xk_getUrl("xk/stdElectCourse!defaultPage.action"),
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
    }
    url = xk_getUrl('xk/stdElectCourse!queryLesson.action', True)
    def _postLesson():
        return xk_try(xk_post, url, headers, Form)
    sCourse = xk_getCourse(_postLesson)
    if isinstance(sCourse, str): return sCourse
    part1 = []
    part2 = []
    for item in sCourse:
        if item[1] != No:
            part1.append(item)
        else:
            part2.append(item)
    setJson('xk_p2', part1)
    if len(part2) !=1: return f'No有误 {No}'
    return part2[0]

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
        "控制台最大输出行数": 300,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36"
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

    # 注册web页面
    server = Manager.getMod("webserver")
    server.register_blueprint(app)

    # 初始化参数
    xk_init()

def xk_getCaptcha_():
    url = xk_getUrl('xk/captcha/image.action?d=')+str(getTimestamp())
    headers = {
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": xk_getUrl("xk/stdElectCourse!defaultPage.action"),
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-origin"
    }
    r = xk_try(xk_get, url, headers)
    img = r.content
    text = OCR(img)
    xk_info(f"验证码： {text}")
    return text
def xk_getCaptcha():
    if getVar('xk_no_captcha') != "T":
        return xk_getCaptcha_()
    setVar('xk_no_captcha', "F")
    return ''

def _Xk_m(key):
    limit = config["一轮最大选课尝试次数"]
    i = limit
    counter = 1
    while i >0 or limit == 0:
        st = key()
        if '选课成功' in st:
            xk_info(f'Xk2S 第{counter}次选课成功!')
            break
        else:
            xk_info(f'Xk2S 第{counter}次选课失败:')
            xk_info(jsp.sub('', st))
            if '选课失败:公选人数已满' in st: 
                if limit: break
            elif '选课失败:你已经选过' in st:
                return '选课成功!因为你已选过'
                break
            elif '课程不能超过最大选课1门数限制' in st:
                if limit: break
            elif '操作失败:验证码错误' in st:
                pass
            elif '选课失败:与以下课程冲突' in st:
                if limit: break
            else:
                i -= 1
        counter += 1
        sleep(10)
    else:
        return '本轮选课失败!'
    return f'{time.ctime(time.time())} 本次尝试结束, 未成功选课'

def xk_electCourse(ID):
    ct = False # 确保课程可以选
    s_ID = str(ID)
    coursegroups = getJson('xk_coursegroups', '[]')
    for group in coursegroups:
        for item in group[1]:
            if item[0] == s_ID:
                ct = True
                break
        if ct: break
    if not ct:
        return "该课程不在待选列表中， 可能已经成功选课！"
    headers = {
    "Accept": "text/html, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": config['选课URL'],
    "Referer": xk_getUrl("xk/stdElectCourse!defaultPage.action"),
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest"
    }
    data = {
    "optype": "true",
    "operator0": f"{ID}:true:0",
    "captcha_response": ""
    }
    url = xk_getUrl("xk/stdElectCourse!batchOperator.action", True)
    def _xk():
        captcha = xk_getCaptcha()
        data["captcha_response"] = captcha
        r = xk_try(xk_post, url, headers, data)
        return htag.sub(' ', space.sub('', r.text))
    res = _Xk_m(_xk)
    xk_info(f"xk_electCourse {res}")
    return res

def xk_XkTask(ID):
    with lock: # 验证码需要保持单线程
        return xk_electCourse(ID)

def _crontab():
    coursegroups = getJson('xk_coursegroups', '[]')
    for group in coursegroups:
        for item in group[1]:
            newC = xk_inquireCoure(item[1])
            if isinstance(newC, str):
                xk_info(newC)
                sleep()
                continue
            item [0] = str(newC[0])
            item [2] = newC[2]
            item [3] = str(newC[3][0])
            item [4] = str(newC[3][1])
            if newC[3][0] >= newC[3][1]:
                item [5] = f'{time.ctime(time.time())} 已达上限, 等待退课或余量释放'
                xk_setC(group[0], item[1], item)
                sleep()
            else:
                res = xk_XkTask(newC[0])
                if len(res) > 40:
                    xk_info(res)
                else:
                    item[5] = space.sub(' ', res).strip()
                if '选课成功' in res:
                    xk_delC(group[0], None)
                else:
                    xk_setC(group[0], item[1], item)
        sleep()

def getVar(name, dvalue=None):
    value = db.select_("value", f"globalVar='{name}'")
    if value:
        value = value[0][0]
    else:
        value = dvalue
    return value
def setVar(name, value):
    db.replace("globalVar,value", "?,?", (name, value), commit=True)

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

