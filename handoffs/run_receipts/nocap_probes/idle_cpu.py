import os, subprocess, sys, time, psutil
cases = {
  "sleep_only": "import time; time.sleep(40)",
  "sleep_with_psutil_sampler_0.5s": "import threading,time,psutil\np=psutil.Process()\ndef f():\n    while True:\n        p.memory_info(); [c.memory_info() for c in p.children(recursive=True)]; time.sleep(0.5)\nthreading.Thread(target=f,daemon=True).start(); time.sleep(40)",
  "blocked_on_lock": "import threading; l=threading.Lock(); l.acquire(); l.acquire()",
  "blocking_read_stdin": "import sys; sys.stdin.read()",
}
for name, code in cases.items():
    pr = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.PIPE)
    time.sleep(3); p = psutil.Process(pr.pid); t0 = sum(p.cpu_times()[:2]); w0 = time.time()
    time.sleep(30); t1 = sum(p.cpu_times()[:2]); w1 = time.time()
    print(f"{name}: {(t1-t0)/(w1-w0):.4f} core")
    pr.kill()
