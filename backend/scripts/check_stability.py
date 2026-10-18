"""Sequential, low-frequency GET availability samples using only the stdlib."""

import argparse
import ctypes
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def positive_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("seconds must be a positive finite number")
    return seconds


def public_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise argparse.ArgumentTypeError("URL must be an absolute HTTP(S) URL")
    if parts.username or parts.password or parts.fragment:
        raise argparse.ArgumentTypeError("URL must not contain credentials or a fragment")
    return value


def prevent_automatic_sleep() -> None:
    """Keep Windows awake only while this measuring process is running."""
    if sys.platform != "win32":
        raise RuntimeError("--prevent-sleep is supported only on Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.SetThreadExecutionState.argtypes = [ctypes.c_ulong]
    kernel32.SetThreadExecutionState.restype = ctypes.c_ulong
    if not kernel32.SetThreadExecutionState(0x80000000 | 0x00000001):
        raise OSError(ctypes.get_last_error(), "could not prevent automatic sleep")


def sample(url: str, timeout_seconds: float) -> dict:
    requested_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    started = time.monotonic()
    status_code = None
    error = None
    request = Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": "TYPEUP-stability-check/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = response.status
            response.read()
    except HTTPError as exc:
        status_code = exc.code
        error = f"HTTP {exc.code}: {exc.reason}"
    except (URLError, TimeoutError, OSError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    return {
        "requested_at_utc": requested_at,
        "url": url,
        "status_code": status_code,
        "latency_ms": round((time.monotonic() - started) * 1000, 2),
        "error": error,
    }


def percentile_nearest_rank(values: list[float], percent: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(percent / 100 * len(ordered)) - 1]


def summarize(records: list[dict], urls: list[str], elapsed_seconds: float) -> dict:
    by_url = {}
    for url in urls:
        rows = [record for record in records if record["url"] == url]
        successful = [row for row in rows if row["status_code"] is not None and 200 <= row["status_code"] < 300]
        longest_failure_run = 0
        current_failure_run = 0
        for row in rows:
            if row["status_code"] is not None and 200 <= row["status_code"] < 300:
                current_failure_run = 0
            else:
                current_failure_run += 1
                longest_failure_run = max(longest_failure_run, current_failure_run)
        latencies = [row["latency_ms"] for row in successful]
        by_url[url] = {
            "samples": len(rows),
            "successful_samples": len(successful),
            "success_rate_percent": round(100 * len(successful) / len(rows), 2) if rows else None,
            "latency_p50_ms": percentile_nearest_rank(latencies, 50),
            "latency_p95_ms": percentile_nearest_rank(latencies, 95),
            "longest_consecutive_failures": longest_failure_run,
            "first_sample_at_utc": rows[0]["requested_at_utc"] if rows else None,
            "last_sample_at_utc": rows[-1]["requested_at_utc"] if rows else None,
        }
    return {
        "actual_elapsed_seconds": round(elapsed_seconds, 2),
        "total_samples": len(records),
        "note": "Success rates describe sampled GET requests only, not uptime between samples.",
        "urls": by_url,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", type=public_url, required=True, help="Public GET URL; repeat for multiple URLs")
    parser.add_argument("--duration-seconds", type=positive_seconds, required=True)
    parser.add_argument("--interval-seconds", type=positive_seconds, default=60.0)
    parser.add_argument("--timeout-seconds", type=positive_seconds, default=15.0)
    parser.add_argument("--prevent-sleep", action="store_true", help="Prevent automatic Windows sleep while this process runs")
    parser.add_argument("--output", type=Path, required=True, help="New JSONL evidence file; existing files are not overwritten")
    args = parser.parse_args()
    if len(set(args.url)) != len(args.url):
        parser.error("duplicate URLs are not allowed")

    if args.prevent_sleep:
        prevent_automatic_sleep()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    started = time.monotonic()
    deadline = started + args.duration_seconds
    interrupted = False
    with args.output.open("x", encoding="utf-8") as evidence:
        try:
            tick = 0
            next_at = started
            while next_at < deadline:
                time.sleep(max(0.0, next_at - time.monotonic()))
                if time.monotonic() >= deadline:
                    break
                request_started = time.monotonic()
                url = args.url[tick % len(args.url)]
                remaining = deadline - request_started
                record = sample(url, min(args.timeout_seconds, remaining))
                evidence.write(json.dumps(record, ensure_ascii=False) + "\n")
                evidence.flush()
                records.append(record)
                tick += 1
                next_at = request_started + args.interval_seconds
            time.sleep(max(0.0, deadline - time.monotonic()))
        except KeyboardInterrupt:
            interrupted = True

    summary = summarize(records, args.url, time.monotonic() - started)
    summary["interrupted"] = interrupted
    summary["output"] = str(args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
