"""Tests for fetch_gate.py: separate processes play separate sessions on one state folder.

Run: python -I scripts/tests/test_fetch_gate.py   (standard library only, about 15 s)

Each fake session is a process environment with its own CLAUDE_CODE_HOST_SESSION_ID and a
CLAUDE_PID that points at a helper process, so killing the helper makes the session "dead".
Covered: one GO among racing starts, BUSY, slot spacing, LOST for a non-owner, takeover of a
dead session and of an expired heartbeat (and LOST for the old owner afterwards), handover
spacing, the same session continuing its run, holds, idempotent end, wait, the Downloads
warnings, and fetch_oa_pdfs.py refusing to run while another session holds the lease, also
when it runs outside Claude Code (no session id: the run is owned by its own process).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(os.path.dirname(HERE), "fetch_gate.py")
OA = os.path.join(os.path.dirname(HERE), "fetch_oa_pdfs.py")


def sleeper():
    return subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(120)"])


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.tmp.name, "state")
        self.dl = os.path.join(self.tmp.name, "Downloads")
        os.makedirs(self.dl)
        self.manifest = os.path.join(self.tmp.name, "manifest.json")
        with open(self.manifest, "w", encoding="utf-8", newline="\n") as fh:
            json.dump([
                dict(doi="10.1/a", first="Alpha", year="2020", file="Alpha - 2020 - One.pdf", pub="springer",
                     status="closed", landing="https://doi.org/10.1/a", pdf="", pdfs=[]),
                dict(doi="10.1/b", first="Beta", year="2021", file="Beta - 2021 - Two.pdf", pub="iop",
                     status="closed", landing="https://doi.org/10.1/b", pdf="", pdfs=[]),
            ], fh)
        self.procs = {}

    def tearDown(self):
        for p in self.procs.values():
            if p.poll() is None:
                p.kill()
                p.wait()
        self.tmp.cleanup()

    def env(self, who):
        if who not in self.procs:
            self.procs[who] = sleeper()
        e = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "PAPER_DOWNLOAD"))}
        e.update(CLAUDE_CODE_HOST_SESSION_ID="local_" + who, CLAUDE_PID=str(self.procs[who].pid),
                 PAPER_DOWNLOAD_STATE=self.state, PYTHONIOENCODING="utf-8")
        return e

    def kill(self, who):
        self.procs[who].kill()
        self.procs[who].wait()

    def gate(self, who, *args, script=GATE):
        env = self.env(who) if who else self.bare_env()
        r = subprocess.run([sys.executable, "-I", script] + list(args), env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        return r.returncode, r.stdout.strip()

    def bare_env(self):
        """A shell of another agent: no Claude Code session variables."""
        e = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "PAPER_DOWNLOAD"))}
        e.update(PAPER_DOWNLOAD_STATE=self.state, PYTHONIOENCODING="utf-8")
        return e

    def start(self, who, *extra):
        return self.gate(who, "start", "--manifest", self.manifest, "--label", "test " + who,
                         "--downloads", self.dl, *extra)

    def wait_s(self, out):
        return int(re.match(r"WAIT (\d+)", out).group(1))

    def test_racing_starts_give_one_go(self):
        names = ["r%d" % i for i in range(6)]
        envs = {n: self.env(n) for n in names}
        ps = [subprocess.Popen([sys.executable, "-I", GATE, "start", "--manifest", self.manifest, "--label", n,
                                "--downloads", self.dl], env=envs[n], stdout=subprocess.PIPE, text=True)
              for n in names]
        outs = [(p.wait(timeout=60), p.stdout.read()) for p in ps]
        for p in ps:
            p.stdout.close()
        self.assertEqual(sorted(c for c, _ in outs), [0] + [3] * 5, outs)
        self.assertEqual(sum(o.startswith("GO") for _, o in outs), 1)

    def test_busy_slots_lost(self):
        c, out = self.start("a")
        self.assertEqual(c, 0, out)
        self.assertTrue(out.startswith("GO run="), out)
        c, out = self.start("b")
        self.assertEqual(c, 3, out)
        self.assertIn('BUSY "test a"', out)
        self.assertIn("0 of 2 slots used", out)
        c, out = self.gate("a", "next", "--doi", "10.1/a")
        self.assertEqual((c, self.wait_s(out)), (0, 0), out)
        c, out = self.gate("a", "next", "--doi", "10.1/b")
        self.assertEqual(c, 0, out)
        self.assertGreaterEqual(self.wait_s(out), 28, out)   # the second slot is one interval later
        c, out = self.gate("b", "next", "--doi", "10.1/a")
        self.assertEqual(c, 4, out)
        self.assertTrue(out.startswith("LOST the lease is now held by"), out)
        c, out = self.gate("a", "end")
        self.assertEqual(c, 0, out)
        self.assertRegex(out, r"ENDED run=\w+: 2 slots, smallest gap between slots on the machine 30 s")
        c, out = self.gate("a", "end")
        self.assertEqual(c, 0)
        self.assertTrue(out.startswith("NONE"), out)

    def test_dead_session_is_taken_over(self):
        self.start("a")
        self.gate("a", "next", "--doi", "10.1/a")
        self.kill("a")
        c, out = self.gate("b", "status")
        self.assertTrue(out.startswith("STALE"), out)
        self.assertIn("has exited", out)
        c, out = self.start("b")
        self.assertEqual(c, 0, out)
        self.assertTrue(out.startswith("GO"), out)
        self.assertIn('TOOK-OVER the lease of "test a"', out)
        self.assertIn("has exited", out)
        c, out = self.gate("b", "next", "--doi", "10.1/b")   # the takeover keeps the spacing
        self.assertGreaterEqual(self.wait_s(out), 28, out)

    def test_expired_heartbeat_is_taken_over_and_old_owner_lost(self):
        self.start("a", "--ttl", "1")
        time.sleep(1.5)                       # session a is alive but silent past its ttl
        c, out = self.start("b")
        self.assertEqual(c, 0, out)
        self.assertIn("no activity for", out)
        c, out = self.gate("a", "next", "--doi", "10.1/a")
        self.assertEqual(c, 4, out)
        self.assertIn('held by "test b"', out)

    def test_handover_spacing_and_continue(self):
        self.start("a")
        self.gate("a", "next", "--doi", "10.1/a")
        self.gate("a", "end")
        c, out = self.start("b")
        self.assertEqual(c, 0, out)
        c, out = self.start("b")
        self.assertEqual(c, 0, out)
        self.assertIn("continues", out)
        c, out = self.gate("b", "next", "--doi", "10.1/a")
        self.assertGreaterEqual(self.wait_s(out), 27, out)   # a's last slot was moments ago

    def test_hold_and_clear(self):
        self.start("a")
        c, out = self.gate("a", "hold", "--pub", "iop", "--reason", "Radware captcha")
        self.assertTrue(out.startswith("HELD iop"), out)
        c, out = self.gate("a", "next", "--doi", "10.1/b")
        self.assertEqual(c, 5, out)
        self.assertIn("Radware captcha", out)
        self.gate("a", "end")
        c, out = self.start("b")
        self.assertIn("NOTE publisher iop is on hold", out)
        self.gate("b", "clear", "--pub", "iop")
        c, out = self.gate("b", "next", "--doi", "10.1/b")
        self.assertEqual(c, 0, out)

    def test_wait(self):
        self.start("a")
        c, out = self.gate("b", "wait", "--max", "1", "--poll", "0.3")
        self.assertEqual(c, 3, out)
        self.assertTrue(out.startswith("STILL-BUSY"), out)
        self.kill("a")
        c, out = self.gate("b", "wait", "--max", "5", "--poll", "0.3")
        self.assertEqual(c, 0, out)
        self.assertIn("has exited", out)

    def test_downloads_warnings(self):
        def touch(name):
            with open(os.path.join(self.dl, name), "wb") as fh:
                fh.write(b"%PDF-1.4 test")
        touch("stray.pdf")                    # landed while no run was open
        c, out = self.start("a")
        self.assertIn("WARN 1 PDF(s) landed in Downloads", out)
        time.sleep(0.05)
        touch("Alpha - 2020 - One.pdf")       # this run's own file: no warning
        touch("Alpha - 2020 - One (1).pdf")   # a browser's second copy of it: no warning
        touch("other session.pdf")            # someone else's: one warning, once
        c, out = self.gate("a", "next", "--doi", "10.1/a")
        self.assertEqual(out.count("WARN"), 1, out)
        self.assertIn("other session.pdf", out)
        c, out = self.gate("a", "next", "--doi", "10.1/b")
        self.assertNotIn("WARN", out)
        c, out = self.gate("a", "end")
        self.assertIn("1 PDF(s) outside the manifest", out)

    def test_script_route_respects_the_lease(self):
        staging = os.path.join(self.tmp.name, "staging")
        self.start("a")
        c, out = self.gate("b", self.manifest, staging, script=OA)
        self.assertEqual(c, 3, out)
        self.assertTrue(out.startswith("BUSY"), out)
        self.assertNotIn("skip", out)
        self.gate("a", "end")
        c, out = self.gate("b", self.manifest, staging, script=OA)
        self.assertEqual(c, 0, out)
        self.assertIn("saved or present: 0 / 2", out)
        self.assertIn("ENDED", out)
        c, out = self.gate("a", "status")
        self.assertTrue(out.startswith("FREE"), out)

    def test_script_route_outside_claude_code(self):
        staging = os.path.join(self.tmp.name, "staging")
        self.start("a")
        c, out = self.gate(None, self.manifest, staging, script=OA)
        self.assertEqual(c, 3, out)
        self.assertTrue(out.startswith("BUSY"), out)
        self.gate("a", "end")
        c, out = self.gate(None, self.manifest, staging, script=OA)
        self.assertEqual(c, 0, out)
        self.assertIn("ENDED", out)
        self.assertNotIn("continues", out)
        c, out = self.gate("a", "status")
        self.assertTrue(out.startswith("FREE"), out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
