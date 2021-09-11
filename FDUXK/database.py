config, Manager, log, lock = 0,0,0,0 #保存宿主传递的环境 分别为配置文件， 模块管理器，日志，全局线程锁
def _default_config(root, name): #返回默认配置文件 载入时被调用 root为数据文件根目录 name为当前模块名称
    return {
        'modInformation':{ #该模块的信息
            'Name': 'BaseMod database',
            'Author': 'Limour @limour.top',
            'Version': '1.1',
            'description': 'A sqlite3 database for all mods'
        },
        'priority':9999, # 模块加载和调用的优先级，越大越先，默认为0
        'db_path': f'{root}/{name}.db'
    }

def _init(m_name, _config, _Manager, _log): #载入时被调用
    global config, Manager, log, lock, db
    config, Manager, log, lock = _config, _Manager, _log, _Manager.threading_lock #保存宿主传递的环境
    db = DataBase(config["db_path"])
    log.debug(f'{config["db_path"]} connected')

def _exit():
    db.commit()
    db.close()
    log.debug(f'{config["db_path"]} committed and closed')

import threading, sqlite3
from typing import Iterable
class DB_Table(object):
    def __init__(self, name, cursor:sqlite3.Cursor, lock, datab:sqlite3.Connection):
        self.name = name
        self.cursor = cursor
        self.lock = lock
        self.datab = datab
    def insert(self, col, values):
        with self.lock:
            return self.cursor.execute(f'INSERT INTO {self.name} ({col}) VALUES ({values})')
    def select(self, col):
        with self.lock:
            return tuple(self.cursor.execute(f'SELECT {col} from {self.name}'))
    def select_(self, col, where):
        with self.lock:
            return tuple(self.cursor.execute(f'SELECT {col} from {self.name} where {where}'))
    def slip(self, col, ord, range_start, range_size):
        with self.lock:
            return tuple(self.cursor.execute(f'SELECT {col} from {self.name} order by {ord} limit {range_start},{range_size}'))
    def update(self, where, _set):
        with self.lock:
            return self.cursor.execute(f'UPDATE {self.name} set {_set} where {where}')
    def delete(self, where):
        with self.lock:
            return self.cursor.execute(f'DELETE from {self.name} where {where}')
    def show(self):
        cursor = self.select('*')
        for row in cursor:
            print(*row)
    def replace(self, col, f_value:str, values:Iterable, commit=False):
        with self.lock:
            res = self.cursor.execute(f'REPLACE INTO {self.name} ({col}) VALUES ({f_value})', values)
            if commit: self.datab.commit()
            return res
    def commit(self):
        with self.lock:
            return self.datab.commit()

class DataBase(object):
    def __init__(self, path):
        self.lock = threading.Lock()
        with self.lock:
            self.datab = sqlite3.connect(path, check_same_thread=False)
            self.cursor =  self.datab.cursor() 
    def close(self):
        with self.lock:
            self.datab.close()
    def commit(self):
        with self.lock:
            self.datab.commit()
    def execute(self, sql):
        with self.lock:
            return self.cursor.execute(sql)
    def create(self, name, structure):
        with self.lock:
            tmp = self.cursor.execute("select count(*) from sqlite_master where type='table' and name = ?", (name,))
            if next(tmp)[0] == 0: tmp = self.cursor.execute(f'CREATE TABLE {name} ({structure});')
            if tmp is not None:
                return self.getTable(name)
    def getTable(self, name):
        return DB_Table(name, self.cursor, self.lock, self.datab)