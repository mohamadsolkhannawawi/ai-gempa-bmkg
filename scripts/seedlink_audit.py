#!/usr/bin/env python3
"""
seedlink_audit.py - Audit bukti-per-bukti ketersediaan SeedLink publik untuk stasiun Indonesia.

Fase:
  1  Bukti web primer (forum GFZ, EarthScope, GeoShake, FDSN): simpan teks + cuplikan kata kunci
  2  DNS / TCP / HELLO (+TLS untuk port 18500) per endpoint
  3  INFO STREAMS per server: jumlah stasiun, jaringan, lat/lon di XML?, kanal, dan UMUR data (end_time)
  4  Koordinat dari FDSN station -> irisan dengan stasiun yang LIVE di tiap server SeedLink
  5  Uji streaming live (latensi, sampling rate, kanal, gap) + simpan miniSEED (rekaman 512 byte asli)

Keamanan: hanya host:port pada daftar di bawah. Tanpa port scanning, tanpa kredensial.
Dependensi: python3.8+ SAJA (v2: tanpa obspy; SeedLink v3 lewat socket mentah, aman di Windows).

Contoh:
  python3 seedlink_audit.py
  python3 seedlink_audit.py --skip-live --skip-web
  python3 seedlink_audit.py --geoshake-fdsn https://api.geoshake.org/fdsnws/station/1/query --geocode
  python3 seedlink_audit.py --live "rtserve.earthscope.org:18000|II|KAPI|BH?,EN?" --live-seconds 120
"""
import argparse
import html as htmllib
import ipaddress
import json
import os
import re
import socket
import ssl
import statistics
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
TIMEOUT = 15
UA = "seedlink-audit/1.0 (academic thesis research; contact: researcher)"

BBOX = dict(minlatitude=-11.5, maxlatitude=6.5, minlongitude=94.5, maxlongitude=141.5)

# (host, port, tls)
ENDPOINTS = [
    ("seedlink.geoshake.org", 18000, False),
    ("rtserve.earthscope.org", 18000, False),
    ("rtserve.earthscope.org", 18500, True),
    ("rtserve.iris.washington.edu", 18000, False),
    ("geofon.gfz.de", 18000, False),
    ("auspass.edu.au", 18000, False),
    ("seedlink.resif.fr", 18000, False),   # diharapkan NXDOMAIN
    ("rtserve.resif.fr", 18000, False),
    ("eida.bgr.de", 18000, False),
    ("geof.bmkg.go.id", 18000, False),     # diharapkan TIMEOUT
]

# server yang diambil inventarisnya (INFO STREAMS)
INVENTORY_SERVERS = [
    "seedlink.geoshake.org:18000",
    "rtserve.earthscope.org:18000",
    "auspass.edu.au:18000",
    "rtserve.resif.fr:18000",
    "eida.bgr.de:18000",
    "geofon.gfz.de:18000",
]

FDSN_BASES = {
    "EARTHSCOPE": "https://service.earthscope.org/fdsnws/station/1/query",
    "GFZ": "https://geofon.gfz.de/fdsnws/station/1/query",
}

GE_INDO = ["BBJI", "BKB", "BKNI", "BNDI", "CISI", "FAKI", "GENI", "GSI", "JAGI", "LHMI", "LUWI",
           "MMRI", "MNAI", "PLAI", "PMBI", "PMBT", "SANI", "SAUI", "SMRI", "SOEI", "TNTI",
           "TOLI", "TOLI2", "UGM", "YOGI"]
WATCH_CODES = set(GE_INDO) | {"KAPI", "WRAB", "BKNI"}

WEB_SOURCES = [
    ("gfz_forum",
     "https://geofon.gfz.de/forum/t/no-data-for-geofon-stations-in-indonesia/43807",
     ["BMKG", "Indonesia", "28 Aug", "04:55", "internal", "redistribut", "restor", "SeedLink", "FDSNWS"]),
    ("earthscope_news",
     "https://www.earthscope.org/news/seedlink-service-is-moving-as-part-of-our-cloud-transition/",
     ["rtserve.earthscope.org", "18500", "TLS", "version 4", "v4", "18000", "iris.washington.edu", "May"]),
    ("geoshake_api", "https://api.geoshake.org/",
     ["seedlink", "18000", "GW", "anonym", "fdsnws", "station", "_LNZ", "_ENZ"]),
    ("fdsn_geoshake", "https://www.fdsn.org/datacenters/detail/GEOSHAKE/",
     ["seedlink", "18000", "GW", "GEOSHAKE", "2026"]),
    ("fdsn_auspass", "https://www.fdsn.org/datacenters/detail/AusPass/",
     ["seedlink", "18000", "fdsnws", "AusPass"]),
]

CLOUDFLARE_NETS = [ipaddress.ip_network(n) for n in (
    "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13", "162.158.0.0/15", "141.101.64.0/18",
    "108.162.192.0/18", "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "188.114.96.0/20", "190.93.240.0/20", "197.234.240.0/22", "198.41.128.0/17", "131.0.72.0/22",
    "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32")]

OUT = None
R = {}


def log(msg=""):
    line = str(msg)
    print(line, flush=True)
    if OUT:
        with open(os.path.join(OUT, "audit.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")


def save(name, text):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def strip_html(s):
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", htmllib.unescape(s)).strip()


def snippets(text, kw, width=140, maxn=3):
    out, low, k, pos = [], text.lower(), kw.lower(), 0
    while len(out) < maxn:
        i = low.find(k, pos)
        if i < 0:
            break
        out.append(text[max(0, i - width // 2): i + width // 2].replace("\n", " "))
        pos = i + max(len(k), width)
    return out


def phase1_web():
    log("\n" + "=" * 70 + "\nFASE 1: BUKTI SUMBER PRIMER (WEB)\n" + "=" * 70)
    res = {}
    for name, url, kws in WEB_SOURCES:
        posts = []
        status, body = http_get(url)
        text = strip_html(body) if status == 200 else ""
        if name == "gfz_forum":
            s2, j = http_get(url + ".json")
            if s2 == 200:
                try:
                    data = json.loads(j)
                    for p in data.get("post_stream", {}).get("posts", []):
                        posts.append({"created_at": p.get("created_at"), "user": p.get("username"),
                                      "text": strip_html(p.get("cooked", ""))})
                    text = "\n".join(f"[{p['created_at']}] {p['user']}: {p['text']}" for p in posts)
                except Exception as e:
                    log(f"  (json forum gagal diparse: {e})")
        path = save(f"web_{name}.txt", f"URL: {url}\nHTTP: {status}\n\n{text}")
        entry = {"url": url, "http": status, "chars": len(text), "file": path, "hits": {}}
        log(f"\n[{name}] HTTP={status} chars={len(text)}  -> {path}")
        if posts:
            entry["post_dates"] = [p["created_at"] for p in posts]
            log(f"  tanggal posting: {entry['post_dates'][:10]}")
        for kw in kws:
            sn = snippets(text, kw)
            entry["hits"][kw] = len(sn)
            if sn:
                log(f"  '{kw}': {len(sn)} cuplikan, mis.: ...{sn[0]}...")
            else:
                log(f"  '{kw}': TIDAK DITEMUKAN")
        res[name] = entry
    R["phase1_web"] = res


def check_endpoint(host, port, tls):
    r = {"host": host, "port": port, "tls": tls, "dns": None, "ips": [], "tcp": None,
         "connect_ms": None, "hello": None, "tls_info": None, "error": None}
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        r["ips"] = sorted({i[4][0] for i in infos})
        r["dns"] = "OK"
    except socket.gaierror as e:
        r["dns"], r["error"] = "NXDOMAIN/ERR", str(e)
        return r
    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
    except socket.timeout:
        r["tcp"] = "TIMEOUT"
        return r
    except ConnectionRefusedError:
        r["tcp"] = "REFUSED"
        return r
    except OSError as e:
        r["tcp"], r["error"] = "ERROR", str(e)
        return r
    r["tcp"] = "OPEN"
    r["connect_ms"] = round((time.time() - t0) * 1000)
    try:
        if tls:
            s = ssl.create_default_context().wrap_socket(s, server_hostname=host)
            try:
                cert = s.getpeercert()
                subj = dict(x[0] for x in cert.get("subject", ()))
                r["tls_info"] = {"version": s.version(), "subject_cn": subj.get("commonName"),
                                 "not_after": cert.get("notAfter")}
            except Exception:
                r["tls_info"] = {"version": s.version()}
        s.settimeout(TIMEOUT)
        s.sendall(b"HELLO\r\n")
        data, t_end = b"", time.time() + TIMEOUT
        while data.count(b"\n") < 2 and time.time() < t_end:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
        r["hello"] = data.decode("utf-8", "replace").strip().splitlines()[:2]
    except ssl.SSLError as e:
        r["error"] = f"TLS: {e}"
    except Exception as e:
        r["error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            s.close()
        except Exception:
            pass
    return r


def phase2_connectivity():
    log("\n" + "=" * 70 + "\nFASE 2: KONEKTIVITAS + HELLO\n" + "=" * 70)
    rows = []
    for host, port, tls in ENDPOINTS:
        r = check_endpoint(host, port, tls)
        rows.append(r)
        log(f"{host}:{port}{' [TLS]' if tls else ''}  DNS={r['dns']} TCP={r['tcp']} "
            f"HELLO={r['hello']} {('ERR=' + r['error']) if r['error'] else ''}")
    for r in rows:
        try:
            r["cloudflare_ips"] = [ip for ip in r["ips"]
                                   if any(ipaddress.ip_address(ip) in n for n in CLOUDFLARE_NETS)]
        except ValueError:
            r["cloudflare_ips"] = []
        if r["cloudflare_ips"]:
            log(f"   >>> {r['host']}: {len(r['cloudflare_ips'])}/{len(r['ips'])} IP di rentang Cloudflare")
    save("phase2_connectivity.json", json.dumps(rows, indent=2))
    R["phase2_connectivity"] = rows


def _readline(sock, deadline):
    buf = b""
    while not buf.endswith(b"\n"):
        if time.time() > deadline:
            raise socket.timeout("timeout menunggu baris respons")
        sock.settimeout(max(0.5, min(5.0, deadline - time.time())))
        try:
            c = sock.recv(1)
        except socket.timeout:
            continue
        if not c:
            raise ConnectionError("koneksi ditutup server")
        buf += c
    return buf.decode("utf-8", "replace").strip()


def _recv_exact(sock, n, deadline):
    buf = b""
    while len(buf) < n:
        if time.time() >= deadline:
            raise socket.timeout("deadline")
        sock.settimeout(max(0.5, min(5.0, deadline - time.time())))
        try:
            c = sock.recv(n - len(buf))
        except socket.timeout:
            continue
        if not c:
            raise ConnectionError("koneksi ditutup server")
        buf += c
    return buf


def sl_open(host, port, timeout=TIMEOUT, tls=False):
    s = socket.create_connection((host, port), timeout=timeout)
    if tls:
        s = ssl.create_default_context().wrap_socket(s, server_hostname=host)
    deadline = time.time() + timeout
    s.sendall(b"HELLO\r")
    hello = [_readline(s, deadline), _readline(s, deadline)]
    return s, hello


def ms_header(rec):
    """Parse header miniSEED v2 (512 byte)."""
    if len(rec) < 48 or rec[6:7] not in (b"D", b"R", b"Q", b"M"):
        return None
    end = ">"
    year = struct.unpack(">H", rec[20:22])[0]
    if not 1900 <= year <= 2200:
        end = "<"
        year = struct.unpack("<H", rec[20:22])[0]
        if not 1900 <= year <= 2200:
            return None
    doy, = struct.unpack(end + "H", rec[22:24])
    hh, mm, ss = rec[24], rec[25], rec[26]
    fract, = struct.unpack(end + "H", rec[28:30])
    nsamp, = struct.unpack(end + "H", rec[30:32])
    fac, mul = struct.unpack(end + "hh", rec[32:36])
    offset, = struct.unpack(end + "H", rec[44:46])
    if fac > 0 and mul > 0:
        rate = float(fac * mul)
    elif fac > 0 and mul < 0:
        rate = -float(fac) / mul
    elif fac < 0 and mul > 0:
        rate = -float(mul) / fac
    elif fac < 0 and mul < 0:
        rate = 1.0 / (fac * mul)
    else:
        rate = 0.0
    try:
        start = (datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=doy - 1, hours=hh, minutes=mm,
                                                              seconds=ss + fract * 1e-4))
    except Exception:
        return None
    clean = lambda b: b.decode("ascii", "replace").strip()
    return {"net": clean(rec[18:20]), "sta": clean(rec[8:13]), "loc": clean(rec[13:15]),
            "cha": clean(rec[15:18]), "start": start, "nsamp": nsamp, "rate": rate, "offset": offset,
            "end": start + timedelta(seconds=(nsamp / rate) if rate > 0 else 0)}


def sl_info(host, port, level="STREAMS", timeout=40, tls=False):
    """INFO <level> via SeedLink v3."""
    s, hello = sl_open(host, port, min(timeout, TIMEOUT), tls)
    try:
        deadline = time.time() + timeout
        s.sendall(f"INFO {level}\r".encode())
        parts = []
        while True:
            pkt = _recv_exact(s, 8, deadline)
            if pkt[:2] != b"SL":
                rest = b""
                try:
                    rest = s.recv(200)
                except Exception:
                    pass
                raise RuntimeError("respons INFO bukan paket SeedLink: " + repr((pkt + rest)[:80]))
            rec = _recv_exact(s, 512, deadline)
            h = ms_header(rec)
            if h is None:
                raise RuntimeError("rekaman INFO bukan miniSEED v2")
            parts.append(rec[h["offset"]: h["offset"] + h["nsamp"]])
            if pkt[:8] == b"SLINFO  ":
                break
        text = b"".join(parts).replace(b"\x00", b"").decode("utf-8", "replace").strip()
        return text, hello
    finally:
        try:
            s.close()
        except Exception:
            pass


def parse_sl_time(t):
    """'2026/10/05 12:30:01.00' -> datetime UTC."""
    try:
        t = t.strip().replace("-", "/")
        main, _, frac = t.partition(".")
        d = datetime.strptime(main, "%Y/%m/%d %H:%M:%S").replace(tzinfo=UTC)
        return d + timedelta(seconds=float("0." + frac)) if frac else d
    except Exception:
        return None


def parse_streams(xml_text):
    root = ET.fromstring(xml_text)
    stations, st_attrs, sm_attrs = {}, set(), set()
    for s in root.iter("station"):
        st_attrs |= set(s.attrib)
        chans, newest = set(), None
        for x in s.iter("stream"):
            sm_attrs |= set(x.attrib)
            chans.add(f"{x.get('location', '')}.{x.get('seedname', '')}")
            et = parse_sl_time(x.get("end_time", ""))
            if et and (newest is None or et > newest):
                newest = et
        stations[(s.get("network"), s.get("name"))] = {"channels": sorted(chans), "newest_end": newest}
    return stations, sorted(st_attrs), sorted(sm_attrs)


def age_s(dt):
    return None if dt is None else round((datetime.now(UTC) - dt).total_seconds(), 1)


INV = {}


def phase3_inventory():
    log("\n" + "=" * 70 + "\nFASE 3: INVENTARIS INFO STREAMS (SeedLink v3 mentah)\n" + "=" * 70)
    res = {}
    for server in INVENTORY_SERVERS:
        host, port = server.split(":")
        try:
            xml_text, hello = sl_info(host, int(port), "STREAMS")
            path = save(f"info_streams_{server.replace(':', '_')}.xml", xml_text)
            stations, st_attrs, sm_attrs = parse_streams(xml_text)
        except Exception as e:
            log(f"{server}: GAGAL {type(e).__name__}: {e}")
            res[server] = {"error": f"{type(e).__name__}: {e}"}
            continue
        INV[server] = stations
        nets = Counter(n for n, _ in stations)
        has_latlon = any(("lat" in a.lower() or "lon" in a.lower()) for a in st_attrs + sm_attrs)
        ages = [age_s(v["newest_end"]) for v in stations.values() if v["newest_end"]]
        res[server] = {"stations": len(stations), "networks": dict(nets.most_common()),
                       "station_attrs": st_attrs, "stream_attrs": sm_attrs, "xml_has_latlon": has_latlon,
                       "stations_with_end_time": len(ages),
                       "stations_fresh_lt_600s": sum(1 for a in ages if a is not None and a < 600),
                       "hello": hello, "file": path}
        log(f"\n{server}: {len(stations)} stasiun, {len(nets)} jaringan; XML memuat lat/lon? {has_latlon}")
        log(f"  atribut <station>: {st_attrs}")
        log(f"  atribut <stream> : {sm_attrs}")
        log(f"  jaringan terbesar: {nets.most_common(8)}")
        log(f"  stasiun dengan data < 10 menit: {res[server]['stations_fresh_lt_600s']}/{len(ages)}")
        if "IA" in nets:
            log(f"  >>> JARINGAN IA ADA: {nets['IA']} stasiun")
        if server.startswith("seedlink.geoshake.org"):
            gw = sorted(k for k in stations if k[0] == "GW")
            log("  contoh stasiun GW (10 pertama):")
            for k in gw[:10]:
                log(f"    {k}: {stations[k]['channels'][:6]}  umur={age_s(stations[k]['newest_end'])}s")
            res[server]["gw_sample"] = {f"{k[0]}.{k[1]}": stations[k]["channels"][:6] for k in gw[:10]}
    R["phase3_inventory"] = res


def fdsn_stations(base, params):
    url = f"{base}?{urllib.parse.urlencode({**params, 'level': 'station', 'format': 'text'})}"
    code, body = http_get(url)
    rows = []
    if code == 200:
        for line in body.splitlines():
            if not line or line.startswith("#"):
                continue
            p = line.split("|")
            if len(p) >= 4:
                try:
                    rows.append({"net": p[0], "sta": p[1], "lat": float(p[2]), "lon": float(p[3]),
                                 "start": p[6] if len(p) > 6 else "", "end": p[7] if len(p) > 7 else ""})
                except ValueError:
                    pass
    return code, url, rows


def in_bbox(lat, lon):
    return (BBOX["minlatitude"] <= lat <= BBOX["maxlatitude"]
            and BBOX["minlongitude"] <= lon <= BBOX["maxlongitude"])


def country_of(lat, lon):
    url = ("https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=3"
           f"&lat={lat}&lon={lon}")
    code, body = http_get(url, timeout=20)
    time.sleep(1.1)
    try:
        return json.loads(body).get("address", {}).get("country_code", "?").upper()
    except Exception:
        return "?"


def phase4_fdsn_intersection(args):
    log("\n" + "=" * 70 + "\nFASE 4: KOORDINAT FDSN x STASIUN LIVE\n" + "=" * 70)
    endafter = (datetime.now(UTC) - timedelta(days=args.active_days)).strftime("%Y-%m-%d")
    coords, fdsn_log = {}, {}
    for label, base in FDSN_BASES.items():
        code, url, rows = fdsn_stations(base, {**BBOX, "endafter": endafter})
        fdsn_log[label] = {"http": code, "url": url, "stations": len(rows),
                           "networks": dict(Counter(r["net"] for r in rows).most_common())}
        log(f"FDSN {label}: HTTP={code} stasiun aktif di bbox (endafter {endafter})={len(rows)} "
            f"jaringan={fdsn_log[label]['networks']}")
        for r in rows:
            coords.setdefault((r["net"], r["sta"]), (r["lat"], r["lon"], label))
    R["phase4_fdsn"] = fdsn_log
    log(f"Total stasiun unik (net,sta) di bbox: {len(coords)}")

    hits_all, inter = {}, {}
    for server, inv in INV.items():
        hits = sorted(set(inv) & set(coords))
        inter[server] = [{"net": n, "sta": s, "lat": coords[(n, s)][0], "lon": coords[(n, s)][1],
                          "channels": inv[(n, s)]["channels"][:8],
                          "age_s": age_s(inv[(n, s)]["newest_end"])} for n, s in hits]
        hits_all[server] = hits
        log(f"\n{server}: {len(hits)} stasiun LIVE yang koordinatnya masuk bbox "
            f"{dict(Counter(n for n, _ in hits))}")
        for h in inter[server][:60]:
            log(f"   {h['net']}.{h['sta']:<6} lat={h['lat']:.3f} lon={h['lon']:.3f} "
                f"umur_data={h['age_s']}s {h['channels'][:4]}")
    if args.geocode:
        log("\nGeocoding negara (Nominatim, maks 40 titik unik)...")
        seen = {}
        for server, lst in inter.items():
            for h in lst:
                key = (round(h["lat"], 2), round(h["lon"], 2))
                if key not in seen and len(seen) < 40:
                    seen[key] = country_of(h["lat"], h["lon"])
                h["country"] = seen.get(key, "?")
        for server, lst in inter.items():
            log(f"  {server}: " + str(Counter(h.get("country", "?") for h in lst)))
    R["phase4_intersection"] = inter

    where = defaultdict(list)
    for server, inv in INV.items():
        for (n, s) in inv:
            if s in WATCH_CODES:
                where[s].append(f"{server} -> {n}.{s} (umur_data={age_s(inv[(n, s)]['newest_end'])}s)")
    if not INV:
        log("\nPERHATIAN: tidak ada inventaris SeedLink (fase 3 gagal semua).")
    log("\nWatchlist (KAPI/WRAB/BKNI + 25 kode GE Indonesia) - ditemukan di server mana:")
    for code in sorted(WATCH_CODES):
        if not INV:
            log(f"   {code:<6}: TIDAK TERUJI (inventaris SeedLink gagal)")
        else:
            log(f"   {code:<6}: {where.get(code, 'TIDAK ADA di server mana pun')}")
    R["phase4_watchlist"] = ("TIDAK_TERUJI_inventaris_gagal" if not INV
                             else {k: where.get(k, []) for k in sorted(WATCH_CODES)})

    log("\nGeoShake: lokasi semua stasiun GW lewat FDSN (tanpa filter bbox)")
    if not args.geoshake_fdsn:
        log("   dilewati: beri --geoshake-fdsn <URL fdsnws-station GeoShake>")
        R["phase4_geoshake"] = {"skipped": True}
        return
    code, url, rows = fdsn_stations(args.geoshake_fdsn, {"network": "GW"})
    gw_in = [r for r in rows if in_bbox(r["lat"], r["lon"])]
    if "seedlink.geoshake.org:18000" not in INV:
        log("   PERHATIAN: inventaris SeedLink GeoShake tidak tersedia (fase 3 gagal)")
    live_gw = {k for k in INV.get("seedlink.geoshake.org:18000", {}) if k[0] == "GW"}
    meta_gw = {(r["net"], r["sta"]) for r in rows}
    log(f"   HTTP={code}  stasiun GW dengan metadata={len(rows)}  di dalam bbox Indonesia={len(gw_in)}  "
        f"live di SeedLink={len(live_gw)}  live TANPA metadata={len(live_gw - meta_gw)}")
    for r in gw_in[:40]:
        log(f"   {r['net']}.{r['sta']} lat={r['lat']:.3f} lon={r['lon']:.3f}")
    R["phase4_geoshake"] = {"http": code, "url": url, "with_metadata": len(rows),
                            "in_bbox": gw_in, "live": len(live_gw),
                            "live_without_metadata": len(live_gw - meta_gw)}


def live_test(server, net, sta, selectors, seconds, outdir):
    host, port = server.split(":")
    res = {"server": server, "station": f"{net}.{sta}", "selectors": selectors, "seconds": seconds}
    per = defaultdict(lambda: {"packets": 0, "samples": 0, "sampling_rate": None, "first_start": None,
                               "last_end": None, "gaps": 0, "_last_end": None})
    lags, raw, unparsed = [], [], 0
    t0 = time.time()
    s = None
    try:
        s, hello = sl_open(host, int(port))
        res["hello"] = hello
        deadline_cmd = time.time() + 30
        s.sendall(f"STATION  {sta} {net}\r".encode())
        r1 = _readline(s, deadline_cmd)
        replies = {"STATION": r1}
        if r1 != "OK":
            raise RuntimeError(f"STATION ditolak: {r1}")
        for sel in selectors:
            s.sendall(f"SELECT {sel}\r".encode())
            replies[f"SELECT {sel}"] = _readline(s, deadline_cmd)
        s.sendall(b"DATA\r")
        replies["DATA"] = _readline(s, deadline_cmd)
        res["command_replies"] = replies
        if replies["DATA"] != "OK":
            raise RuntimeError(f"DATA ditolak: {replies['DATA']}")
        s.sendall(b"END\r")
        end_at = time.time() + seconds
        while time.time() < end_at:
            try:
                pkt = _recv_exact(s, 520, end_at)
            except socket.timeout:
                break
            if pkt[:2] != b"SL":
                res["unexpected_text"] = repr(pkt[:60])
                break
            rec = pkt[8:]
            h = ms_header(rec)
            if h is None:
                unparsed += 1
                continue
            raw.append(rec)
            cid = f"{h['net']}.{h['sta']}.{h['loc']}.{h['cha']}"
            d = per[cid]
            d["packets"] += 1
            d["samples"] += h["nsamp"]
            d["sampling_rate"] = h["rate"]
            d["first_start"] = d["first_start"] or h["start"].isoformat()
            if d["_last_end"] is not None and h["rate"] > 0:
                if (h["start"] - d["_last_end"]).total_seconds() > 1.5 / h["rate"]:
                    d["gaps"] += 1
            d["_last_end"] = h["end"]
            d["last_end"] = h["end"].isoformat()
            lags.append((datetime.now(UTC) - h["end"]).total_seconds())
        try:
            s.sendall(b"BYE\r")
        except Exception:
            pass
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass
    res["elapsed_s"] = round(time.time() - t0, 1)
    res["packets"] = len(lags)
    res["unparsed_records"] = unparsed
    res["channels"] = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in per.items()}
    if lags:
        tail = lags[len(lags) // 2:] or lags
        res["latency_s"] = {"min": round(min(lags), 1), "median_all": round(statistics.median(lags), 1),
                            "median_second_half": round(statistics.median(tail), 1), "max": round(max(lags), 1)}
    if raw:
        fn = os.path.join(outdir, f"live_{net}_{sta}_{host}.mseed")
        with open(fn, "wb") as f:
            f.write(b"".join(raw))
        res["mseed"] = fn
    return res


def phase5_live(args):
    log("\n" + "=" * 70 + f"\nFASE 5: UJI STREAMING LIVE ({args.live_seconds}s per stasiun)\n" + "=" * 70)
    targets = defaultdict(list)
    for spec in args.live:
        server, net, sta, sels = spec.split("|")
        targets[(server, net, sta)] += sels.split(",")
    if not targets:
        for sel in ("BH?", "EN?", "LH?"):
            targets[("rtserve.earthscope.org:18000", "II", "KAPI")].append(sel)
        for r in R.get("phase4_geoshake", {}).get("in_bbox", [])[:5]:
            targets[("seedlink.geoshake.org:18000", r["net"], r["sta"])].append("???")
    out = []
    for (server, net, sta), sels in targets.items():
        log(f"\n>>> {server} {net}.{sta} selectors={sels}")
        r = live_test(server, net, sta, sels, args.live_seconds, OUT)
        out.append(r)
        log(json.dumps(r, indent=2, default=str))
    R["phase5_live"] = out


def public_ip():
    code, body = http_get("https://api.ipify.org", timeout=10)
    return body.strip() if code == 200 else None


def main():
    global OUT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outdir")
    ap.add_argument("--skip-web", action="store_true")
    ap.add_argument("--skip-live", action="store_true")
    ap.add_argument("--live-seconds", type=int, default=90)
    ap.add_argument("--active-days", type=int, default=45,
                    help="hanya stasiun FDSN yang masih/baru saja beroperasi dalam N hari terakhir")
    ap.add_argument("--geoshake-fdsn", default="https://api.geoshake.org/fdsnws/station/1/query",
                    help="URL lengkap fdsnws-station milik GeoShake")
    ap.add_argument("--geocode", action="store_true", help="tentukan negara tiap titik (Nominatim)")
    ap.add_argument("--live", action="append", default=[],
                    help="format 'host:port|NET|STA|SEL1,SEL2' (boleh diulang)")
    args = ap.parse_args()

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    OUT = args.outdir or os.path.expanduser(f"~/seedlink_audit/{ts}")
    os.makedirs(OUT, exist_ok=True)
    R["meta"] = {"timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                 "public_ip": public_ip(), "python": sys.version.split()[0], "outdir": OUT,
                 "bbox": BBOX}
    log(f"Output: {OUT}\nMeta: {R['meta']}")

    if not args.skip_web:
        phase1_web()
    phase2_connectivity()
    phase3_inventory()
    phase4_fdsn_intersection(args)
    if not args.skip_live:
        phase5_live(args)

    save("results.json", json.dumps(R, indent=2, default=str))
    log(f"\nSELESAI. Bukti mentah + results.json ada di {OUT}")


if __name__ == "__main__":
    main()
