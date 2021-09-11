import pkgutil,traceback, atexit, json, os, threading
import logging, logging.config
from concurrent.futures import ThreadPoolExecutor


def _path(name, root=None):
    p =  os.path.join(root or os.getcwd(), name)
    return (os.path.exists(p) or not os.makedirs(p)) and p
def _rJson(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)
def _wJson(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def _logDefault(path, name):
        config = {
        "version": 1,
        "disable_existing_loggers": False, # 禁用已经存在的logger实例
        "formatters":{ # 日志格式化(负责配置log message 的最终顺序，结构，及内容)
            "simple":{ #简单的格式
                "format":"%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers":{ # 负责将Log message 分派到指定的destination
            "console":{ # 打印到终端的日志
                "class":"logging.StreamHandler", # 打印到屏幕
                "level":"DEBUG",
                "formatter":"simple",
                "stream":"ext://sys.stdout"
            },
            "common":{ # 打印到log文件的日志,收集info及以上的日志
                "class":"logging.handlers.RotatingFileHandler", # 保存到文件
                "level":"INFO",
                "formatter":"simple",
                "filename":path, # 日志文件路径
                "maxBytes":10485760, #日志大小 10M
                "backupCount":3, # 备份3个日志文件
                "encoding":"utf8" # 日志文件的编码
            },
        },
        "loggers":{ # logger实例
            name:{ # 日志记录的名称
                "level":"DEBUG",
                "handlers":["console", "common"], # log数据打印到控制台和文件
                "propagate": True # 向上（更高level的logger）传递
            }
        }}
        return config
def _getConf(path, Default):
    if os.path.exists(path):
        config = _rJson(path)
        return config
    else:
        _wJson (path, Default)
        return Default
class Config(dict):
    def __init__(self, root, name, Default):
        self.path = f'{root}/{name}.json'
        self.update(_getConf(self.path, Default))
    def save(self):
        _wJson(self.path, self)
    def setNew(self, NewDict):
        self.clear()
        self.update(NewDict)

class ModManager(object):
    def __init__(self, name, max_workers=4):
        self.name = name #应用的名称
        self.root = _path(f'data/{name}') #所有数据的储存位置
        # 加载日志模块
        logConf = Config(self.root, 'logging', _logDefault(f'data/{name}/Mod.log', name))
        logging.config.dictConfig(logConf)# 导入上面定义的logging配置
        self.logger = logging.getLogger(name) # 创建日志实例
        self.logger.debug(f'ModManager.__init__({name}, {max_workers})')
        self.threading_lock = threading.Lock()
        self.logger.debug(f'ModManager.threading_lock {self.threading_lock}')
        atexit.register(self._exit) # 模块退出时回调
        self.logger.debug('ModManager exitfunc registered')
        plugins = {} # 查找所有 name 目录下的所有模块
        plist = [] # 按优先级对模块排序
        for finder,m_name,ispck in pkgutil.walk_packages([_path(name)]):
            self.logger.debug(f'ModManager plugin load {m_name}')
            loader = finder.find_module(m_name)
            try:
                mod = loader.load_module(m_name)
                try:
                    default = mod._default_config(f"data/{name}", m_name) # 读取默认配置, 相对路径
                except:
                    default = {} # 无默认配置
                    self.logger.debug(f'ModManager {m_name}._default_config \n{traceback.format_exc()}')
                config = Config(self.root, m_name, default) # 读取配置
                plugins[m_name] = (mod, config)
                priority = config.get('priority', 0) # 按优先级对模块排序 获取优先级
                plist.append((m_name, priority))
            except:
                self.logger.error(f'ModManager load {m_name} \n{traceback.format_exc()}')
        self.plugins = plugins
        plist.sort(key=lambda x:x[1], reverse=True)
        self.plist = plist
        self.logger.debug('ModManager plugins all loaded')
        self.threadPool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"{name}.")
        self.logger.debug(f'ModManager threadPool {self.threadPool}')
        self._init()
    def readConf(self, propertyName, default=None):
        res = []
        for key, priority in self.plist:
            config = self.plugins[key][1]
            property = config.get(propertyName, default)
            if property is not None:
                res.append((key, property))
        return res
    def getCall(self, attributeName):
        res = []
        for key, priority in self.plist:
            mod = self.plugins[key][0]
            attribute = getattr(mod, attributeName, None)
            if attribute is not None:
                res.append((key, attribute))
        return res
    def Call(self, attribute, *args, **kw):
        if type(attribute) is str:
            attribute = self.getCall(attribute)
        res = {}
        for m_name, m_attr in attribute:
            try:
                future = self.threadPool.submit(m_attr, *args, **kw)
                res[m_name] = future
            except:
                self.logger.error(f'ModManager {m_name}.{m_attr} \n{traceback.format_exc()}')
        self.logger.debug(f'ModManager plugins.attr have been added to threadPool')
        resu = []
        for  m_name,future in res.items():
            try:
                r = future.result()
                if r is not None:
                    resu.append(r)
            except:
                self.logger.error(f'ModManager {m_name}.attr \n{traceback.format_exc()}')
        self.logger.debug(f'ModManager plugins.attr all done')
        return resu
    def submit(self, attr, *args, **kw):
        return self.threadPool.submit(attr, *args, **kw)
    def getMod(self, m_name):
        return self.plugins[m_name][0]
    def _init(self):
        _init = self.getCall("_init")
        for m_name, m_init in _init:
            self.logger.debug(f'ModManager {m_name}.init')
            try:
                config = self.plugins[m_name][1]
                m_init(m_name, config, self, logging.getLogger(f'{self.name}.{m_name}'))
            except:
                self.logger.error(f'ModManager {m_name}.init \n{traceback.format_exc()}')
        self.logger.debug(f'ModManager plugins.init all done')
    def _exit(self):
        _exit = self.getCall("_exit")
        _exit.reverse() # 最先加载的模块应该最后退出
        self.threadPool.shutdown(wait=True) #关闭线程池
        self.logger.debug(f'ModManager threadPool.shutdown')
        for m_name, m_exit in _exit:
            self.logger.debug(f'ModManager {m_name}._exit')
            try:
                m_exit()
            except:
                self.logger.error(f'ModManager {m_name}.exit \n{traceback.format_exc()}')
        self.logger.debug(f'ModManager plugins.exit all done')
    def getConfOj(self, key):
        return self.plugins[key][1]
    def getModList(self):
        return tuple(map(lambda x: x[0], self.plist))

if __name__ == '__main__':
    test = ModManager('FDUXK')
    server = test.getMod("webserver")
    from flask import Blueprint
    admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
    @admin_bp.route('/')
    def index():
        return '<h1>Hello, this is admin blueprint</h1>'
    server.register_blueprint(admin_bp)
    server.wait()
