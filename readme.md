## Music Caps Downloader

Unofficial download repository for [MusicCaps](https://www.kaggle.com/datasets/googleai/musiccaps)

`The MusicCaps dataset contains 5,521 music examples, each of which is labeled with an English aspect list and a free text caption written by musicians.`

### Current Status
- ( 5161 / 5521 ) downloaded, 360 permanently unavailable (removed/private/terminated/copyright)

### Quick Start

```
conda create -n YOUR_ENV_NAME python=3.9
conda activate YOUR_ENV_NAME
pip install -r requirements.txt
python download_audio.py
```

Audio is saved to `metadata/wav/` as `[ytid]-[start-end].wav`. The script is resumable — rerunning it skips clips that were already downloaded.

Outputs:
- `metadata/wav/` — downloaded 10s audio clips
- `metadata/download_manifest.csv` — per-clip status (`ok` / `failed` / `already_exists`) with error messages
- `metadata/musiccaps-downloaded.csv` — the original MusicCaps metadata (caption, aspect list, tags, etc.) joined with the local `file_path` for every successfully downloaded clip
- `metadata/download_failures.csv` — the clips that could not be downloaded, with categorized reasons

To build/refresh the last two files from an existing manifest:

```
python -c "
import pandas as pd
meta = pd.read_csv('metadata/musiccaps-public.csv')
manifest = pd.read_csv('metadata/download_manifest.csv')
last = manifest.groupby('ytid').last().reset_index()
ok = last[last['status'].isin(['ok','already_exists'])].copy()
ok['file_path'] = 'metadata/wav/' + ok['filename']
meta.merge(ok[['ytid','filename','file_path']], on='ytid').to_csv('metadata/musiccaps-downloaded.csv', index=False)
"
```

### Options

```
python download_audio.py --workers 12                # parallel downloads
python download_audio.py --only-failed               # retry only rows marked "failed" in the manifest
python download_audio.py --sleep-min 1 --sleep-max 3  # random delay between requests (helps avoid rate limiting)
python download_audio.py --cookies cookies.txt        # authenticate as a logged-in YouTube account
python download_audio.py --limit 20                   # only attempt the first N rows (useful for testing)
```

### Known YouTube-side issues (as of 2026)

YouTube has become considerably stricter about automated access since this dataset was first published. Two issues you're likely to hit:

1. **"Sign in to confirm you're not a bot"** — an IP-level rate limit that kicks in after a burst of requests. `download_audio.py` works around this by forcing the `android` player client (`extractor_args: {"youtube": {"player_client": ["android"]}}`), which is not subject to the same signature/bot checks as the default web client. If you still hit it, retry with `--only-failed --workers 4 --sleep-min 1 --sleep-max 2.5` to slow down.
2. **Missing JS signature solver** (`Signature solving failed` / `The page needs to be reloaded`) — recent YouTube changes require executing JavaScript to deobfuscate stream URLs, which `yt-dlp` needs a JS runtime (Node/Deno) for. The `android` client workaround above sidesteps this for most videos; a small number of age-restricted videos may still require `--cookies` plus a JS runtime installed.

Remaining categories of permanent failures you cannot retry your way out of: age-restricted videos needing sign-in, private videos, terminated accounts, and copyright takedowns — these clips are gone from YouTube regardless of method.

### issue

```
# invalid start time
WARNING: [youtube] Invalid start time (53886.0 < 0) for chapter "26-08-09 Melding : 13-119 A1 AMSTERDAM BOLSTOEN -- RIT:175"
WARNING: [youtube] Invalid start time (380.0 < 0) for chapter "Genre:"
WARNING: [youtube] Invalid start time (380.0 < 0) for chapter "Duur"                                        
...

# issue: Private video & unavailable & terminated
ERROR: [youtube] 0J_2K1Gvruk: Private video. Sign in if you've been granted access to this video
ERROR: [youtube] 63rqIYPHvlc: Private video. Sign in if you've been granted access to this video
ERROR: [youtube] Ah_aYOGnQ_I: Private video. Sign in if you've been granted access to this video
...
ERROR: [youtube] Akg1n9IWSrw: Video unavailable. This video is no longer available because the YouTube account associated with this video has been terminated.
ERROR: [youtube] B7iRvj8y9aU: Video unavailable. This video is no longer available because the YouTube account associated with this video has been terminated.
ERROR: [youtube] NIcsJ8sEd0M: Video unavailable. This video is no longer available because the YouTube account associated with this video has been terminated.
...

# issue: country(KR)
ERROR: [youtube] KMQmM12G9Z4: Video unavailable. This video contains content from WMG, who has blocked it in your country on copyright grounds
```

### Reference
- https://www.kaggle.com/datasets/googleai/musiccaps
- https://github.com/SangwonSUH/audioset-downloader
- https://github.com/keunwoochoi/audioset-downloader
