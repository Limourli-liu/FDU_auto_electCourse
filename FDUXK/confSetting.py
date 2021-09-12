from flask import Blueprint, jsonify, render_template, request
import json, os
app = Blueprint('confSetting', __name__, url_prefix='/mod/confSetting',
                template_folder='confSetting/templates',
                static_folder='confSetting/static',
                static_url_path='/mod/confSetting/static'
                )

@app.route('/')
def index():
    return render_template('confSetting_index.html')

@app.route('/getModList')
def getModList():
    Mlist = Manager.getModList()
    res = {"modlist": Mlist,
    "activeName": Mlist[0]}
    return jsonify(res)
@app.route('/ModConf/<modname>/', methods=['GET'])
def getModConf(modname):
    value = Manager.getConfOj(modname)
    value = json.dumps(value, indent=4, ensure_ascii=False)
    return jsonify({"text": value})
@app.route('/ModConf/<modname>/', methods=["DELETE"])
def delModConf(modname):
    value = Manager.getConfOj(modname)
    if os.path.exists(value.path):
        os.remove(value.path)
    return jsonify({"status":  not os.path.exists(value.path)})
@app.route('/ModConf/<modname>/', methods=["POST"])
def setModConf(modname):
    newConf = request.get_json()
    newConf = json.loads(newConf["text"])
    print(newConf)
    value = Manager.getConfOj(modname)
    value.setNew(newConf)
    value.save()
    return "success"


config, Manager, log, lock = 0,0,0,0 #保存宿主传递的环境 分别为配置文件， 模块管理器，日志，全局线程锁
def _default_config(root, name): #返回默认配置文件 载入时被调用 root为数据文件根目录 name为当前模块名称
    return {
        'modInformation':{ #该模块的信息
            'Name': 'BaseMod Mod Confing editor',
            'Author': 'Limour @limour.top',
            'Version': '1.0',
            'description': 'use web editor to edit mod confing file'
        },
    }

def _init(m_name, _config, _Manager, _log): #载入时被调用
    global config, Manager, log, lock, db
    config, Manager, log, lock = _config, _Manager, _log, _Manager.threading_lock #保存宿主传递的环境
    server = Manager.getMod("webserver")# 注册web页面
    server.register_blueprint(app)