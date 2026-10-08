#!/usr/bin/env python3
"""
expand_radius.py - Cari >= N stasiun seismik LIVE di SeedLink publik di sekitar Indonesia,
dengan memperluas jarak (derajat) bertahap sampai target tercapai. Butuh seedlink_audit.py (v2) di folder yang sama.
Hanya pustaka standar Python.

Definisi jarak (--mode anchor, default):
  jarak sudut (derajat busur bumi, 1 derajat ~ 111 km) dari stasiun ke TITIK ACUAN INDONESIA TERDEKAT
  (daftar ~60 titik yang mencakup Sabang sampai Merauke dan pulau terluar; lihat ANCHORS).
  --mode bbox : derajat di luar kotak Indonesia (lintang -11.5..6.5, bujur 94.5..141.5), nilai Chebyshev.

Alur:
  1. INFO STREAMS semua server SeedLink (paralel) -> stasiun yang punya kanal seismik (band/instrumen sesuai filter)
     dan datanya segar (end_time <= --max-age detik).
  2. Koordinat dari FDSN station (satu kueri per penyedia, bbox sebesar --max-margin) -> irisan (net, sta).
  3. Perluas margin: start, start+step, ... sampai jumlah kandidat >= target.
  4. Verifikasi live: satu koneksi SeedLink multi-stasiun per server selama --verify-seconds; stasiun dihitung
     bila benar-benar mengirim paket. Bila yang lolos < target, margin diperluas lagi (hanya stasiun baru diverifikasi).
  5. Tentukan NEGARA tiap stasiun terpilih (kode ISO + nama, Nominatim; matikan dengan --no-geocode).
  6. Simpan: selected_stations.csv/json, pipeline_config.json, expand_steps.json (termasuk jumlah per negara).

Contoh:
  python3 expand_radius.py --target 20
  python3 expand_radius.py --target 20 --servers-file registry_servers.txt
  python3 expand_radius.py --target 20 --bands EHBSM --max-age 1800 --max-margin 40 --no-verify
Aturan: tanpa port scanning; hanya server pada daftar; HELLO/INFO/DATA ringan; kueri FDSN sopan.
"""
import argparse
import csv
import json
import math
import os
import re
import socket
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

try:
    import seedlink_audit as A
except ImportError:
    sys.exit("Letakkan seedlink_audit.py (v2) di folder yang sama dengan skrip ini.")

UTC = timezone.utc

DEFAULT_SERVERS = [
    "rtserve.earthscope.org:18000", "geofon.gfz.de:18000", "rtserve.resif.fr:18000", "eida.bgr.de:18000",
    "auspass.edu.au:18000", "rtserver.ipgp.fr:18000", "eida.orfeus-eu.org:18000",
    # rtserve.iris.washington.edu = alias EarthScope (sengaja tidak dimasukkan, akan menggandakan stasiun)
]
DEFAULT_FDSN = {
    "EARTHSCOPE": "https://service.earthscope.org/fdsnws/station/1/query",
    "GFZ": "https://geofon.gfz.de/fdsnws/station/1/query",
    "AUSPASS": "https://auspass.edu.au/fdsnws/station/1/query",
}

# Titik acuan Indonesia (nama, lintang, bujur) - kota/pulau terluar, akurasi ~0.1-0.5 derajat
ANCHORS = [
    ("Sabang", 5.89, 95.32), ("Banda Aceh", 5.55, 95.32), ("Medan", 3.59, 98.67), ("Sibolga", 1.74, 98.78),
    ("Padang", -0.95, 100.35), ("Pekanbaru", 0.51, 101.45), ("Batam", 1.05, 104.03), ("Jambi", -1.61, 103.61),
    ("Palembang", -2.99, 104.76), ("Bengkulu", -3.80, 102.26), ("Bandar Lampung", -5.45, 105.27),
    ("Jakarta", -6.21, 106.85), ("Bandung", -6.91, 107.61), ("Semarang", -6.97, 110.42),
    ("Yogyakarta", -7.80, 110.36), ("Surabaya", -7.25, 112.75), ("Banyuwangi", -8.22, 114.37),
    ("Denpasar", -8.65, 115.22), ("Mataram", -8.58, 116.12), ("Labuan Bajo", -8.50, 119.89),
    ("Maumere", -8.62, 122.21), ("Kupang", -10.17, 123.61), ("Rote", -10.95, 122.85), ("Waingapu", -9.66, 120.26),
    ("Pontianak", -0.03, 109.33), ("Ranai Natuna", 3.95, 108.38), ("Putussibau", 0.83, 112.93),
    ("Palangkaraya", -2.21, 113.92), ("Banjarmasin", -3.32, 114.59), ("Balikpapan", -1.24, 116.83),
    ("Samarinda", -0.50, 117.15), ("Tarakan", 3.30, 117.63), ("Nunukan", 4.14, 117.67),
    ("Manado", 1.47, 124.84), ("Miangas", 5.58, 126.58), ("Gorontalo", 0.54, 123.06), ("Palu", -0.90, 119.87),
    ("Makassar", -5.15, 119.43), ("Kendari", -3.97, 122.51), ("Luwuk", -0.95, 122.79),
    ("Ternate", 0.79, 127.38), ("Ambon", -3.70, 128.18), ("Saumlaki", -7.98, 131.30), ("Tual", -5.64, 132.75),
    ("Dobo", -5.77, 134.22), ("Sorong", -0.88, 131.26), ("Manokwari", -0.86, 134.06), ("Biak", -1.18, 136.08),
    ("Nabire", -3.37, 135.49), ("Timika", -4.55, 136.89), ("Wamena", -4.10, 138.95),
    ("Jayapura", -2.53, 140.72), ("Merauke", -8.49, 140.40), ("Tanah Merah", -6.10, 140.30),
]
BBOX_ID = (-11.5, 6.5, 94.5, 141.5)  # minlat, maxlat, minlon, maxlon
BAND_RANK = "HBES"                   # preferensi memilih kanal terbaik


# --------------------------------------------------------------------------- geometri
def ang_deg(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(a))))


def dist_anchor(lat, lon):
    best = min(((ang_deg(lat, lon, a[1], a[2]), a[0]) for a in ANCHORS))
    return best


def dist_bbox(lat, lon):
    mn, mx, ml, xl = BBOX_ID
    return max(0.0, mn - lat, lat - mx, ml - lon, lon - xl), "bbox"


def expanded_bbox(margin, mode):
    if mode == "bbox":
        mn, mx, ml, xl = BBOX_ID
        pad_lon = margin
    else:
        mn, mx = min(a[1] for a in ANCHORS), max(a[1] for a in ANCHORS)
        ml, xl = min(a[2] for a in ANCHORS), max(a[2] for a in ANCHORS)
        pad_lon = margin * 1.5  # bujur menyempit di lintang tinggi: kotak konservatif, disaring tepat setelahnya
    return dict(minlatitude=max(-90.0, mn - margin), maxlatitude=min(90.0, mx + margin),
                minlongitude=max(-180.0, ml - pad_lon), maxlongitude=min(180.0, xl + pad_lon))


_GEO_CACHE = {}


def country_info(lat, lon):
    """(kode_ISO2, nama_negara) lewat reverse geocoding Nominatim; ('?', 'TIDAK DIKETAHUI') bila gagal/laut lepas."""
    key = (round(lat, 2), round(lon, 2))
    if key in _GEO_CACHE:
        return _GEO_CACHE[key]
    time.sleep(1.1)  # batas Nominatim: 1 permintaan per detik
    url = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode(
        {"format": "jsonv2", "zoom": 3, "accept-language": "en", "lat": lat, "lon": lon})
    code, body = A.http_get(url, timeout=20)
    res = ("?", "TIDAK DIKETAHUI")
    try:
        addr = json.loads(body).get("address", {})
        if addr.get("country_code"):
            res = (addr["country_code"].upper(), addr.get("country", "?"))
    except Exception:
        pass
    _GEO_CACHE[key] = res
    return res


# --------------------------------------------------------------------------- inventaris
def parse_inventory(xml_text):
    root = ET.fromstring(xml_text)
    out = {}
    for s in root.iter("station"):
        chans = []
        for x in s.iter("stream"):
            cha = x.get("seedname", "")
            if "_" in cha:  # bentuk FDSN Source ID (mis. B_H_Z)
                parts = cha.split("_")
                cha = "".join(parts[-3:]) if len(parts) >= 3 else cha
            chans.append((x.get("location", ""), cha, A.parse_sl_time(x.get("end_time", ""))))
        out[(s.get("network"), s.get("name"))] = chans
    return out


def qualify(chans, bands, instr):
    """Pilih kanal seismik yang memenuhi syarat. Mengembalikan (best, semua_kanal, end_terbaru) atau None."""
    ok = [(loc, cha, e) for loc, cha, e in chans if len(cha) == 3 and cha[0] in bands and cha[1] in instr]
    if not ok:
        return None
    ends = [e for _, _, e in ok if e]
    newest = max(ends) if ends else None
    rank = lambda c: (c[1][2] != "Z", BAND_RANK.find(c[1][0]) if c[1][0] in BAND_RANK else 9,
                      0 if c[1][1] == "H" else 1)
    best = sorted(ok, key=rank)[0][1]
    return best, sorted({c[1] for c in ok}), newest


def fetch_one(server, args):
    host, port = server.rsplit(":", 1)
    cache = os.path.join(args.cache_dir, f"info_{server.replace(':', '_')}.xml")
    try:
        if args.use_cache and os.path.exists(cache):
            xml = open(cache, encoding="utf-8").read()
        else:
            xml, _ = A.sl_info(host, int(port), "STREAMS", timeout=args.info_timeout)
            with open(os.path.join(A.OUT, f"info_{server.replace(':', '_')}.xml"), "w", encoding="utf-8") as f:
                f.write(xml)
        return server, parse_inventory(xml), None
    except Exception as e:
        return server, None, f"{type(e).__name__}: {e}"


def fetch_inventories(servers, args):
    out, errors = {}, {}
    with ThreadPoolExecutor(max_workers=min(8, len(servers))) as ex:
        for server, inv, err in ex.map(lambda s: fetch_one(s, args), servers):
            if err:
                errors[server] = err
                A.log(f"  {server}: GAGAL {err}")
            else:
                out[server] = inv
                A.log(f"  {server}: {len(inv)} stasiun")
    return out, errors


# --------------------------------------------------------------------------- FDSN
def fdsn_query(base, params, timeout=120):
    q = urllib.parse.urlencode({**params, "level": "station", "format": "text"})
    code, body = A.http_get(f"{base}?{q}", timeout=timeout)
    rows = []
    if code == 200:
        for line in body.splitlines():
            if not line or line.startswith("#"):
                continue
            p = line.split("|")
            if len(p) >= 4:
                try:
                    rows.append({"net": p[0], "sta": p[1], "lat": float(p[2]), "lon": float(p[3])})
                except ValueError:
                    pass
    return code, rows


def collect_coords(fdsn, args):
    box = expanded_bbox(args.max_margin, args.mode)
    endafter = (datetime.now(UTC) - timedelta(days=args.active_days)).strftime("%Y-%m-%d")
    coords, log = {}, {}
    A.log(f"bbox kueri FDSN: {box}  endafter={endafter}")
    for label, base in fdsn.items():
        time.sleep(1.0)
        code, rows = fdsn_query(base, {**box, "endafter": endafter})
        log[label] = {"http": code, "stations": len(rows)}
        A.log(f"  FDSN {label}: HTTP={code} stasiun={len(rows)}")
        for r in rows:
            coords.setdefault((r["net"], r["sta"]), (r["lat"], r["lon"], label))
    return coords, log


# --------------------------------------------------------------------------- verifikasi live
def multi_live(server, items, seconds):
    """Satu koneksi SeedLink v3 multi-stasiun. items: [(net, sta, selector)]. Mengembalikan {(net,sta): stats}."""
    host, port = server.rsplit(":", 1)
    stats = {(n, s): {"ok": False, "packets": 0, "error": None, "rate": None, "lags": []} for n, s, _ in items}
    sock = None
    try:
        sock, _ = A.sl_open(host, int(port))
        dl = time.time() + 90
        accepted = []
        for net, sta, sel in items:
            st = stats[(net, sta)]
            for cmd, tag in ((f"STATION  {sta} {net}", "STATION"), (f"SELECT {sel}", "SELECT"), ("DATA", "DATA")):
                sock.sendall(cmd.encode() + b"\r")
                r = A._readline(sock, dl)
                if r != "OK":
                    st["error"] = f"{tag}: {r}"
                    break
            else:
                accepted.append((net, sta))
        if accepted:
            sock.sendall(b"END\r")
            end_at = time.time() + seconds
            while time.time() < end_at:
                try:
                    pkt = A._recv_exact(sock, 520, end_at)
                except socket.timeout:
                    break
                if pkt[:2] != b"SL":
                    break
                h = A.ms_header(pkt[8:])
                if not h:
                    continue
                st = stats.get((h["net"], h["sta"]))
                if st is None:
                    continue
                st["ok"] = True
                st["packets"] += 1
                st["rate"] = h["rate"]
                st["lags"].append((datetime.now(UTC) - h["end"]).total_seconds())
    except Exception as e:
        for st in stats.values():
            st["error"] = st["error"] or f"{type(e).__name__}: {e}"
    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass
    return stats


def verify(cands, seconds):
    by_server = defaultdict(list)
    for c in cands:
        by_server[c["server"]].append((c["net"], c["sta"], c["selector"]))
    results = {}
    A.log(f"  verifikasi live {seconds}s pada {len(by_server)} server (paralel)...")
    with ThreadPoolExecutor(max_workers=max(1, len(by_server))) as ex:
        futs = {s: ex.submit(multi_live, s, items[:200], seconds) for s, items in by_server.items()}
        for s, f in futs.items():
            for key, st in f.result().items():
                lags = st.pop("lags")
                if lags:
                    st["latency_median_s"] = round(sorted(lags)[len(lags) // 2], 1)
                results[key] = st
    return results


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=int, default=20)
    ap.add_argument("--start", type=float, default=1.0, help="margin awal (derajat)")
    ap.add_argument("--step", type=float, default=1.0, help="penambahan margin per langkah (derajat)")
    ap.add_argument("--max-margin", type=float, default=25.0)
    ap.add_argument("--mode", choices=["anchor", "bbox"], default="anchor")
    ap.add_argument("--bands", default="EHBS", help="huruf band yang diterima (E,H,S,B = laju >= 10 Hz)")
    ap.add_argument("--instr", default="HN", help="huruf instrumen: H seismometer, N akselerometer")
    ap.add_argument("--max-age", type=float, default=900.0, help="umur data maks. (detik) menurut end_time INFO")
    ap.add_argument("--exclude-networks", default="SY,GW", help="kode jaringan yang dibuang (SY sintetis, GW sensor warga)")
    ap.add_argument("--servers-file", help="berkas host:port per baris, ditambahkan ke daftar default")
    ap.add_argument("--server", action="append", default=[])
    ap.add_argument("--fdsn", action="append", default=[], help="NAMA=URL fdsnws-station/1/query tambahan")
    ap.add_argument("--active-days", type=int, default=45)
    ap.add_argument("--info-timeout", type=int, default=90)
    ap.add_argument("--verify-seconds", type=int, default=90)
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--no-geocode", action="store_true", help="matikan penentuan negara (default: aktif)")
    ap.add_argument("--geocode", action="store_true", help=argparse.SUPPRESS)  # kompatibilitas perintah lama
    ap.add_argument("--outdir")
    ap.add_argument("--use-cache", action="store_true", help="pakai info_*.xml yang sudah ada di --cache-dir")
    ap.add_argument("--cache-dir")
    args = ap.parse_args()

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    A.OUT = args.outdir or os.path.expanduser(f"~/seedlink_audit/radius_{ts}")
    os.makedirs(A.OUT, exist_ok=True)
    args.cache_dir = args.cache_dir or A.OUT
    A.log(f"Output: {A.OUT}\nWaktu UTC: {datetime.now(UTC).isoformat(timespec='seconds')}  "
          f"mode={args.mode} target={args.target} margin {args.start}..{args.max_margin} step {args.step}")

    servers = list(DEFAULT_SERVERS) + args.server
    if args.servers_file:
        servers += [l.strip() for l in open(args.servers_file) if l.strip() and not l.startswith("#")]
    servers = list(dict.fromkeys(servers))
    fdsn = dict(DEFAULT_FDSN)
    for kv in args.fdsn:
        k, _, v = kv.partition("=")
        fdsn[k.upper()] = v
    excluded = {x.strip() for x in args.exclude_networks.split(",") if x.strip()}

    # 1. inventaris live
    A.log(f"\n[1] INFO STREAMS dari {len(servers)} server")
    invs, inv_err = fetch_inventories(servers, args)
    live = {}  # (net,sta) -> {server: (best, allc, newest)}
    for server, inv in invs.items():
        for key, chans in inv.items():
            if key[0] in excluded:
                continue
            q = qualify(chans, args.bands, args.instr)
            if q:
                live.setdefault(key, {})[server] = q
    A.log(f"stasiun dengan kanal seismik (band {args.bands}, instrumen {args.instr}) di semua server: {len(live)}")

    # 2. koordinat
    A.log("\n[2] Koordinat dari FDSN")
    coords, fdsn_log = collect_coords(fdsn, args)

    # 3. kandidat segar + jarak
    cands, no_coord, stale = [], Counter(), 0
    for key, per_server in live.items():
        server, (best, allc, newest) = min(
            per_server.items(), key=lambda kv: (kv[1][2] is None, -(kv[1][2].timestamp() if kv[1][2] else 0)))
        age = A.age_s(newest)
        if age is None or age > args.max_age:
            stale += 1
            continue
        if key not in coords:
            no_coord[key[0]] += 1
            continue
        lat, lon, src = coords[key]
        d, near = dist_anchor(lat, lon) if args.mode == "anchor" else dist_bbox(lat, lon)
        cands.append({"net": key[0], "sta": key[1], "lat": lat, "lon": lon, "dist_deg": round(d, 2), "nearest": near,
                      "server": server, "servers": sorted(per_server), "selector": best, "channels": allc,
                      "age_s": age, "fdsn": src})
    cands.sort(key=lambda c: (c["dist_deg"], c["net"], c["sta"]))
    A.log(f"\n[3] kandidat segar (<= {args.max_age:.0f}s) BERKOORDINAT: {len(cands)} | data tidak segar/tanpa end_time: {stale}"
          f" | segar tetapi TANPA koordinat: {sum(no_coord.values())}")
    if no_coord:
        A.log(f"    jaringan tanpa koordinat (tambahkan --fdsn NAMA=URL bila perlu): {dict(no_coord.most_common(12))}")

    # 4. perluas margin
    steps, verified, selected = [], {}, []
    m = args.start
    reached = False
    A.log("\n[4] Perluasan margin")
    while m <= args.max_margin + 1e-9:
        inside = [c for c in cands if c["dist_deg"] <= m]
        prev = steps[-1]["count"] if steps else 0
        new = [c for c in inside if c["dist_deg"] > m - args.step] if steps else inside
        steps.append({"margin_deg": m, "count": len(inside), "new": [f"{c['net']}.{c['sta']}" for c in new]})
        names = ", ".join("%s.%s(%s)" % (c["net"], c["sta"], c["dist_deg"]) for c in new[:8])
        A.log("  margin %5.1f derajat: %3d stasiun segar (+%d)  baru: %s%s"
              % (m, len(inside), len(inside) - prev, names, " ..." if len(new) > 8 else ""))
        if len(inside) >= args.target:
            if args.no_verify:
                selected, reached = inside[: args.target], True
                break
            todo = [c for c in inside if (c["net"], c["sta"]) not in verified]
            if todo:
                verified.update(verify(todo, args.verify_seconds))
            ok = [c for c in inside if verified.get((c["net"], c["sta"]), {}).get("ok")]
            A.log(f"    verifikasi: {len(ok)}/{len(inside)} stasiun benar-benar mengirim paket")
            if len(ok) >= args.target:
                selected, reached = ok[: args.target], True
                break
        m = round(m + args.step, 6)

    # 5. keluaran
    A.log("\n" + "=" * 78)
    if reached:
        A.log(f"TARGET TERCAPAI: {len(selected)} stasiun pada margin <= {steps[-1]['margin_deg']} derajat")
    else:
        top = len([c for c in cands if c['dist_deg'] <= args.max_margin])
        A.log(f"TARGET BELUM TERCAPAI sampai {args.max_margin} derajat (kandidat segar: {top}, "
              f"lolos verifikasi: {sum(1 for v in verified.values() if v['ok'])}).")
        A.log("Saran: naikkan --max-margin; longgarkan --bands (mis. EHBSM) atau --max-age; tambah server/--fdsn.")
        selected = [c for c in cands if verified.get((c['net'], c['sta']), {}).get('ok')] or cands[: args.target]
    for c in selected:
        c["verified"] = verified.get((c["net"], c["sta"]))
    per_country = {}
    if selected and not args.no_geocode:
        A.log("\nMenentukan negara tiap stasiun (Nominatim, ~1 dtk per stasiun)...")
        for c in selected:
            c["country_code"], c["country_name"] = country_info(c["lat"], c["lon"])
        per_country = dict(Counter("%s (%s)" % (c["country_name"], c["country_code"]) for c in selected).most_common())
        A.log("Jumlah stasiun per negara: " + ", ".join("%s: %d" % kv for kv in per_country.items()))
    A.log(f"{'No':>3} {'NET.STA':<10} {'jarak':>6} {'terdekat':<14} {'server':<30} {'kanal':<6} {'umur_s':>7} {'paket':>5} {'lag_s':>6} negara")
    for i, c in enumerate(selected, 1):
        v = c.get("verified") or {}
        A.log(f"{i:>3} {c['net'] + '.' + c['sta']:<10} {c['dist_deg']:>6} {c['nearest']:<14} {c['server']:<30} "
              f"{c['selector']:<6} {c['age_s']:>7} {v.get('packets', '-'):>5} {v.get('latency_median_s', '-'):>6} "
              f"{c.get('country_name', '')} ({c.get('country_code', '')})")

    A.save("expand_steps.json", json.dumps({"steps": steps, "fdsn": fdsn_log, "inventory_errors": inv_err,
                                            "per_country": per_country}, indent=2))
    A.save("selected_stations.json", json.dumps(selected, indent=2, default=str))
    with open(os.path.join(A.OUT, "selected_stations.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["net", "sta", "lat", "lon", "dist_deg", "nearest_anchor", "server", "selector", "channels",
                    "age_s", "packets", "latency_median_s", "country_code", "country_name"])
        for c in selected:
            v = c.get("verified") or {}
            w.writerow([c["net"], c["sta"], c["lat"], c["lon"], c["dist_deg"], c["nearest"], c["server"],
                        c["selector"], " ".join(c["channels"]), c["age_s"], v.get("packets"),
                        v.get("latency_median_s"), c.get("country_code", ""), c.get("country_name", "")])
    cfg = defaultdict(list)
    for c in selected:
        cfg[c["server"]].append({"net": c["net"], "sta": c["sta"], "select": c["selector"], "channels": c["channels"]})
    A.save("pipeline_config.json", json.dumps(cfg, indent=2))
    A.log(f"\nSELESAI. File: selected_stations.csv/json, pipeline_config.json, expand_steps.json di {A.OUT}")
    sys.exit(0 if reached else 2)


if __name__ == "__main__":
    main()
