#!/usr/bin/env python
"""Simulated real-time for one Transmetro line: fake buses driven along the GTFS shape at the
estimated headway, published as valid GTFS-RT VehiclePositions + TripUpdates.

The goal is to prove the pipeline, not to be accurate: positions come from the (estimated) schedule.

  python simulate.py --once                  # one snapshot of "now" -> feed/*.pb
  python simulate.py --live                  # rewrite feed/*.pb every 10 s (sim clock = wall clock + offset)
  python simulate.py --replay                # docs/data/replay.json for the GitHub Pages map
"""
import argparse, bisect, csv, functools, json, math, random, re, shutil, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.protobuf.json_format import MessageToDict
from google.transit import gtfs_realtime_pb2 as rt

ROOT = Path(__file__).parent
GTFS = ROOT / "gtfs"
TZ = timezone(timedelta(hours=-6))  # America/Guatemala, no DST
DWELL = 20  # seconds at each stop, already baked into the scheduled trip time


@functools.lru_cache(maxsize=None)
def read(name, gtfs=GTFS):
    with open(gtfs / name, encoding="utf-8", newline="") as f:
        return tuple(csv.DictReader(f))


def hms(s):
    h, m, sec = map(int, s.split(":"))
    return h * 3600 + m * 60 + sec


def haversine(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742000 * math.asin(math.sqrt(h))


def bearing(a, b):
    p1, p2, dl = math.radians(a[0]), math.radians(b[0]), math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


class Line:
    """One trip pattern: shape, stops projected on it, and time/distance mapping."""

    def __init__(self, trip_id, gtfs=GTFS):
        self.trip_id = trip_id
        trip = next(t for t in read("trips.txt", gtfs) if t["trip_id"] == trip_id)
        self.route_id, self.shape_id, self.headsign = trip["route_id"], trip["shape_id"], trip["trip_headsign"]
        self.direction = int(trip["direction_id"])
        route = next(r for r in read("routes.txt", gtfs) if r["route_id"] == self.route_id)
        self.short = route["route_short_name"] if self.route_id.startswith("EX") else re.sub(r"^(TB|L)", "", self.route_id)   # 12E / 18R keep their suffix; TuBus routes are TB<n>; Express shows R10...
        self.color = route.get("route_color") or None; self.text_color = route.get("route_text_color") or None
        self.name = f"Línea {route['route_short_name']} – {route['route_long_name']}" if self.route_id.startswith("L") else route["route_long_name"]

        pts = sorted((r for r in read("shapes.txt", gtfs) if r["shape_id"] == self.shape_id),
                     key=lambda r: int(r["shape_pt_sequence"]))
        self.pts = [(float(r["shape_pt_lat"]), float(r["shape_pt_lon"])) for r in pts]
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + haversine(a, b))

        coords = {r["stop_id"]: r for r in read("stops.txt", gtfs)}
        sts = sorted((r for r in read("stop_times.txt", gtfs) if r["trip_id"] == trip_id),
                     key=lambda r: int(r["stop_sequence"]))
        # place stops in order along the shape: monotone DP (stop k at vertex i, i non-decreasing) minimising total
        # stop-to-vertex distance, so a stop visited twice (e.g. a loop passing the same station) gets two positions
        INF = float("inf")
        n, K = len(self.pts), len(sts)
        lls = [(float(coords[r["stop_id"]]["stop_lat"]), float(coords[r["stop_id"]]["stop_lon"])) for r in sts]
        prev = [None] * K
        cost = [haversine(lls[0], p) for p in self.pts]
        for k in range(1, K):
            best, arg, run = [INF] * n, [0] * n, (INF, 0)
            for i in range(n):
                if cost[i] < run[0]:
                    run = (cost[i], i)
                best[i], arg[i] = run[0] + haversine(lls[k], self.pts[i]), run[1]
            prev[k], cost = arg, best
        idxs = [min(range(n), key=cost.__getitem__)]
        for k in range(K - 1, 0, -1):
            idxs.append(prev[k][idxs[-1]])
        idxs.reverse()
        self.stops = []
        for r, ll, idx in zip(sts, lls, idxs):
            s = coords[r["stop_id"]]
            self.stops.append({"id": r["stop_id"], "seq": int(r["stop_sequence"]), "name": s["stop_name"],
                               "lat": ll[0], "lon": ll[1], "dist": self.cum[idx]})
        self.duration = hms(sts[-1]["arrival_time"]) - hms(sts[0]["departure_time"])
        total = self.stops[-1]["dist"] or 1.0
        for s in self.stops:  # intermediate stop times are blank in the draft: spread by distance
            s["offset"] = round(self.duration * s["dist"] / total)

        self.windows = [(hms(r["start_time"]), hms(r["end_time"]), int(r["headway_secs"]))
                        for r in read("frequencies.txt", gtfs) if r["trip_id"] == trip_id]

    def departures(self, lo, hi):
        """Trip start times (seconds after midnight) in [lo, hi)."""
        out = []
        for start, end, hw in self.windows:
            t = start
            while t < end:
                if lo <= t < hi:
                    out.append(t)
                t += hw
        return out

    def point_at(self, dist):
        i = min(max(bisect.bisect_right(self.cum, dist) - 1, 0), len(self.pts) - 2)
        seg = (self.cum[i + 1] - self.cum[i]) or 1.0
        f = min(max((dist - self.cum[i]) / seg, 0), 1)
        a, b = self.pts[i], self.pts[i + 1]
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), bearing(a, b)

    def dist_at(self, elapsed):
        """Distance along the shape after `elapsed` seconds of the trip (piecewise linear between stops)."""
        offs = [s["offset"] for s in self.stops]
        i = min(max(bisect.bisect_right(offs, elapsed) - 1, 0), len(offs) - 2)
        span = (offs[i + 1] - offs[i]) or 1
        f = min(max((elapsed - offs[i]) / span, 0), 1)
        return self.stops[i]["dist"] + (self.stops[i + 1]["dist"] - self.stops[i]["dist"]) * f


def trip_delay(start):
    """Deterministic per-trip lateness so the feed isn't just the schedule (-60..+150 s)."""
    return random.Random(start).randint(-60, 150)


def build_feed(line, day, now_s):
    """FeedMessage-pair for sim-clock `now_s` (seconds after local midnight of `day`)."""
    midnight = datetime(day.year, day.month, day.day, tzinfo=TZ)
    epoch = lambda s: int((midnight + timedelta(seconds=s)).timestamp())
    ts = epoch(now_s)

    def feed():
        m = rt.FeedMessage()
        m.header.gtfs_realtime_version = "2.0"
        m.header.incrementality = rt.FeedHeader.FULL_DATASET
        m.header.timestamp = ts
        return m

    vp, tu = feed(), feed()
    # active trips, plus the next one still at the terminal so "next bus" works at the first stop
    for start in line.departures(now_s - line.duration - 600, now_s + 600):
        delay = trip_delay(start)
        elapsed = now_s - start - delay
        if elapsed >= line.duration:
            continue
        tid = f"{line.trip_id}@{start // 3600:02d}{start % 3600 // 60:02d}"
        td = lambda e: (setattr(e.trip, "trip_id", line.trip_id), setattr(e.trip, "route_id", line.route_id),
                        setattr(e.trip, "direction_id", line.direction),
                        setattr(e.trip, "start_time", f"{start // 3600:02d}:{start % 3600 // 60:02d}:{start % 60:02d}"),
                        setattr(e.trip, "start_date", day.strftime("%Y%m%d")),
                        setattr(e.trip, "schedule_relationship", rt.TripDescriptor.SCHEDULED))

        nxt = next((s for s in line.stops if s["offset"] >= elapsed), line.stops[-1])
        e = tu.entity.add(id=tid)
        td(e.trip_update)
        e.trip_update.vehicle.id = f"SIM-{start // 60:04d}"
        e.trip_update.delay = delay
        for s in line.stops:
            if s["offset"] < elapsed - 1:
                continue
            u = e.trip_update.stop_time_update.add(stop_sequence=s["seq"], stop_id=s["id"])
            u.arrival.time = epoch(start + s["offset"] + delay)
            u.arrival.delay = delay
            u.departure.time = epoch(start + s["offset"] + delay + (DWELL if s is not line.stops[-1] else 0))
            u.departure.delay = delay
            u.schedule_relationship = rt.TripUpdate.StopTimeUpdate.SCHEDULED

        if elapsed < 0:  # waiting at the terminal: no vehicle on the road yet
            continue
        (lat, lon), brg = line.point_at(line.dist_at(elapsed))
        v = vp.entity.add(id=tid)
        td(v.vehicle)
        v.vehicle.vehicle.id = f"SIM-{start // 60:04d}"
        v.vehicle.vehicle.label = f"Bus {start // 3600:02d}:{start % 3600 // 60:02d}"
        v.vehicle.position.latitude, v.vehicle.position.longitude = lat, lon
        v.vehicle.position.bearing = brg
        v.vehicle.current_stop_sequence = nxt["seq"]
        v.vehicle.stop_id = nxt["id"]
        v.vehicle.current_status = rt.VehiclePosition.IN_TRANSIT_TO
        v.vehicle.timestamp = ts
    return vp, tu


def write_feed(line, day, now_s, out):
    out.mkdir(parents=True, exist_ok=True)
    vp, tu = build_feed(line, day, now_s)
    (out / "vehicle_positions.pb").write_bytes(vp.SerializeToString())
    (out / "trip_updates.pb").write_bytes(tu.SerializeToString())
    return vp, tu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trip", default="L7_0_WEEKDAY", help="trip_id, or 'all' with --replay (every WEEKDAY pattern)")
    ap.add_argument("--out", type=Path, default=ROOT / "feed")
    ap.add_argument("--at", default=None, help="sim clock start HH:MM (default: wall clock)")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--minutes", type=int, default=20, help="replay length")
    ap.add_argument("--step", type=int, default=20, help="seconds between frames")
    a = ap.parse_args()

    now = datetime.now(TZ)
    day = now.date()
    start_s = hms(a.at + ":00") if a.at else now.hour * 3600 + now.minute * 60 + now.second
    if not (a.live or a.once or a.replay):
        a.once = True

    if a.replay:
        nets = [("transmetro", GTFS), ("tubus", ROOT / "gtfs_tubus"), ("express", ROOT / "gtfs_express")] if a.trip == "all" else [("transmetro", GTFS)]
        data_dir = ROOT / "docs" / "data"
        shutil.rmtree(data_dir, ignore_errors=True)
        shutil.rmtree(ROOT / "docs" / "feed", ignore_errors=True)
        data_dir.mkdir(parents=True)
        index, stops_idx = [], {}
        for net, gdir in nets:
            if not (gdir / "trips.txt").exists():
                continue
            trips = [t["trip_id"] for t in read("trips.txt", gdir) if t["service_id"].endswith("WEEKDAY")] if a.trip == "all" else [a.trip]
            for tid in trips:
                line = Line(tid, gdir)
                frames = []
                for t in range(start_s, start_s + a.minutes * 60, a.step):
                    vp, tu = build_feed(line, day, t)
                    frames.append({"t": t, "vp": MessageToDict(vp), "tu": MessageToDict(tu)})
                data = {"line": {"name": line.name, "headsign": line.headsign, "shape": [[round(p[0], 6), round(p[1], 6)] for p in line.pts],
                                 "stops": [{k: s[k] for k in ("id", "seq", "name", "lat", "lon")} for s in line.stops]},
                        "day": day.isoformat(), "step": a.step, "frames": frames}
                p = data_dir / f"{tid}.json"
                p.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
                write_feed(line, day, start_s, ROOT / "docs" / "feed" / tid)  # sample binary feeds next to the map
                short = line.short
                index.append({"id": tid, "network": net, "short": short, "name": line.name.split(" – ", 1)[-1] if line.route_id.startswith("L") else line.name, "headsign": line.headsign,
                              "color": line.color, "text": line.text_color, "label": f"{line.name} → {line.headsign}"})
                for st in line.stops:
                    e = stops_idx.setdefault(st["id"], {"id": st["id"], "name": st["name"], "lat": st["lat"], "lon": st["lon"], "network": net, "lines": []})
                    if short not in e["lines"]:
                        e["lines"].append(short)
                print(f"wrote {p.name} ({p.stat().st_size // 1024} KiB, {len(frames)} frames)")
        (data_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        (data_dir / "stops.json").write_text(json.dumps(sorted(stops_idx.values(), key=lambda e: e["name"]), ensure_ascii=False,
                                                       separators=(",", ":")), encoding="utf-8")
        return

    line = Line(a.trip)
    t0 = time.time()
    while True:
        t = start_s + int(time.time() - t0)
        vp, tu = write_feed(line, day, t, a.out)
        print(f"[{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}] {len(vp.entity)} vehicles, {len(tu.entity)} trip updates -> {a.out}")
        if a.once:
            return
        time.sleep(10)


if __name__ == "__main__":
    main()
