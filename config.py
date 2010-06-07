import collections
import ConfigParser

Zone = collections.namedtuple("Zone", ("name", "rrs", "serial", "refresh", "retry", "expire", "minimum", "rname", "mname"))
RR = collections.namedtuple("RR", ("name", "interval", "timeout", "target", "port", "weight", "priority"))

def get_all(p, section, entries, defaults={}):
  type_map = {
    "s": p.get,
    "i": p.getint,
  }
  def fn():
    for x in entries:
      f = x.find(":")
      type = "s"
      if f > -1:
        type = x[:f]
        x = x[f+1:]

      if defaults and not p.has_option(section, x) and defaults.has_key(x):
        yield (x, defaults[x])
      else:
        yield (x, type_map[type](section, x))

  return dict(fn())

class Configuration(object):
  def __init__(self, filename="config.ini"):
    p = ConfigParser.ConfigParser()
    p.read(filename)

    self.port = p.getint("core", "port")
    self.interface = p.get("core", "interface")

    default_keys = "i:interval", "i:timeout", "i:weight", "i:priority"
    defaults = get_all(p, "defaults", default_keys)

    self.zones = []
    for zone_name in p.get("core", "zones").strip().split(" "):
      soa_args = get_all(p, zone_name, ("i:serial", "refresh", "retry", "expire", "minimum", "rname", "mname"))

      rrs = []
      for rr_section_name in p.get(zone_name, "rrs").strip().split(" "):
        r = get_all(p, rr_section_name, default_keys + ("name", "target", "i:port"), defaults=defaults)
        rrs.append(RR(**r))

      self.zones.append(Zone(name=zone_name, rrs=rrs, **soa_args))

  def __repr__(self):
    return "<Configuration zones=%s port=%d interface=%s>" % (repr(self.zones), self.port, repr(self.interface))

if __name__ == "__main__":
  print Configuration("config.ini")
