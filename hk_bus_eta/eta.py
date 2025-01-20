"""
This module implements the main functionality of hk-bus-eta

Author: Chun Law
Github: https://github.com/chunlaw
"""

__author__ = "Chun Law"
__email__ = "chunlaw@rocketmail.com"
__status__ = "production"

import requests
import time
from datetime import datetime, timezone
import re
import hashlib


def get_platform_display(plat, lang):
  number = int(plat) if isinstance(plat, str) else plat
  if number < 0 or number > 20:
    return ("Platform {}" if lang == "en" else "{}號月台").format(number)
  if number == 0:
    return "⓿"
  if number > 10:
    return chr(9451 + (number - 11))
  return chr(10102 + (number - 1))


class HKEta:
  holidays = None
  route_list = None
  stop_list = None
  stop_map = None

  def __init__(self):
    md5 = requests.get(
        "https://hkbus.github.io/hk-bus-crawling/routeFareList.md5").text
    r = requests.get(
        "https://hkbus.github.io/hk-bus-crawling/routeFareList.min.json")
    m = hashlib.md5()
    m.update(r.text.encode('utf-8'))
    if md5 != m.hexdigest():
      raise Exception("Error in accessing hk-eta-db, md5sum not match")
    db = r.json()
    self.holidays, self.route_list, self.stop_list, self.stop_map = db[
        "holidays"], db["routeList"], db["stopList"], db["stopMap"]

  # 0-indexed seq
  def getEtas(self, route_id, seq, language):
    routeEntry = self.route_list[route_id]
    route, stops, bound = routeEntry['route'], routeEntry['stops'], routeEntry['bound']
    dest, service_type, co, nlb_id, gtfs_id = routeEntry['dest'], routeEntry[
        'serviceType'], routeEntry['co'], routeEntry["nlbId"], routeEntry['gtfsId']
    _etas = []
    for company_id in co:
      if company_id == "kmb" and "kmb" in stops:
        _etas.extend(self.kmb(
            route=route,
            stop_id=stops["kmb"][seq],
            bound=bound["kmb"],
            seq=seq, co=co,
            service_type=service_type
        ))
      elif company_id == "ctb" and "ctb" in stops:
        _etas.extend(self.ctb(
            stop_id=stops['ctb'][seq], route=route, bound=bound['ctb'], seq=seq
        ))
      elif company_id == "nlb" and "nlb" in stops:
        _etas.extend(self.nlb(
            stop_id=stops['nlb'][seq], nlb_id=nlb_id
        ))
      elif company_id == "lrtfeeder" and "lrtfeeder" in stops:
        _etas.extend(self.lrtfeeder(
            stop_id=stops['lrtfeeder'][seq], route=route, language=language
        ))
      elif company_id == "mtr" and "mtr" in stops:
        _etas.extend(self.mtr(
            stop_id=stops['mtr'][seq], route=route, bound=bound["mtr"]
        ))
      elif company_id == "lightRail" and "lightRail" in stops:
        _etas.extend(self.lightrail(
            stop_id=stops['lightRail'][seq], route=route, dest=dest
        ))
      elif company_id == "gmb" and "gmb" in stops:
        _etas.extend(
            self.gmb(
                stop_id=stops["gmb"][seq],
                gtfs_id=gtfs_id,
                seq=seq,
                bound=bound["gmb"]))

    return _etas

  def kmb(self, stop_id, route, seq, service_type, co, bound):
    data = requests.get(
        "https://data.etabus.gov.hk/v1/transport/kmb/eta/{}/{}/{}".format(
            stop_id, route, service_type)).json()['data']
    data = list(filter(lambda e: 'eta' in e and e['dir'] == bound, data))
    data.sort(key=lambda e: abs(seq - e['seq']))
    data = [e for e in data if e['seq'] == data[0]['seq']]
    data = list(filter(lambda e: len(co) > 1 or service_type ==
                e['service_type'] or e['seq'] == seq + 1, data))
    return [{
        "eta": e['eta'],
        "remark": {
            "zh": e['rmk_tc'],
            "en": e['rmk_en']
        },
        "co": "kmb"
    } for e in data]

  def ctb(self, stop_id, route, bound, seq):
    data = requests.get(
        "https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{}/{}".format(
            stop_id, route)).json()['data']
    data = list(filter(lambda e: 'eta' in e and e['dir'] in bound, data))
    data.sort(key=lambda e: abs(seq - e['seq']))
    data = [e for e in data if e['seq'] == data[0]['seq']]
    return [{
        "eta": e['eta'],
        "remark": {
            "zh": e['rmk_tc'],
            "en": e['rmk_en']
        },
        "co": "ctb"
    }for e in data]

  def nlb(self, stop_id, nlb_id):
    try:
      data = requests.post(
          "https://rt.data.gov.hk/v1/transport/nlb/stop.php?action=estimatedArrivals",
          json={
              "routeId": nlb_id,
              "stopId": stop_id,
              "language": "zh"},
          headers={
              "Content-Type": "text/plain"}).json()["estimatedArrivals"]
      data = list(filter(lambda e: 'estimatedArrivalTime' in e, data))
      return [{
          "eta": e['estimatedArrivalTime'].replace(' ', 'T') + ".000+08:00",
          "remark": {
              "zh": "",
              "en": ""
          },
          "co": "nlb"
      } for e in data]
    except Exception as e:
      return []

  def lrtfeeder(self, stop_id, route, language):
    data = requests.post(
        "https://rt.data.gov.hk/v1/transport/mtr/bus/getSchedule",
        json={
            "language": language,
            "routeName": route},
        headers={
            "Content-Type": "application/json"}).json()['busStop']
    data = list(filter(lambda e: e["busStopId"] == stop_id, data))
    ret = []
    for buses in data:
      for bus in buses['bus']:
        remark = ""
        if bus["busRemark"] is not None:
          remark = bus["busRemark"]
        elif bus["isScheduled"] == 1:
          remark = "Scheduled" if language == "en" else "預定班次"
        delta_second = int(bus["departureTimeInSecond"] if bus['arrivalTimeInSecond']
                           == "108000" else bus["arrivalTimeInSecond"])
        dt = datetime.fromtimestamp(time.time() + delta_second + 8 * 3600)

        ret.append({
            "eta": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "remark": {
                language: remark
            },
            "co": "lrtfeeder"
        })
    return ret

  def mtr(self, stop_id, route, bound):
    res = requests.get(
        "https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={}&sta={}".format(
            route, stop_id)).json()
    data, status = res["data"], res["status"]

    if status == 0:
      return []
    ret = []
    for e in data["{}-{}".format(route, stop_id)
                  ]["UP" if bound[-2:1] == "U" else "DOWN"]:
      ret.append({
          "eta": e["time"].replace(" ", "T") + "+08:00",
          "remark": {
              "zh": get_platform_display(e["plat"], "zh"),
              "en": get_platform_display(e["plat"], "en")
          },
          "co": "mtr"
      })
    return ret

  def lightrail(self, stop_id, route, dest):
    platform_list = requests.get(
        "https://rt.data.gov.hk/v1/transport/mtr/lrt/getSchedule?station_id={}".format(stop_id[2:])).json()["platform_list"]
    ret = []
    for platform in platform_list:
      route_list, platform_id = platform["route_list"], platform["platform_id"]
      for e in route_list:
        route_no, dest_ch, dest_en, stop, time_en = e["route_no"], e[
            "dest_ch"], e["dest_en"], e["stop"], e["time_en"]
        if route == route_no and (
                dest_ch == dest["zh"] or "Circular" in dest_en) and stop == 0:
          waitTime = 0
          if time_en.lower() == "arriving" or time_en.lower() == "departing" or time_en == "-":
            waitTime = 0
          else:
            waitTime = int(re.search(r'\d+', time_en).group())
          dt = datetime.fromtimestamp(time.time() + waitTime + 8 * 3600)
          ret.append({
              "eta": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
              "remark": {
                  "zh": get_platform_display(platform_id, "zh"),
                  "en": get_platform_display(platform_id, "en")
              },
              "co": "lightrail"
          })
    return ret

  def gmb(self, gtfs_id, stop_id, bound, seq):
    data = requests.get(
        "https://data.etagmb.gov.hk/eta/route-stop/{}/{}".format(gtfs_id, stop_id)).json()["data"]
    data = list(
        filter(
            lambda e: (
                e['route_seq'] == 1 and bound == "O") or (
                e['route_seq'] == 2 and bound == "I"),
            data))
    data = list(filter(lambda e: e["stop_seq"] == seq + 1, data))
    ret = []
    for e in data:
      etas = e["eta"]
      for eta in etas:
        ret.append({
            "eta": eta["timestamp"],
            "remark": {
                "zh": eta["remarks_tc"],
                "en": eta["remarks_en"],
            },
            "co": "gmb"
        })
    return ret


if __name__ == "__main__":
  hketa = HKEta()
  route_ids = list(hketa.route_list.keys())
  print(route_ids[0:10])
