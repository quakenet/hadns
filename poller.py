from twisted.internet import defer, protocol, reactor

class NullProtocol(protocol.Protocol):
  def connectionMade(self):
    self.transport.loseConnection()

class ConnectFactory(protocol.ClientFactory):
  def __init__(self, d):
    self.d = d

  def startedConnecting(self, connector):
    self.connector = connector

  def buildProtocol(self, connector):
    self.d.callback(None)
    return NullProtocol()

  def clientConnectionFailed(self, connector, reason):
    self.d.errback(reason)
    
class Poller(object):
  def __init__(self, (ip, port), timeout, add_fn, remove_fn):
    self.add_fn = add_fn
    self.remove_fn = remove_fn
    self.ip = ip
    self.port = port
    self.timeout = timeout
    self._previous_connect = None
    self.present = False

  def poll(self):
    if self._previous_connect:
      self._previous_connect.disconnect()
      self._previous_connect = None

    def callback(d):
      if self.present: return
      self.present = True

      self._previous_connect = None
      self.add_fn()
    def errback(d):
      if not self.present: return
      self.present = False

      self._previous_connect = None
      self.remove_fn()

    d = defer.Deferred()
    d.addCallbacks(callback, errback)
    self._previous_connect = reactor.connectTCP(self.ip, self.port, ConnectFactory(d), timeout=self.timeout)

  def __repr__(self):
    return "<Poller ip=%s port=%d>" % (self.ip, self.port)
