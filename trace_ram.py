"""
The program is to trace whether the worker application fully utilizes available CPU cores and RAM, or there's wasted
capacity in AWS.
"""
import time
from datetime import datetime

import pandas as pd
import psutil

print("Logical Cores:", psutil.cpu_count(logical=True))

records = []
worker_seen = False

while True:
    worker_found = False

    heaviest_worker = None
    heaviest_ram = -1

    for proc in psutil.process_iter(attrs=["pid", "name", "memory_info"]):
        try:
            name = proc.info["name"]

            if name and "WORKER" in name.upper():
                worker_found = True
                worker_seen = True

                ram_mb = (
                proc.info["memory_info"].rss / 1024**2)

                if ram_mb > heaviest_ram:
                    heaviest_ram = ram_mb
                    heaviest_worker = proc

        except Exception:
            pass
            
    if heaviest_worker is not None:
        records.append(
            {
                "Time": datetime.now(),
                "PID": heaviest_worker.pid,
                "RAM_MB": round(heaviest_ram, 2),
                "CPU_%": heaviest_worker.cpu_percent(interval=None),
            }
        )

    if worker_seen and not worker_found:
        print("Worker Application finished.")
        break

    time.sleep(1)

pd.DataFrame(records).to_csv("worker_monitor.csv", index=False)

df = pd.read_csv("worker_monitor.csv")
print("Peak RAM (GB):", df["RAM_MB"].max() / 1024)
print("Average RAM (GB):", df["RAM_MB"].mean() / 1024)

print("Peak CPU (%):", df["CPU_%"].max())
print("Average CPU (%):", df["CPU_%"].mean())

logical_cores = psutil.cpu_count(logical=True)
avg_core_utilization = df["CPU_%"].mean() / logical_cores

print("Average Core Utilization (%):", round(avg_core_utilization, 2))
