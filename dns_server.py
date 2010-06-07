from twisted.names import dns, server, common, authority

class DynamicZone(authority.FileAuthority):
  def __init__(self, soa_name, soa_record):
    common.ResolverBase.__init__(self)
    self._cache = {}
    self.records = {}
    self.soa = (soa_name, soa_record)

  def _name(self, name):
    return "%s.%s" % (name.lower(), self.soa[0])

  def add(self, name, record):
    self.records.setdefault(self._name(name), set()).add(record)

  def remove(self, name, record):
    name = self._name(name)
    if not self.records.has_key(name):
      return
  
    d = self.records[name]
    d.remove(record)
    if not d:
      del self.records[name]

  def __iter__(self):
    return iter(self.records)

  def __len__(self):
    return len(self.records)

def DNSServerFactory(zones):
  factory = server.DNSServerFactory(zones, None, []) # resolver])
  return dns.DNSDatagramProtocol(factory)

