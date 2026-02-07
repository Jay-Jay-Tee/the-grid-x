#!/usr/bin/env python3
"""Submit a small job to the coordinator and poll until completion.
Usage: python scripts/submit_and_wait.py --coordinator 192.168.42.46 --user soorya --code "print('hi')"
"""
import argparse
import requests
import time

parser = argparse.ArgumentParser()
parser.add_argument("--coordinator", default="127.0.0.1", help="Coordinator IP")
parser.add_argument("--port", type=int, default=8081, help="Coordinator HTTP port")
parser.add_argument("--user", required=True, help="User ID")
parser.add_argument("--language", default="python", help="Language")
parser.add_argument("--timeout", type=int, default=120, help="Max seconds to wait for job result")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--code", help="Inline code to run")
group.add_argument("--file", help="Path to source file")
args = parser.parse_args()

if args.file:
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
    except OSError as e:
        print(f"Failed to read file {args.file}: {e}")
        raise SystemExit(1)
else:
    code = args.code

base = f"http://{args.coordinator}:{args.port}"
try:
    print(f"Posting job to {base}/jobs as user {args.user}...")
    resp = requests.post(f"{base}/jobs", json={"user_id": args.user, "code": code, "language": args.language}, timeout=10)
    try:
        resp.raise_for_status()
    except Exception as e:
        print("HTTP error when submitting job:", resp.status_code, resp.text)
        raise
    job_id = resp.json().get("job_id")
    if not job_id:
        print("Coordinator response missing job_id:", resp.text)
        raise SystemExit(1)
    print("Submitted job_id:", job_id)

    # Poll
    start = time.time()
    while time.time() - start < args.timeout:
        time.sleep(2)
        try:
            r = requests.get(f"{base}/jobs/{job_id}", timeout=10)
            if r.status_code == 404:
                print("Job not found yet; retrying...")
                continue
            r.raise_for_status()
            job = r.json()
            status = job.get("status")
            print(f"Status: {status}")
            if status in ("completed", "failed", "error"):
                print("Final job payload:")
                print(job)
                # Print stdout/stderr
                if job.get('stdout'):
                    print("\n--- STDOUT ---\n", job.get('stdout'))
                if job.get('stderr'):
                    print("\n--- STDERR ---\n", job.get('stderr'))
                break
        except requests.RequestException as e:
            print("Error polling job:", e)
            time.sleep(2)
    else:
        print("Timed out waiting for job result")

except Exception as e:
    print("Error:", e)
    raise
