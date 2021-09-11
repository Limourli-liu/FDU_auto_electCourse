config, Manager, log, lock = 0,0,0,0 #保存宿主传递的环境 分别为配置文件， 模块管理器，日志，全局线程锁
def _default_config(root, name): #返回默认配置文件 载入时被调用 root为数据文件根目录 name为当前模块名称
    return {
        'modInformation':{ #该模块的信息
            'Name': 'BaseMod crontab',
            'Author': 'Limour @limour.top',
            'Version': '1.0',
            'description': 'A timer'
        },
        'priority':-9999, # 模块加载和调用的优先级，越大越先，默认为0
        'interval_scale': 60.0 # 一个时间间隔 单位 s
    }

def _init(m_name, _config, _Manager, _log): #载入时被调用
    global config, Manager, log, lock
    config, Manager, log, lock = _config, _Manager, _log, _Manager.threading_lock #保存宿主传递的环境
    main()
def _exit():
    tmp = timer.exit()
    log.debug(f'exit {tmp}')

import threading, time, traceback
def _interval():
    last = time.time()
    while True:
        now = time.time()
        yield now - last
        last = now
class Signal():
    sig = True # 控制信号， True表示线程继续执行
    state = False # 表明当前线程执行到哪一阶段
    def __init__(self):
        self._lock = threading.Lock() # 控制信号的锁
    def _set(self, sig):
        with self._lock:
            self.sig = sig
            return self.state
    def __call__(self, state):
        with self._lock:
            self.state = state
            return self.sig
class Timer(object):
    def __init__(self, _repeat, interval_scale = 60.0, _start=None):
        self._repeat = _repeat # 需要循环定时执行的函数
        self._i_scale = interval_scale # 时间间隔
        self._s = _start # 进入循环前执行的函数
        self.sig = Signal() # 交互控制信号
        self.t = threading.Thread(target=self._exec, daemon=True)
        self.t.start()
    def _exec(self):
        if self._s: self._s()
        _itv = _interval() # 间隔计时器
        while self.sig(False): # False表示可以中断的阶段
            slp = self._i_scale - next(_itv) # 需要休眠的时间
            if slp > 0: time.sleep(slp)
            next(_itv) # 重新开始计时
            if not self.sig(True): break # True表示需要等待的阶段
            self._repeat()
    def exit(self):
        if self.sig._set(False): # 设置为退出状态，并获取线程执行阶段
            self.t.join(self._i_scale+1) # 等待exec线程结束, 最多等interval_scale+1秒
            return not self.t.is_alive() # 是否成功结束
        return True

_crontab = []
_crontab_r = []
_lock = threading.Lock() # _crontab的线程锁
def repeat():
    with _lock:
        for _i,interval in enumerate(_crontab_r):
            if interval <= 1:
                f_name, interval, _func = _crontab[_i]
                _crontab_r[_i] = interval # 行一次后重置倒计时
                log.debug(f'exec {f_name}')
                try:
                    _func()
                except:
                    log.error(f'exec {f_name} {traceback.format_exc()}')
            else:
                _crontab_r[_i] = interval - 1
def submit(f_name, interval, _func):
    with _lock:
        _crontab.append((f_name, interval, _func))
        _crontab_r.append(interval)
def main():
    global timer
    interval_scale = config.get('interval_scale', 60.0)
    # print(interval_scale)
    # interval_scale = 2.0
    timer = Timer(repeat, interval_scale)
    log.debug('start')
