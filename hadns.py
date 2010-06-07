# twistd launch script

import app
import config
import signal

from twisted.application import service
from twisted.internet import task

application = service.Application("hadns")

reloaded = [False]
def hup_receieved(n, stack):
  reloaded[0] = True
signal.signal(signal.SIGHUP, hup_receieved)

r = app.ReloadableHADNSHelper(lambda: app.HADNSApplication(config.Configuration("config.ini"), application))
r.start_new()

def check_reloaded():
  if not reloaded[0]:
    return
  reloaded[0] = False
  r.start_new()

t = task.LoopingCall(check_reloaded)
t.start(0.5)
