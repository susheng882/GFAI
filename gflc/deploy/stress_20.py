# -*- coding: utf-8 -*-
"""N4 生产栈冒烟：20 并发压测（仅标准库，不依赖 locust/httpx）。

用法：
  python deploy/stress_20.py --url http://127.0.0.1/health --concurrency 20 --seconds 600
  python deploy/stress_20.py --url http://127.0.0.1/ --seconds 5   # 本机快速自检

判定：错误率 ≤2% 且 P95 延迟达标（默认 3s）才算通过。
说明：本机数据不能替代线上灰度压测（G2），生产需在灰度环境用真实流量复测。
"""
import argparse
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser(description="GFLC 20 并发压测")
    ap.add_argument("--url", default="http://127.0.0.1/health")
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--seconds", type=float, default=600, help="压测时长秒数，默认 600（10min）")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--max-error-rate", type=float, default=2.0, help="允许错误率百分比，默认 2")
    ap.add_argument("--p95-limit", type=float, default=3.0, help="P95 延迟上限秒，默认 3")
    args = ap.parse_args()

    # 绕过 HTTP_PROXY/HTTPS_PROXY，避免本机压测被代理劫持导致延迟虚高
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.time() + args.seconds
    latencies: list[float] = []
    counts = {"ok": 0, "err": 0}
    lock = threading.Lock()

    def worker():
        while time.time() < deadline:
            t0 = time.time()
            try:
                with opener.open(args.url, timeout=args.timeout) as r:
                    r.read(2048)
                    ok = 200 <= r.status < 400
            except Exception:
                ok = False
            dt = time.time() - t0
            with lock:
                if ok:
                    counts["ok"] += 1
                else:
                    counts["err"] += 1
                latencies.append(dt)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(args.concurrency)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total = counts["ok"] + counts["err"]
    err_rate = counts["err"] / total * 100 if total else 100.0
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else float("inf")
    print(f"URL={args.url}  并发={args.concurrency}  时长={args.seconds}s")
    print(f"总请求={total}  成功={counts['ok']}  错误={counts['err']}  错误率={err_rate:.2f}%")
    print(f"平均延迟={(statistics.mean(latencies) if latencies else 0):.3f}s  P95={p95:.3f}s")
    ok = err_rate <= args.max_error_rate and p95 <= args.p95_limit
    print("结果：" + ("通过（本机参考值，线上需复测）" if ok else "未通过，需排查"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
