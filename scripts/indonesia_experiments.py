#!/usr/bin/env python3
"""
indonesia_experiments.py - Eksperimen lanjutan: mencari sumber data stasiun Indonesia.
Butuh seedlink_audit.py (v2) di folder yang sama. Hanya pustaka standar Python.

  E1 registry   Crawl registri FDSN data center -> kumpulkan seedlink:// dan fdsnws-station yang DIDEKLARASIKAN operator
  E2 survey     HELLO + INFO STREAMS tiap server  x  stasiun FDSN di bbox Indonesia (semua pusat data) -> irisan LIVE
  E3 httpprobe  Probe HTTP ringserver pada port yang sama (/id, /streams), jalur inventaris alternatif
  E4 archive    Arsip FDSN: availability + dataselect sebelum/sesudah 28 Agu 2026 + latensi data terbaru
  E5 bmkg       Katalog terbuka BMKG (autogempa/gempaterkini/gempadirasakan): status, kesegaran, header cache
  E6 leads      Ekstrak URL/host dari repo GitHub publik yang disitasi laporan Gemini (HANYA petunjuk, tidak diuji)

Contoh:
  python3 indonesia_experiments.py all
  python3 indonesia_experiments.py e1 e2 --geocode
  python3 indonesia_experiments.py e4 --archive-target EARTHSCOPE:PS:JAY:BH?
Aturan: tanpa port scanning; hanya host:port dari daftar/registri resmi; permintaan ringan; jeda >= 1 dtk antar permintaan web.
"""
import argparse
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import struct
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

try:
    import seedlink_audit as A
except ImportError:
    sys.exit("Letakkan seedlink_audit.py (v2) di folder yang sama dengan skrip ini.")

UTC = timezone.utc
UA = A.UA
RES = {}

REGISTRY_INDEX = "https://www.fdsn.org/datacenters/"

DEFAULT_SERVERS = [
    "rtserve.earthscope.org:18000", "seedlink.geoshake.org:18000", "geofon.gfz.de:18000",
    "auspass.edu.au:18000", "rtserve.resif.fr:18000", "eida.bgr.de:18000",
    "rtserver.ipgp.fr:18000", "eida.orfeus-eu.org:18000",
]
# fdsnws-station yang URL-nya tertera di registri FDSN (GeoShake, AusPass) atau layanan resmi operator
DEFAULT_FDSN = {
    "EARTHSCOPE": "https://service.earthscope.org/fdsnws/station/1/query",
    "GFZ": "https://geofon.gfz.de/fdsnws/station/1/query",
    "GEOSHAKE": "https://api.geoshake.org/fdsnws/station/1/query",
    "AUSPASS": "https://auspass.edu.au/fdsnws/station/1/query",
}
FDSN_BASE_HOST = {"EARTHSCOPE": "https://service.earthscope.org", "GFZ": "https://geofon.gfz.de"}

BMKG_FILES = [
    "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json",
    "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json",
    "https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json",
    "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.xml",
]
LEAD_REPOS = [("luhtfiimanal", "seedlink-rs"), ("bagusindrayana", "ews-concept")]


# --------------------------------------------------------------------------- util
def http_bytes(url, timeout=30, maxbytes=8_000_000, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(maxbytes + 1)
            return r.status, dict(r.headers), data[:maxbytes], None
    except urllib.error.HTTPError as e:
        try:
            body = e.read(2000)
        except Exception:
            body = b""
        return e.code, dict(e.headers or {}), body, None
    except Exception as e:
        return None, {}, b"", f"{type(e).__name__}: {e}"


def norm_sl(url):
    s = url.replace("seedlink://", "").strip("/")
    return s if ":" in s else s + ":18000"


def split_server(s):
    host, _, port = s.rpartition(":")
    return host, int(port)


# --------------------------------------------------------------------------- E1
def e1_registry(args):
    A.log("\n" + "=" * 70 + "\nE1: CRAWL REGISTRI FDSN DATA CENTER\n" + "=" * 70)
    st, h, body, err = http_bytes(REGISTRY_INDEX)
    names = []
    if st == 200:
        names = sorted(set(re.findall(r"/datacenters/detail/([^/\"'#?\s<>]+)/?", body.decode("utf-8", "replace"))))
    A.log(f"indeks HTTP={st} err={err}; pusat data ditemukan: {len(names)}")
    if args.centers:
        names = sorted(set(names) | set(args.centers.split(",")))
    if not names:
        A.log("  indeks tidak bisa di-parse. Cari tautan API JSON di halaman registri atau pakai --centers NAMA1,NAMA2")
    out, servers, fdsn = {}, set(), {}
    for name in names[: args.max_centers]:
        time.sleep(1.0)
        st, h, body, err = http_bytes(f"https://www.fdsn.org/datacenters/detail/{name}/")
        if st != 200:
            out[name] = {"http": st, "error": err}
            continue
        text = A.strip_html(body.decode("utf-8", "replace"))
        sl = sorted({norm_sl(m) for m in re.findall(r"seedlink://[A-Za-z0-9.\-]+(?::\d+)?", text)})
        fs = sorted(set(re.findall(r"https?://[^\s\"<>]+/fdsnws/station/1/?", text)))
        out[name] = {"http": st, "seedlink": sl, "fdsnws_station": fs}
        servers |= set(sl)
        if fs:
            fdsn[name] = fs[0].rstrip("/") + "/query"
        if sl or fs:
            A.log(f"  {name}: seedlink={sl} fdsnws-station={fs}")
    RES["e1_registry"] = {"centers": out, "seedlink_servers": sorted(servers), "fdsn_station": fdsn}
    A.save("registry_servers.txt", "\n".join(sorted(servers)))
    A.log(f"\nTotal endpoint SeedLink yang dideklarasikan operator: {len(servers)} -> registry_servers.txt")
    return sorted(servers), fdsn


# --------------------------------------------------------------------------- E2
def collect_fdsn(args, fdsn):
    endafter = (datetime.now(UTC) - timedelta(days=args.active_days)).strftime("%Y-%m-%d")
    coords, flog = {}, {}
    for label, base in fdsn.items():
        time.sleep(0.5)
        code, url, rows = A.fdsn_stations(base, {**A.BBOX, "endafter": endafter})
        flog[label] = {"http": code, "stations": len(rows),
                       "networks": dict(Counter(r["net"] for r in rows).most_common()), "url": url}
        A.log(f"FDSN {label}: HTTP={code} stasiun aktif di bbox={len(rows)} {flog[label]['networks']}")
        for r in rows:
            coords.setdefault((r["net"], r["sta"]), (r["lat"], r["lon"], label))
    return coords, flog


def e2_survey(args, servers, fdsn):
    A.log("\n" + "=" * 70 + "\nE2: SURVEY SERVER x STASIUN FDSN DI BBOX INDONESIA\n" + "=" * 70)
    coords, flog = collect_fdsn(args, fdsn)
    A.log(f"Total stasiun unik (net,sta) di bbox dari semua pusat data: {len(coords)}")
    coord_nets = {n for n, _ in coords}
    results, summary = {}, []
    for srv in servers:
        host, port = split_server(srv)
        ce = A.check_endpoint(host, port, False)
        entry = {"dns": ce["dns"], "tcp": ce["tcp"], "hello": ce["hello"]}
        if ce["tcp"] != "OPEN" or not ce["hello"]:
            A.log(f"\n{srv}: dilewati (DNS={ce['dns']} TCP={ce['tcp']})")
            results[srv] = entry
            continue
        try:
            xml, _ = A.sl_info(host, port, "STREAMS", timeout=args.info_timeout)
            stations, _, _ = A.parse_streams(xml)
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {e}"
            A.log(f"\n{srv}: INFO STREAMS GAGAL {entry['error']}")
            results[srv] = entry
            continue
        A.save(f"survey_info_{srv.replace(':', '_')}.xml", xml)
        hits = sorted(set(stations) & set(coords))
        rows = [{"net": n, "sta": s, "lat": coords[(n, s)][0], "lon": coords[(n, s)][1],
                 "age_s": A.age_s(stations[(n, s)]["newest_end"]),
                 "channels": stations[(n, s)]["channels"][:8]} for n, s in hits]
        entry.update({"stations": len(stations), "bbox_live_stations": rows,
                      "networks_shared_with_bbox": sorted(coord_nets & {n for n, _ in stations}),
                      "has_IA": any(n == "IA" for n, _ in stations)})
        results[srv] = entry
        fresh = sum(1 for r in rows if r["age_s"] is not None and r["age_s"] < 600)
        summary.append((srv, len(stations), len(rows), fresh))
        A.log(f"\n{srv}: {len(stations)} stasiun | di bbox: {len(rows)} (data <10 menit: {fresh}) | IA: {entry['has_IA']}")
        for r in rows[:40]:
            A.log(f"   {r['net']}.{r['sta']:<6} lat={r['lat']:.3f} lon={r['lon']:.3f} umur={r['age_s']}s {r['channels'][:4]}")
    if args.geocode:
        seen = {}
        A.log("\nGeocoding negara (Nominatim, maks 40 titik unik)...")
        for srv, e in results.items():
            for r in e.get("bbox_live_stations", []):
                key = (round(r["lat"], 2), round(r["lon"], 2))
                if key not in seen and len(seen) < 40:
                    seen[key] = A.country_of(r["lat"], r["lon"])
                r["country"] = seen.get(key, "?")
            if e.get("bbox_live_stations"):
                A.log(f"  {srv}: {dict(Counter(r.get('country', '?') for r in e['bbox_live_stations']))}")
    A.log("\nRINGKASAN: server | stasiun | di bbox | segar(<10m)")
    for row in summary:
        A.log("  %-40s %6d %6d %6d" % row)
    RES["e2_survey"] = {"fdsn": flog, "servers": results, "n_coords": len(coords)}
    return results


# --------------------------------------------------------------------------- E3
def http_raw(host, port, path, tls=False, timeout=15, maxbytes=3_000_000):
    conn = None
    try:
        conn = (http.client.HTTPSConnection(host, port, timeout=timeout, context=ssl.create_default_context())
                if tls else http.client.HTTPConnection(host, port, timeout=timeout))
        conn.request("GET", path, headers={"User-Agent": UA, "Accept": "*/*"})
        r = conn.getresponse()
        return r.status, dict(r.getheaders()), r.read(maxbytes), None
    except Exception as e:
        return None, {}, b"", f"{type(e).__name__}: {e}"
    finally:
        if conn:
            conn.close()


def e3_httpprobe(args, survey):
    A.log("\n" + "=" * 70 + "\nE3: PROBE HTTP RINGSERVER (/id, /streams)\n" + "=" * 70)
    watch = [w.strip() for w in args.watch.split(",") if w.strip()]
    targets = []
    for srv, e in (survey or {}).items():
        if e.get("hello") and "ringserver" in " ".join(e["hello"]).lower():
            targets.append((*split_server(srv), False))
    for t in args.tls_hosts.split(","):
        if t.strip():
            h, p = split_server(t.strip())
            targets.append((h, p, True))
    if args.http_hosts:
        for t in args.http_hosts.split(","):
            h, p = split_server(t.strip())
            targets.append((h, p, False))
    out = {}
    for host, port, tls in targets:
        key = f"{host}:{port}{' TLS' if tls else ''}"
        entry = {}
        for path in ("/id", "/streams"):
            time.sleep(1.0)
            st, hd, body, err = http_raw(host, port, path, tls)
            text = body.decode("utf-8", "replace")
            lines = [l for l in text.splitlines() if l.strip()]
            e = {"http": st, "error": err, "bytes": len(body), "lines": len(lines),
                 "content_type": hd.get("Content-Type")}
            if path == "/id":
                e["head"] = lines[:5]
            else:
                e["watch_matches"] = {w: [l[:160] for l in lines if w.lower() in l.lower()][:5] for w in watch}
            entry[path] = e
            A.log(f"{key} GET {path}: HTTP={st} err={err} bytes={len(body)} lines={len(lines)}")
            if path == "/id" and lines:
                A.log(f"    {lines[:3]}")
            if path == "/streams":
                for w, m in e["watch_matches"].items():
                    A.log(f"    '{w}': {len(m)} baris cocok {m[:2]}")
        out[key] = entry
    RES["e3_httpprobe"] = out


# --------------------------------------------------------------------------- E4
def ms_scan(data):
    """Iterasi rekaman miniSEED v2 panjang variabel lewat blockette 1000. Mengembalikan daftar header."""
    recs, i = [], 0
    while i + 48 <= len(data):
        end = ">"
        y = struct.unpack(">H", data[i + 20:i + 22])[0]
        if not 1900 <= y <= 2200:
            end = "<"
            y = struct.unpack("<H", data[i + 20:i + 22])[0]
            if not 1900 <= y <= 2200:
                break
        h = A.ms_header(data[i:i + 512])
        if not h:
            break
        recs.append(h)
        bo = struct.unpack(end + "H", data[i + 46:i + 48])[0]
        reclen, guard = None, 0
        while bo and guard < 10 and i + bo + 8 <= len(data):
            bt, nxt = struct.unpack(end + "HH", data[i + bo:i + bo + 4])
            if bt == 1000:
                reclen = 2 ** data[i + bo + 6]
                break
            bo, guard = nxt, guard + 1
        if not reclen:
            break
        i += reclen
    return recs


def fmt_t(d):
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def fetch_window(base, net, sta, cha, t0, t1, outdir, tag):
    url = (f"{base}/fdsnws/dataselect/1/query?net={net}&sta={sta}&loc=*&cha={cha}"
           f"&start={fmt_t(t0)}&end={fmt_t(t1)}")
    st, hd, data, err = http_bytes(url, timeout=60, maxbytes=3_000_000)
    r = {"url": url, "http": st, "error": err, "bytes": len(data)}
    if st == 200 and data:
        recs = ms_scan(data)
        r["records"] = len(recs)
        if recs:
            r["channels"] = sorted({f"{x['loc']}.{x['cha']}" for x in recs})
            r["first_start"] = min(x["start"] for x in recs).isoformat()
            r["last_end"] = max(x["end"] for x in recs).isoformat()
            r["lag_s_vs_now"] = round((datetime.now(UTC) - max(x["end"] for x in recs)).total_seconds(), 1)
        fn = os.path.join(outdir, f"archive_{tag}_{net}_{sta}.mseed")
        with open(fn, "wb") as f:
            f.write(data)
        r["file"] = fn
    return r


def availability(base, net, sta, cha, start, end):
    url = (f"{base}/fdsnws/availability/1/query?net={net}&sta={sta}&cha={cha}&start={start}&end={end}"
           f"&merge=quality,samplerate&format=text")
    st, hd, data, err = http_bytes(url, timeout=60, maxbytes=1_000_000)
    lines = [l for l in data.decode("utf-8", "replace").splitlines() if l and not l.startswith("#")]
    latest = None
    for l in lines:
        p = l.split()
        if len(p) >= 8:
            latest = max(latest, p[7]) if latest else p[7]
    return {"url": url, "http": st, "error": err, "rows": len(lines), "latest": latest, "sample": lines[:5]}


def e4_archive(args):
    A.log("\n" + "=" * 70 + "\nE4: ARSIP FDSN (availability + dataselect) DAN LATENSI\n" + "=" * 70)
    targets = []
    for t in args.archive_target:
        prov, net, sta, cha = t.split(":")
        targets.append((prov, net, sta, cha))
    if not targets:
        targets = [("EARTHSCOPE", "II", "KAPI", "BH?"), ("EARTHSCOPE", "PS", "JAY", "BH?"),
                   ("GFZ", "GE", "TOLI", "?HZ"), ("GFZ", "GE", "YOGI", "?HZ"), ("GFZ", "GE", "BKB", "?HZ"),
                   ("EARTHSCOPE", "GE", "TOLI", "?HZ")]
    now = datetime.now(UTC).replace(microsecond=0)
    windows = {"pra_28Agu": (datetime(2026, 8, 20, 0, 0, 0, tzinfo=UTC), datetime(2026, 8, 20, 0, 2, 0, tzinfo=UTC)),
               "pasca_28Agu": (datetime(2026, 9, 10, 0, 0, 0, tzinfo=UTC), datetime(2026, 9, 10, 0, 2, 0, tzinfo=UTC)),
               "terbaru": (now - timedelta(minutes=15), now - timedelta(minutes=1))}
    out = []
    for prov, net, sta, cha in targets:
        base = FDSN_BASE_HOST.get(prov, prov if prov.startswith("http") else None)
        if not base:
            A.log(f"provider tidak dikenal: {prov}")
            continue
        time.sleep(1.2)
        av = availability(base, net, sta, cha, "2026-08-01", fmt_t(now)[:10])
        A.log(f"\n{prov} {net}.{sta}/{cha} availability: HTTP={av['http']} baris={av['rows']} latest={av['latest']}")
        entry = {"provider": prov, "net": net, "sta": sta, "cha": cha, "availability": av, "windows": {}}
        for wname, (t0, t1) in windows.items():
            if wname == "terbaru" and (net, sta) not in {("II", "KAPI"), ("PS", "JAY")} and not args.recent_all:
                continue
            time.sleep(1.2)
            r = fetch_window(base, net, sta, cha, t0, t1, A.OUT, wname)
            entry["windows"][wname] = r
            A.log(f"  [{wname}] HTTP={r['http']} bytes={r['bytes']} rec={r.get('records')} "
                  f"ch={r.get('channels')} akhir={r.get('last_end')} lag_vs_now={r.get('lag_s_vs_now')}s {r.get('error') or ''}")
        out.append(entry)
    RES["e4_archive"] = out


# --------------------------------------------------------------------------- E5
def bmkg_events(obj):
    try:
        g = obj["Infogempa"]["gempa"]
    except Exception:
        return []
    return g if isinstance(g, list) else [g]


def parse_iso(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        return None


def e5_bmkg(args):
    A.log("\n" + "=" * 70 + "\nE5: KATALOG TERBUKA BMKG\n" + "=" * 70)
    out = {}
    for url in BMKG_FILES:
        time.sleep(1.0)
        st, hd, body, err = http_bytes(url, timeout=30)
        name = url.rsplit("/", 1)[1]
        A.save(f"bmkg_{name}", body.decode("utf-8", "replace"))
        e = {"url": url, "http": st, "error": err, "bytes": len(body),
             "content_type": hd.get("Content-Type"), "last_modified": hd.get("Last-Modified"),
             "etag": hd.get("ETag"), "cache_control": hd.get("Cache-Control"), "server": hd.get("Server")}
        if st == 200 and name.endswith(".json"):
            try:
                evs = bmkg_events(json.loads(body.decode("utf-8", "replace")))
                times = [parse_iso(x.get("DateTime", "")) for x in evs]
                times = [t for t in times if t]
                e["n_events"] = len(evs)
                if times:
                    newest = max(times)
                    e["newest_event_utc"] = newest.isoformat()
                    e["newest_event_age_h"] = round((datetime.now(UTC) - newest).total_seconds() / 3600, 1)
                e["fields"] = sorted(evs[0].keys()) if evs else []
            except Exception as ex:
                e["parse_error"] = f"{type(ex).__name__}: {ex}"
        out[name] = e
        A.log(f"{name}: HTTP={st} {e.get('content_type')} events={e.get('n_events')} "
              f"terbaru={e.get('newest_event_utc')} (umur {e.get('newest_event_age_h')} jam) "
              f"Last-Modified={e.get('last_modified')} Cache-Control={e.get('cache_control')} {err or ''}")
    RES["e5_bmkg"] = out


# --------------------------------------------------------------------------- E6
SECRET_RE = re.compile(r"(?i)((?:token|passw(?:or)?d|secret|api[_-]?key)\s*[:=]\s*)(\S+)")
URL_RE = re.compile(r"(?:https?|wss?|seedlink)://[^\s)>\"'\]\\,;]+")
HOSTPORT_RE = re.compile(r"\b[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}:\d{2,5}\b")
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d{2,5})?\b")


def extract_leads(text):
    urls = sorted(set(u.rstrip(".") for u in URL_RE.findall(text)))
    hostports = sorted(set(HOSTPORT_RE.findall(text)))
    ips = []
    for m in sorted(set(IP_RE.findall(text))):
        try:
            ip = ipaddress.ip_address(m.split(":")[0])
            ips.append({"value": m, "private": ip.is_private})
        except ValueError:
            pass
    keyl = []
    for line in text.splitlines():
        if re.search(r"(?i)bmkg|seedlink|18000|inatews|websocket|wss?://", line):
            keyl.append(SECRET_RE.sub(r"\1[DIREDAKSI]", line.strip())[:200])
    return {"urls": urls, "host_port": hostports, "ips": ips, "key_lines": keyl[:25]}


def e6_leads(args):
    A.log("\n" + "=" * 70 + "\nE6: PETUNJUK DARI REPO PUBLIK (hanya ekstraksi teks, TIDAK menguji host apa pun)\n" + "=" * 70)
    exts = (".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".js", ".ts", ".py", ".php", ".vue", ".rs", ".go", ".env.example")
    out = {}
    for owner, repo in LEAD_REPOS:
        time.sleep(1.0)
        st, hd, body, err = http_bytes(f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1")
        entry = {"tree_http": st, "error": err, "files": {}}
        if st != 200:
            A.log(f"{owner}/{repo}: tree HTTP={st} {err or ''} (rate limit? coba lagi nanti)")
            out[f"{owner}/{repo}"] = entry
            continue
        tree = json.loads(body.decode("utf-8", "replace")).get("tree", [])
        cands = [t for t in tree if t.get("type") == "blob" and t["path"].lower().endswith(exts)
                 and t.get("size", 0) <= 150_000 and "node_modules" not in t["path"] and "lock" not in t["path"].lower()]
        cands.sort(key=lambda t: (0 if re.search(r"(?i)readme|claude|config|env|\.md$", t["path"]) else 1, t["path"]))
        A.log(f"\n{owner}/{repo}: {len(tree)} berkas, {len(cands)} kandidat teks; dibaca maks {args.max_repo_files}")
        total = 0
        for t in cands[: args.max_repo_files]:
            time.sleep(0.5)
            st, hd, data, err = http_bytes(f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{t['path']}",
                                           timeout=30, maxbytes=200_000)
            if st != 200:
                continue
            total += len(data)
            leads = extract_leads(data.decode("utf-8", "replace"))
            if leads["urls"] or leads["host_port"] or leads["ips"]:
                entry["files"][t["path"]] = leads
            if total > 3_000_000:
                break
        all_urls = sorted({u for f in entry["files"].values() for u in f["urls"]})
        hosts = Counter(re.sub(r"^\w+://", "", u).split("/")[0] for u in all_urls)
        entry["hosts"] = dict(hosts.most_common())
        entry["private_ips"] = sorted({i["value"] for f in entry["files"].values() for i in f["ips"] if i["private"]})
        out[f"{owner}/{repo}"] = entry
        A.log(f"  host unik: {dict(hosts.most_common(25))}")
        flagged = [h for h in hosts if "bmkg" in h or h.startswith("ws") or "seedlink" in h]
        A.log(f"  host terkait BMKG/WebSocket/SeedLink: {flagged}")
        if entry["private_ips"]:
            A.log(f"  PERHATIAN IP privat di repo (JANGAN diuji): {entry['private_ips']}")
        for p, f in list(entry["files"].items())[:6]:
            if f["key_lines"]:
                A.log(f"  [{p}] {f['key_lines'][:3]}")
    RES["e6_leads"] = out


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("experiments", nargs="*", default=["all"], help="e1 e2 e3 e4 e5 e6 atau all")
    ap.add_argument("--outdir")
    ap.add_argument("--geocode", action="store_true")
    ap.add_argument("--active-days", type=int, default=45)
    ap.add_argument("--info-timeout", type=int, default=60)
    ap.add_argument("--centers", help="nama pusat data FDSN tambahan (pisah koma) bila indeks registri gagal di-parse")
    ap.add_argument("--max-centers", type=int, default=150)
    ap.add_argument("--servers-file", help="berkas teks host:port per baris (ditambahkan ke daftar)")
    ap.add_argument("--server", action="append", default=[], help="host:port tambahan (boleh diulang)")
    ap.add_argument("--no-registry-servers", action="store_true", help="E2 hanya memakai daftar default + --server")
    ap.add_argument("--watch", default="KAPI,JAY", help="kode stasiun yang dicari di /streams (pisah koma)")
    ap.add_argument("--tls-hosts", default="rtserve.earthscope.org:18500")
    ap.add_argument("--http-hosts", default="", help="host:port tambahan untuk probe HTTP")
    ap.add_argument("--archive-target", action="append", default=[], help="PROVIDER:NET:STA:CHA, mis. EARTHSCOPE:PS:JAY:BH?")
    ap.add_argument("--recent-all", action="store_true", help="E4: cek jendela 'terbaru' untuk semua target")
    ap.add_argument("--max-repo-files", type=int, default=25)
    args = ap.parse_args()

    sel = {x.lower() for x in args.experiments}
    if "all" in sel:
        sel = {"e1", "e2", "e3", "e4", "e5", "e6"}
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    A.OUT = args.outdir or os.path.expanduser(f"~/seedlink_audit/exp_{ts}")
    os.makedirs(A.OUT, exist_ok=True)
    RES["meta"] = {"timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                   "public_ip": A.public_ip(), "python": sys.version.split()[0], "experiments": sorted(sel)}
    A.log(f"Output: {A.OUT}\nMeta: {RES['meta']}")

    reg_servers, reg_fdsn = [], {}
    if "e1" in sel:
        reg_servers, reg_fdsn = e1_registry(args)
    servers = list(DEFAULT_SERVERS) + list(args.server)
    if args.servers_file:
        servers += [l.strip() for l in open(args.servers_file) if l.strip() and not l.startswith("#")]
    if not args.no_registry_servers:
        servers += reg_servers
    servers = list(dict.fromkeys(servers))
    fdsn = {**DEFAULT_FDSN, **{k.upper() + "_REG": v for k, v in reg_fdsn.items() if v not in DEFAULT_FDSN.values()}}

    survey = None
    if "e2" in sel:
        survey = e2_survey(args, servers, fdsn)
    if "e3" in sel:
        e3_httpprobe(args, survey)
    if "e4" in sel:
        e4_archive(args)
    if "e5" in sel:
        e5_bmkg(args)
    if "e6" in sel:
        e6_leads(args)
    A.save("experiments_results.json", json.dumps(RES, indent=2, default=str))
    A.log(f"\nSELESAI. Bukti mentah + experiments_results.json ada di {A.OUT}")


if __name__ == "__main__":
    main()
