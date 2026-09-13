"""
Download MusicCaps audio clips and produce a manifest linking each
downloaded file back to its metadata row.

Usage:
    python download_audio.py [--workers N] [--save_path metadata/wav]
"""
import argparse
import csv
import datetime as dt
import multiprocessing as mp
import os
import random
import threading
import time

import pandas as pd
from tqdm import tqdm
from yt_dlp import YoutubeDL

METADATA_CSV = "metadata/musiccaps-public.csv"
MANIFEST_CSV = "metadata/download_manifest.csv"


def _download_one(args):
    ytid, start, end, out_dir, cookies, sleep_min, sleep_max = args
    filename = f"[{ytid}]-[{int(start)}-{int(end)}].wav"
    out_path = os.path.join(out_dir, filename)

    if os.path.exists(out_path):
        return ytid, start, end, filename, "already_exists", ""

    start_ms, end_ms = int(start) * 1000, int(end) * 1000
    start_dt, end_dt = dt.timedelta(milliseconds=start_ms), dt.timedelta(milliseconds=end_ms)

    if sleep_max > 0:
        time.sleep(random.uniform(sleep_min, sleep_max))

    ydl_opts = {
        "outtmpl": os.path.join(out_dir, f"[{ytid}]-[{int(start)}-{int(end)}].%(ext)s"),
        "format": "bestaudio[ext=webm]/bestaudio/best",
        "external_downloader": "ffmpeg",
        "external_downloader_args": [
            "-ss", str(start_dt),
            "-to", str(end_dt),
            "-loglevel", "panic",
        ],
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
        "no_warnings": True,
        "no-mtime": True,
        "socket_timeout": 15,
        "retries": 1,
        "extractor_retries": 1,
        "noplaylist": True,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }
    if cookies:
        ydl_opts["cookiefile"] = cookies
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={ytid}"])
        if os.path.exists(out_path):
            return ytid, start, end, filename, "ok", ""
        else:
            return ytid, start, end, filename, "failed", "file_not_produced"
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return ytid, start, end, filename, "failed", str(e)[:300]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save_path", default="metadata/wav", type=str)
    parser.add_argument("--workers", default=12, type=int)
    parser.add_argument("--limit", default=None, type=int, help="only attempt first N rows (testing)")
    parser.add_argument("--cookies", default=None, type=str, help="path to a Netscape-format cookies.txt")
    parser.add_argument("--sleep-min", default=0.0, type=float, help="min random delay (s) before each request")
    parser.add_argument("--sleep-max", default=0.0, type=float, help="max random delay (s) before each request")
    parser.add_argument("--only-failed", action="store_true", help="only retry rows marked failed in the manifest")
    args = parser.parse_args()

    os.makedirs(args.save_path, exist_ok=True)

    meta = pd.read_csv(METADATA_CSV)

    # Resume support: load already-recorded manifest results.
    done_ytids = set()
    failed_ytids = None
    manifest_exists = os.path.exists(MANIFEST_CSV)
    if manifest_exists:
        prev = pd.read_csv(MANIFEST_CSV)
        done_ytids = set(prev.loc[prev["status"].isin(["ok", "already_exists"]), "ytid"])
        if args.only_failed:
            last_status = prev.groupby("ytid")["status"].last()
            failed_ytids = set(last_status[last_status == "failed"].index) - done_ytids

    tasks = []
    for _, row in meta.iterrows():
        if row["ytid"] in done_ytids:
            continue
        if failed_ytids is not None and row["ytid"] not in failed_ytids:
            continue
        tasks.append(
            (row["ytid"], row["start_s"], row["end_s"], args.save_path, args.cookies, args.sleep_min, args.sleep_max)
        )
        if args.limit and len(tasks) >= args.limit:
            break

    print(f"Total rows: {len(meta)} | Already done: {len(done_ytids)} | To attempt: {len(tasks)}")

    write_lock = threading.Lock()
    fieldnames = ["ytid", "start_s", "end_s", "filename", "status", "error"]
    mode = "a" if manifest_exists else "w"
    manifest_f = open(MANIFEST_CSV, mode, newline="", encoding="utf-8")
    writer = csv.DictWriter(manifest_f, fieldnames=fieldnames)
    if not manifest_exists:
        writer.writeheader()
    manifest_f.flush()

    if not tasks:
        print("Nothing to do.")
        manifest_f.close()
        return

    with mp.Pool(processes=args.workers) as pool:
        for ytid, start, end, filename, status, error in tqdm(
            pool.imap_unordered(_download_one, tasks), total=len(tasks)
        ):
            with write_lock:
                writer.writerow(
                    {
                        "ytid": ytid,
                        "start_s": start,
                        "end_s": end,
                        "filename": filename,
                        "status": status,
                        "error": error,
                    }
                )
                manifest_f.flush()

    manifest_f.close()


if __name__ == "__main__":
    main()
