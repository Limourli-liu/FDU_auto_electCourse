from flask import Blueprint, jsonify, render_template, request
app = Blueprint('editor', __name__, url_prefix='/mod/editor',
                template_folder='editor/templates',
                static_folder='editor/static',
                static_url_path='/mod/editor/static'
                )

@app.route('/')
def index():
    api = request.args.get('api', "/mod/editor/test/test/", type=str)
    title = request.args.get('ti', "Editor", type=str)
    # log.info(f"{api=}  {title=}")
    return render_template('editor_index.html', api=api, title=title)

@app.route("/test/<name>/", methods=['GET'])
def test_GET(name):
    value = db.select_("value", f"globalVar='{name}'")
    if value:
        value = value[0][0]
    else:
        value = "{'text': 'hello world'}"
    return jsonify(eval(value))
@app.route("/test/<name>/", methods=['POST'])
def test_SET(name):
    res = str(request.get_json())
    res = db.replace("globalVar,value", "?,?", (name, res), commit=True)
    return "success"

config, Manager, log, lock = 0,0,0,0 #保存宿主传递的环境 分别为配置文件， 模块管理器，日志，全局线程锁
def _default_config(root, name): #返回默认配置文件 载入时被调用 root为数据文件根目录 name为当前模块名称
    return {
        'modInformation':{ #该模块的信息
            'Name': 'BaseMod editor',
            'Author': 'Limour @limour.top',
            'Version': '1.0',
            'description': 'A simple web editor'
        },
    }

def _init(m_name, _config, _Manager, _log): #载入时被调用
    global config, Manager, log, lock, db
    config, Manager, log, lock = _config, _Manager, _log, _Manager.threading_lock #保存宿主传递的环境
    _db = Manager.getMod('database').db # 调用BaseMod database
    server = Manager.getMod("webserver")# 注册web页面
    server.register_blueprint(app)
    db = _db.create(m_name, 'globalVar TEXT PRIMARY KEY, value TEXT')