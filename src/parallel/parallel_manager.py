import concurrent.futures
import threading
import time
from pathlib import Path
import json

LOG = Path("logs/parallel.log")
LOG.parent.mkdir(parents=True, exist_ok=True)

class ParallelManager:
    def __init__(self, max_workers=3):
        self.max_workers = max(1, min(int(max_workers), 4))
        self.lock = threading.Lock()

    def _log(self, item):
        with self.lock:
            with LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def run_jobs(self, jobs):
        """
        jobs:
        [
          {"name":"job1","func":callable,"args":[],"kwargs":{},"safe_parallel":True}
        ]

        Unsafe jobs run sequentially after safe jobs.
        """
        safe = [j for j in jobs if j.get("safe_parallel", False)]
        unsafe = [j for j in jobs if not j.get("safe_parallel", False)]

        results = []

        if safe:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                futures = {}
                for job in safe:
                    future = ex.submit(
                        job["func"],
                        *(job.get("args") or []),
                        **(job.get("kwargs") or {})
                    )
                    futures[future] = job

                for future in concurrent.futures.as_completed(futures):
                    job = futures[future]
                    started = time.time()
                    try:
                        value = future.result()
                        item = {
                            "name": job["name"],
                            "ok": True,
                            "result": value,
                            "parallel": True
                        }
                    except Exception as e:
                        item = {
                            "name": job["name"],
                            "ok": False,
                            "error": f"{type(e).__name__}: {e}",
                            "parallel": True
                        }
                    item["duration_s"] = round(time.time() - started, 3)
                    results.append(item)
                    self._log(item)

        for job in unsafe:
            started = time.time()
            try:
                value = job["func"](
                    *(job.get("args") or []),
                    **(job.get("kwargs") or {})
                )
                item = {
                    "name": job["name"],
                    "ok": True,
                    "result": value,
                    "parallel": False
                }
            except Exception as e:
                item = {
                    "name": job["name"],
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                    "parallel": False
                }
            item["duration_s"] = round(time.time() - started, 3)
            results.append(item)
            self._log(item)

        return results
