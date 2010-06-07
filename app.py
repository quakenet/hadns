import dns_server
import poller

from twisted.application import internet
from twisted.names import dns
from twisted.internet import task, reactor

def log(x): # TODO: tidy up
  print x

def add(zone, rr, dyn_zone, record):
  log("adding entry %s to zone: %s" % (rr, zone.name))
  dyn_zone.add(rr.name, record)

def remove(zone, rr, dyn_zone, record):
  log("removing entry %s from zone: %s" % (rr, zone.name))
  dyn_zone.remove(rr.name, record)

get_multiple = lambda d, n: dict((k, getattr(d, k)) for k in n)

class HADNSApplication(object):
  def __init__(self, config_file, application):
    self.config = config_file
    self.state = 0
    self.tasks = []
    self.server = None
    self.application = application

  def _assert_state(self, state):
    if self.state != state:
      raise Exception("Application in invalid state: %d vs %d" % (self.state, state))
    self.state+=1

  def start_polling(self):
    self._assert_state(0)
    self.state = 1

    max_interval = -1

    tasks = self.tasks
    zones = self.zones = []
    for zone in self.config.zones:
      soa = dns.Record_SOA(**get_multiple(zone, ("mname", "rname", "serial", "refresh", "retry", "expire", "minimum")))

      dyn_zone = dns_server.DynamicZone(zone.name, soa)

      for rr in zone.rrs:
        record = dns.Record_SRV(**get_multiple(rr, ("priority", "weight", "port", "target")))
        fn = lambda x: lambda zone=zone, rr=rr, dyn_zone=dyn_zone, record=record: x(zone=zone, rr=rr, dyn_zone=dyn_zone, record=record)

        p = poller.Poller((rr.target, rr.port), timeout=rr.timeout, add_fn=fn(add), remove_fn=fn(remove))
        t = task.LoopingCall(p.poll)
        t.start(rr.interval)
        self.tasks.append(t)
        max_interval = max(max_interval, rr.interval)

      zones.append(dyn_zone)

    if max_interval == -1:
      raise Exception("No RR's defined!")
    self.max_interval = max_interval

  def listen(self):
    self._assert_state(1)

    self.server = internet.UDPServer(self.config.port, dns_server.DNSServerFactory(self.zones), interface=self.config.interface)
    self.server.setServiceParent(self.application)

  def stop(self):
    while self.tasks:
      self.tasks.pop().stop()

    if self.server:
      self.server.stopService()
      self.server = None

class ReloadableHADNSHelper(object):
  def __init__(self, start_app):
    self.start_app = start_app
    self.d = None
    self.app = None
    self.new_app = None

  def start_new(self):
    if self.d:
      self.d.cancel()
      self.d = None
      self.new_app.stop()
      self.new_app = None

    try:
      self.new_app = self.start_app()
    except:
      traceback.print_exc()
      return

    self.new_app.start_polling()

    def start_listening():
      self.d = None
      if self.app:
        self.app.stop()

      reactor.callLater(0, self.new_app.listen)
      self.app = self.new_app
      self.new_app = None

    self.d = reactor.callLater(self.new_app.max_interval, start_listening)

