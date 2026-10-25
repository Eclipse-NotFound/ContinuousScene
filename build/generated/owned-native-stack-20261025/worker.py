"""Owned disposable fixture. Never used to launch or attach to a game."""
import json
import os
import sys
import threading
import time

stop = threading.Event()


def sleeper():
    while not stop.wait(0.25):
        pass


t = threading.Thread(target=sleeper, name="owned-sleep-fixture")
t.start()
print(json.dumps({"pid": os.getpid(), "busy_tid": threading.get_native_id(),
                  "sleep_tid": t.native_id}), flush=True)
# Parent assigns the kill-on-close job and confirms ownership before workload.
if sys.stdin.readline().strip() == "go":
    deadline = time.monotonic() + 25
    x = 1
    while time.monotonic() < deadline:
        for _ in range(10000):
            x = (x * 1664525 + 1013904223) & 0xffffffff
stop.set()
t.join(timeout=1)
