"""One fetch loop per machine for the paper-download skill: a lease plus a log of fetch slots.

Usage (every command also takes --state-dir DIR and --owner ID):
  python -I fetch_gate.py start --manifest <manifest.json> --label "<manuscript> priority <P>"
                                [--interval 30] [--ttl 600] [--downloads DIR]
  python -I fetch_gate.py next --doi <doi> [--pub <publisher>]
  python -I fetch_gate.py hold --pub <publisher> --reason "<what was seen>"
  python -I fetch_gate.py clear --pub <publisher>   |   clear --run
  python -I fetch_gate.py end [--aborted]
  python -I fetch_gate.py status
  python -I fetch_gate.py wait [--max 10800] [--poll 20]

The servers see one machine and one network, so the fetch interval is per machine, not per
session. A session opens a run with `start` before its first fetch (GO, or BUSY while another
live session holds the lease), reserves a slot with `next` before every fetch (WAIT <s>: wait
that long before the request; HOLD: skip that publisher; LOST: another session took the lease
over, stop), and closes the run with `end` after its final collector pass or on any abort.
`hold` marks a publisher that showed a captcha or challenge, for every session, until `clear`
or 24 h. `wait` blocks until the lease is free (run it in the background), without taking it.

A lease is taken over by the next `start` when its session's process has exited or when it saw
no `next` for --ttl seconds. A session and its subagents are one owner: the owner is read from
CLAUDE_CODE_HOST_SESSION_ID and the process from CLAUDE_PID, which subagents inherit (--owner
for a terminal or another agent; without either the owner is "terminal"). State lives in
%LOCALAPPDATA%\\paper-download\\ (or the PAPER_DOWNLOAD_STATE folder): state.json (the lease,
the holds, the last slot) and gate_log.jsonl (one line per event), changed only while holding
an OS lock on gate.mutex, which the system releases if a process dies.

The first word of the output is the answer. Exit codes: 0 GO / WAIT / FREE / done, 3 BUSY or
still busy, 4 LOST, 5 HOLD, 2 usage error.
"""
import argparse
import json
import math
import os
import re
import secrets
import sys
import time

INTERVAL = 30           # s between any two fetch slots on the machine
TTL = 600               # s without `next` before a live session's lease may be taken over
HOLD_TTL = 24 * 3600    # s a publisher hold lasts unless cleared
LOG_MAX = 1_000_000     # bytes; the log is trimmed to its last LOG_KEEP lines beyond this
LOG_KEEP = 3000
WARN_WINDOW = 1800      # s back that `start` looks for ungated PDFs in Downloads

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes
else:
    import fcntl


def default_state_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.environ.get("PAPER_DOWNLOAD_STATE") or os.path.join(base, "paper-download")


def pid_alive(pid):
    """True / False for a process id, None when there is none to check.

    On Windows os.kill(pid, 0) terminates the process instead of probing it, so the check goes
    through OpenProcess and GetExitCodeProcess."""
    if not pid:
        return None
    pid = int(pid)
    if os.name == "nt":
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        k.CloseHandle.argtypes = (wintypes.HANDLE,)
        h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ctypes.get_last_error() == 5   # access denied: it exists
        code = wintypes.DWORD()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259   # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def clock(t):
    if not t:
        return "never"
    lt = time.localtime(t)
    same_day = time.strftime("%Y-%m-%d", lt) == time.strftime("%Y-%m-%d")
    return time.strftime("%H:%M:%S" if same_day else "%Y-%m-%d %H:%M", lt)


class Mutex:
    """An OS byte-range lock on one file, held for the milliseconds a command needs."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        if os.fstat(self.fd).st_size == 0:
            os.write(self.fd, b"\0")
        deadline = time.time() + 30
        while True:
            try:
                if os.name == "nt":
                    os.lseek(self.fd, 0, 0)
                    msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.time() > deadline:
                    os.close(self.fd)
                    raise SystemExit("fetch_gate: could not lock %s within 30 s" % self.path)
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            if os.name == "nt":
                os.lseek(self.fd, 0, 0)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)


def same_download(name):
    """A browser saves a second copy of a name as 'name (1).pdf'."""
    return re.sub(r" \(\d+\)(?=\.pdf$)", "", name, flags=re.I)


def recent_pdfs(folder, since):
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    out = []
    for n in names:
        if not n.lower().endswith(".pdf"):
            continue
        try:
            if os.path.getmtime(os.path.join(folder, n)) >= since:
                out.append(n)
        except OSError:
            pass
    return sorted(out)


def read_manifest(path):
    try:
        with open(path, encoding="utf-8") as fh:
            man = json.load(fh)
        return {str(m.get("doi", "")).lower(): m for m in man if isinstance(m, dict)}
    except (OSError, ValueError, TypeError):
        return {}


class Gate:
    def __init__(self, state_dir=None, owner=None, pid=None):
        self.dir = state_dir or default_state_dir()
        os.makedirs(self.dir, exist_ok=True)
        self.state_path = os.path.join(self.dir, "state.json")
        self.log_path = os.path.join(self.dir, "gate_log.jsonl")
        self.mutex = Mutex(os.path.join(self.dir, "gate.mutex"))
        self.owner = owner or os.environ.get("CLAUDE_CODE_HOST_SESSION_ID") or "terminal"
        env_pid = os.environ.get("CLAUDE_PID", "")
        self.pid = pid if pid is not None else (int(env_pid) if env_pid.isdigit() else None)

    # -- state and log (call only inside `with self.mutex`) --
    def _load(self):
        try:
            with open(self.state_path, encoding="utf-8") as fh:
                st = json.load(fh)
        except (OSError, ValueError):
            st = {}
        st.setdefault("lease", None)
        st.setdefault("holds", {})
        st.setdefault("last_slot", 0.0)
        st.setdefault("last_activity", 0.0)
        return st

    def _save(self, st):
        tmp = "%s.%d.tmp" % (self.state_path, os.getpid())
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(st, fh, indent=1, ensure_ascii=False)
        os.replace(tmp, self.state_path)

    def _log(self, ev, **kw):
        now = time.time()
        rec = dict(t=round(now, 1), time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                   ev=ev, owner=self.owner)
        rec.update({k: v for k, v in kw.items() if v not in (None, "")})
        try:
            if os.path.getsize(self.log_path) > LOG_MAX:
                with open(self.log_path, encoding="utf-8") as fh:
                    keep = fh.readlines()[-LOG_KEEP:]
                with open(self.log_path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.writelines(keep)
        except OSError:
            pass
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _records(self):
        out = []
        try:
            with open(self.log_path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass   # a line torn by a crash mid-write
        except OSError:
            pass
        return out

    @staticmethod
    def _stale(lease, now):
        if pid_alive(lease.get("pid")) is False:
            return "its session process %s has exited" % lease["pid"]
        idle = now - lease["beat"]
        if idle > lease["ttl"]:
            return "no activity for %d s (ttl %d s)" % (idle, lease["ttl"])
        return ""

    @staticmethod
    def _who(lease):
        return '"%s" (session %s, run %s)' % (lease.get("label") or "no label", lease["owner"], lease["run"])

    def _progress(self, lease, now):
        s = "%d of %d slots used" % (lease["done"], lease["total"]) if lease["total"] else "%d slots used" % lease["done"]
        s += ", last activity %d s ago" % (now - lease["beat"])
        left = lease["total"] - lease["done"]
        if lease["total"] and left > 0:
            per = max(lease["interval"], (lease["beat"] - lease["started"]) / lease["done"]) if lease["done"] else lease["interval"] + 20
            s += ", about %d min left" % math.ceil(left * per / 60)
        return s

    def _foreign(self, lease):
        """PDFs that landed in Downloads during the run under names outside its manifest."""
        names = {same_download(m.get("file", "")) for m in read_manifest(lease.get("manifest", "")).values()}
        seen = set(lease.get("seen", []))
        new = [n for n in recent_pdfs(lease["downloads"], lease["started"])
               if same_download(n) not in names and n not in seen]
        lease["seen"] = sorted(seen | set(new))
        return ["WARN a PDF outside this run's manifest landed in Downloads: %s (another session "
                "fetching without the gate, or the user saving by hand); tell the user" % n for n in new]

    def _active_holds(self, st, now):
        for pub in [p for p, h in st["holds"].items() if now - h["t"] > HOLD_TTL]:
            del st["holds"][pub]
        return st["holds"]

    # -- commands; each returns (exit code, output lines) --
    def start(self, manifest=None, label="", interval=INTERVAL, ttl=TTL, downloads=None):
        code, lines, _ = self._start(manifest, label, interval, ttl, downloads, nested=False)
        return code, lines

    def enter(self, manifest=None, label=""):
        """For a script that fetches in-process: open a run, or run inside this owner's open one.
        Returns (code, lines, opened); call end() afterwards only if opened."""
        return self._start(manifest, label, INTERVAL, TTL, None, nested=True)

    def _start(self, manifest, label, interval, ttl, downloads, nested):
        manifest = os.path.abspath(manifest) if manifest else ""
        downloads = downloads or os.path.join(os.path.expanduser("~"), "Downloads")
        total = len(read_manifest(manifest)) if manifest else 0
        notes = []
        with self.mutex:
            st = self._load()
            now = time.time()
            lease = st["lease"]
            if lease and lease["owner"] == self.owner:
                if not nested:
                    lease.update(manifest=manifest, label=label, total=lease["done"] + total,
                                 interval=interval, ttl=ttl, downloads=downloads)
                lease.update(beat=now, pid=self.pid or lease.get("pid"))
                st["last_activity"] = now
                self._log("continue", run=lease["run"], label=label)
                self._save(st)
                return 0, ["GO run=%s since=%d interval=%d ttl=%d (this session's run, open since %s, continues)"
                           % (lease["run"], lease["started"], lease["interval"], lease["ttl"], clock(lease["started"]))], False
            if lease:
                why = self._stale(lease, now)
                if not why:
                    return 3, ["BUSY %s has held the lease since %s; %s. Do not fetch: tell the user, "
                               "run `fetch_gate.py wait` in the background, then start again."
                               % (self._who(lease), clock(lease["started"]), self._progress(lease, now))], False
                notes.append("TOOK-OVER the lease of %s: %s" % (self._who(lease), why))
                self._log("takeover", run=lease["run"], note=why, prev_owner=lease["owner"], prev_label=lease.get("label"))
            else:
                since = max(st["last_activity"], now - WARN_WINDOW)
                stray = recent_pdfs(downloads, since)
                if stray:
                    notes.append("WARN %d PDF(s) landed in Downloads since the last gated activity (%s) while no "
                                 "run was open: %s. Another session may be fetching without the gate, or the user "
                                 "saved them; tell the user before fetching."
                                 % (len(stray), clock(since), ", ".join(stray[:5]) + (" ..." if len(stray) > 5 else "")))
            run = secrets.token_hex(4)
            st["lease"] = dict(run=run, owner=self.owner, pid=self.pid, label=label, manifest=manifest,
                               downloads=downloads, started=now, beat=now, interval=interval, ttl=ttl,
                               total=total, done=0, seen=[])
            st["last_activity"] = now
            self._log("start", run=run, label=label, manifest=manifest, total=total, pid=self.pid)
            self._save(st)
        holds = ["NOTE publisher %s is on hold since %s: %s" % (p, clock(h["t"]), h["reason"])
                 for p, h in sorted(st["holds"].items())]
        return 0, ["GO run=%s since=%d interval=%d ttl=%d" % (run, now, interval, ttl)] + notes + holds, True

    def next(self, doi, pub=None):
        with self.mutex:
            st = self._load()
            now = time.time()
            lease = st["lease"]
            if not lease:
                return 4, ["LOST no run is open on this machine (it was ended or cleared). Stop fetching, "
                           "run the collector, and start again only if the user wants to continue."]
            if lease["owner"] != self.owner:
                return 4, ["LOST the lease is now held by %s since %s. Stop fetching, run the collector, report."
                           % (self._who(lease), clock(lease["started"]))]
            entry = read_manifest(lease["manifest"]).get(doi.lower())
            pub = pub or (entry or {}).get("pub") or "unknown"
            lease.update(beat=now, pid=self.pid or lease.get("pid"))
            st["last_activity"] = now
            warns = self._foreign(lease)
            if entry is None and lease["manifest"]:
                warns.append("WARN %s is not in this run's manifest" % doi)
            hold = self._active_holds(st, now).get(pub)
            if hold:
                self._log("held", run=lease["run"], doi=doi, pub=pub)
                self._save(st)
                return 5, ["HOLD %s since %s (%s): skip this entry and the rest of this publisher"
                           % (pub, clock(hold["t"]), hold["reason"])] + warns
            slot = max(now, st["last_slot"] + lease["interval"])
            st["last_slot"] = slot
            lease["done"] += 1
            self._log("next", run=lease["run"], doi=doi, pub=pub, slot=round(slot, 1))
            self._save(st)
        return 0, ["WAIT %d (slot %s, %s)" % (math.ceil(slot - now - 0.05), clock(slot), pub)] + warns

    def touch(self):
        """Renew this owner's lease without reserving a slot; False when it is no longer ours."""
        with self.mutex:
            st = self._load()
            lease = st["lease"]
            if not lease or lease["owner"] != self.owner:
                return False
            lease["beat"] = st["last_activity"] = time.time()
            self._save(st)
            return True

    def hold(self, pub, reason):
        with self.mutex:
            st = self._load()
            lease = st["lease"]
            label = lease.get("label", "") if lease and lease["owner"] == self.owner else ""
            st["holds"][pub] = dict(t=time.time(), owner=self.owner, label=label, reason=reason)
            self._log("hold", pub=pub, note=reason)
            self._save(st)
        return 0, ["HELD %s for every session until `fetch_gate.py clear --pub %s` or 24 h" % (pub, pub)]

    def clear(self, pub=None, run=False):
        lines = []
        with self.mutex:
            st = self._load()
            if pub:
                h = st["holds"].pop(pub, None)
                self._log("clear", pub=pub)
                lines.append("CLEARED hold on %s" % pub if h else "NONE no hold on %s" % pub)
            if run:
                lease = st["lease"]
                st["lease"] = None
                if lease:
                    self._log("clear", run=lease["run"], prev_owner=lease["owner"], prev_label=lease.get("label"))
                    lines.append("CLEARED the lease of %s" % self._who(lease))
                else:
                    lines.append("NONE no lease to clear")
            self._save(st)
        return 0, lines or ["NONE nothing to clear (give --pub or --run)"]

    def end(self, aborted=False):
        with self.mutex:
            st = self._load()
            lease = st["lease"]
            if not lease or lease["owner"] != self.owner:
                return 0, ["NONE this session has no open run" + (
                    "; the lease is held by %s" % self._who(lease) if lease else "")]
            warns = self._foreign(lease)
            st["lease"] = None
            st["last_activity"] = time.time()
            self._log("end", run=lease["run"], note="aborted" if aborted else "")
            self._save(st)
            recs = self._records()
        mine = [r for r in recs if r.get("ev") == "next" and r.get("run") == lease["run"]]
        slots = sorted(r["slot"] for r in recs if r.get("ev") == "next" and "slot" in r
                       and r["slot"] >= lease["started"] - 4 * lease["interval"])
        gaps = [b - a for a, b in zip(slots, slots[1:])]
        return 0, ["ENDED run=%s%s: %d slots, smallest gap between slots on the machine %s, interval %d s, "
                   "%d PDF(s) outside the manifest seen in Downloads"
                   % (lease["run"], " (aborted)" if aborted else "", len(mine),
                      "%.0f s" % min(gaps) if gaps else "n/a", lease["interval"], len(lease["seen"]))] + warns

    def status(self):
        with self.mutex:
            st = self._load()
            now = time.time()
            recs = self._records()[-8:]
            lease = st["lease"]
            holds = self._active_holds(st, now)
        lines = []
        if lease:
            why = self._stale(lease, now)
            alive = pid_alive(lease.get("pid"))
            lines.append("%s %s since %s; %s; pid %s %s; interval %d s, ttl %d s"
                         % ("STALE" if why else "HELD", self._who(lease), clock(lease["started"]),
                            self._progress(lease, now), lease.get("pid"),
                            {True: "alive", False: "exited", None: "unknown"}[alive], lease["interval"], lease["ttl"]))
            if why:
                lines.append("  stale because %s; the next start takes it over" % why)
        else:
            lines.append("FREE no run is open")
        for p, h in sorted(holds.items()):
            lines.append("hold %s since %s: %s" % (p, clock(h["t"]), h["reason"]))
        lines.append("last slot on the machine: %s" % clock(st["last_slot"]))
        for r in recs:
            lines.append("  %s %-8s %s %s %s" % (r.get("time", "")[11:], r.get("ev", ""), r.get("label") or r.get("run", ""),
                                               r.get("doi", r.get("pub", "")), r.get("note", "")))
        return 0, lines

    def wait(self, max_s=10800, poll=20):
        t0 = time.time()
        while True:
            with self.mutex:
                st = self._load()
                now = time.time()
                lease = st["lease"]
                why = self._stale(lease, now) if lease else ""
            if not lease or lease["owner"] == self.owner or why:
                return 0, ["FREE after %d s%s; run start now" % (now - t0, " (%s: %s)" % (self._who(lease), why) if why else "")]
            if now - t0 >= max_s:
                return 3, ["STILL-BUSY after %d s: %s; %s" % (now - t0, self._who(lease), self._progress(lease, now))]
            time.sleep(min(poll, max(1, max_s - (now - t0))))


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state-dir", default=None)
    common.add_argument("--owner", default=None)
    ap = argparse.ArgumentParser(description="One fetch loop per machine for the paper-download skill.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start", parents=[common])
    p.add_argument("--manifest", default=None)
    p.add_argument("--label", default="")
    p.add_argument("--interval", type=float, default=INTERVAL)
    p.add_argument("--ttl", type=float, default=TTL)
    p.add_argument("--downloads", default=None)
    p = sub.add_parser("next", parents=[common])
    p.add_argument("--doi", required=True)
    p.add_argument("--pub", default=None)
    p = sub.add_parser("hold", parents=[common])
    p.add_argument("--pub", required=True)
    p.add_argument("--reason", required=True)
    p = sub.add_parser("clear", parents=[common])
    p.add_argument("--pub", default=None)
    p.add_argument("--run", action="store_true")
    p = sub.add_parser("end", parents=[common])
    p.add_argument("--aborted", action="store_true")
    sub.add_parser("status", parents=[common])
    p = sub.add_parser("wait", parents=[common])
    p.add_argument("--max", type=float, default=10800)
    p.add_argument("--poll", type=float, default=20)
    a = ap.parse_args(argv)
    g = Gate(a.state_dir, a.owner)
    if a.cmd == "start":
        code, lines = g.start(a.manifest, a.label, a.interval, a.ttl, a.downloads)
    elif a.cmd == "next":
        code, lines = g.next(a.doi, a.pub)
    elif a.cmd == "hold":
        code, lines = g.hold(a.pub, a.reason)
    elif a.cmd == "clear":
        code, lines = g.clear(a.pub, a.run)
    elif a.cmd == "end":
        code, lines = g.end(a.aborted)
    elif a.cmd == "status":
        code, lines = g.status()
    else:
        code, lines = g.wait(a.max, a.poll)
    print("\n".join(lines), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
