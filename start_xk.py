from ModManager import ModManager
XKmod = ModManager('FDUXK', max_workers=1)
server = XKmod.getMod("webserver")
server.wait()