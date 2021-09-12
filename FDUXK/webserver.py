from http import server
from flask import Flask, request
from werkzeug import serving
import threading
config, Manager, log, lock = 0,0,0,0 #保存宿主传递的环境 分别为配置文件， 模块管理器，日志，全局线程锁
def _default_config(root, name): #返回默认配置文件 载入时被调用 root为数据文件根目录 name为当前模块名称
    return {
        'modInformation':{ #该模块的信息
            'Name': 'BaseMod websever',
            'Author': 'Limour @limour.top',
            'Version': '1.1',
            'description': 'A flask websever for all mods'
        },
        'priority':-9998, # 模块加载和调用的优先级，越大越先，默认为0
        'host': '0.0.0.0',
        'port': 12021,
        'threaded': False,
        'processes': 1
    }

def _init(m_name, _config, _Manager, _log): #载入时被调用
    global config, Manager, log, lock
    config, Manager, log, lock = _config, _Manager, _log, _Manager.threading_lock #保存宿主传递的环境
    global server, app
    run_simple(config['host'], config['port'], app,
                threaded=config['threaded'], processes=config['processes'])
    run()
def _exit():
    server.shutdown()

def server_run():
    # log.debug('starting server')
    server.serve_forever()

serverT = threading.Thread(target=server_run, daemon=True)
app = Flask(__name__, static_folder=None)
app.jinja_env.variable_start_string = '[{'
app.jinja_env.variable_end_string = '}]'
serverT.ctx = app.app_context()
serverT.ctx.push()

# @app.before_request 
# def before_request(): # https://blog.csdn.net/qq_43224338/article/details/106699451
#     if request.blueprint is not None:
#         bp = app.blueprints[request.blueprint]
#         if bp.jinja_loader is not None:
#             newsearchpath = bp.jinja_loader.searchpath + app.jinja_loader.searchpath
#             app.jinja_loader.searchpath = newsearchpath
#         else:
#             app.jinja_loader.searchpath = app.jinja_loader.searchpath[-1:]
#     else:
#         app.jinja_loader.searchpath = app.jinja_loader.searchpath[-1:]

def register_blueprint(bp):
    global server, app
    app.register_blueprint(bp)
    
def run():
    serverT.start()
    return serverT

def wait(timeout = None):
    serverT.join(timeout)

def _run():
    app.run(host=config['host'], port=config['port'])

def run_simple(
    hostname: str,
    port: int,
    application,
    use_reloader: bool = False,
    use_debugger: bool = False,
    use_evalex: bool = True,
    extra_files = None,
    exclude_patterns = None,
    reloader_interval: int = 1,
    reloader_type: str = "auto",
    threaded: bool = False,
    processes: int = 1,
    request_handler = None,
    static_files = None,
    passthrough_errors: bool = False,
    ssl_context = None,
) -> None:

    if not isinstance(port, int):
        raise TypeError("port must be an integer")

    def log_startup(sock: serving.socket.socket) -> None:
        all_addresses_message = (
            " * Running on all addresses.\n"
            "   WARNING: This is a development server. Do not use it in"
            " a production deployment."
        )

        if sock.family == serving.af_unix:
            serving._log("info", " * Running on %s (Press CTRL+C to quit)", hostname)
        else:
            if hostname == "0.0.0.0":
                serving._log("warning", all_addresses_message)
                display_hostname = serving.get_interface_ip(serving.socket.AF_INET)
            elif hostname == "::":
                serving._log("warning", all_addresses_message)
                display_hostname = serving.get_interface_ip(serving.socket.AF_INET6)
            else:
                display_hostname = hostname

            if ":" in display_hostname:
                display_hostname = f"[{display_hostname}]"

            serving._log(
                "info",
                " * Running on %s://%s:%d/ (Press CTRL+C to quit)",
                "http" if ssl_context is None else "https",
                display_hostname,
                sock.getsockname()[1],
            )

    def inner() -> None:
        try:
            fd: serving.t.Optional[int] = int(serving.os.environ["WERKZEUG_SERVER_FD"])
        except (LookupError, ValueError):
            fd = None
        global server
        server = serving.make_server(
            hostname,
            port,
            application,
            threaded,
            processes,
            request_handler,
            passthrough_errors,
            ssl_context,
            fd=fd,
        )
        if fd is None:
            log_startup(server.socket)

    if use_reloader:
        # If we're not running already in the subprocess that is the
        # reloader we want to open up a socket early to make sure the
        # port is actually available.
        if not serving.is_running_from_reloader():
            if port == 0 and not serving.can_open_by_fd:
                raise ValueError(
                    "Cannot bind to a random port with enabled "
                    "reloader if the Python interpreter does "
                    "not support socket opening by fd."
                )

            # Create and destroy a socket so that any exceptions are
            # raised before we spawn a separate Python interpreter and
            # lose this ability.
            address_family = serving.select_address_family(hostname, port)
            server_address = serving.get_sockaddr(hostname, port, address_family)
            s = serving.socket.socket(address_family, serving.socket.SOCK_STREAM)
            s.setsockopt(serving.socket.SOL_SOCKET, serving.socket.SO_REUSEADDR, 1)
            s.bind(server_address)
            s.set_inheritable(True)

            # If we can open the socket by file descriptor, then we can just
            # reuse this one and our socket will survive the restarts.
            if serving.can_open_by_fd:
                serving.os.environ["WERKZEUG_SERVER_FD"] = str(s.fileno())
                s.listen(serving.LISTEN_QUEUE)
                log_startup(s)
            else:
                s.close()
                if address_family == serving.af_unix:
                    server_address = serving.t.cast(str, server_address)
                    serving._log("info", "Unlinking %s", server_address)
                    serving.os.unlink(server_address)

        from werkzeug._reloader import run_with_reloader as _rwr

        _rwr(
            inner,
            extra_files=extra_files,
            exclude_patterns=exclude_patterns,
            interval=reloader_interval,
            reloader_type=reloader_type,
        )
    else:
        inner()
