"""The holdout slice of SNAPMe and JFB, frozen on 19 October 2026 (ids/holdout-2026-10-19.txt).

Rule: per track, split the photos into quartiles of reference kcal (numpy linear percentiles over the whole track;
a photo on an edge goes to the lower quartile). Within each quartile, sort the photos by the SHA-256 hex digest of
the photo id (UTF-8) and take the first round(0.2 x quartile size). Deterministic, no seed. The result is 296
SNAPMe photos (177 participant-days) and 200 JFB photos.

The slice has been read once, for the paper's holdout table. It is spent: it no longer tells you anything about a
model chosen after reading it.

  python -m platebench.holdout          # rebuild the slice from data/ (or references/) and compare with the file
"""
import hashlib
import json

import numpy as np

from platebench.tracks import IDS

FILE = IDS / 'holdout-2026-10-19.txt'
TRACKS = ('snapme', 'jfb')
FRACTION = 0.2


def read_file(path=FILE):
    return sorted(tuple(line.split()) for line in path.read_text().splitlines() if line.strip() and not line.startswith('#'))


def ids():
    return {i for _, i in read_file()}


def build(references):
    """references: {track: [(photo id, reference kcal), ...]} for snapme and jfb, in any order."""
    out = []
    for track in TRACKS:
        rows = references[track]
        edges = np.percentile([kcal for _, kcal in rows], [25, 50, 75])
        quartile = [int(np.searchsorted(edges, kcal, side='left')) for _, kcal in rows]
        for q in range(4):
            members = sorted((hashlib.sha256(i.encode('utf-8')).hexdigest(), i) for (i, _), k in zip(rows, quartile) if k == q)
            out += [(track, i) for _, i in members[:round(FRACTION * len(members))]]
    return sorted(out)


def main():
    from platebench.score import load_track
    references = {}
    for track in TRACKS:
        t = load_track(track)
        references[track] = list(zip(t.ids, t.ref('calories')))
    pairs = build(references)
    ok = pairs == read_file()
    counts = {t: sum(1 for tt, _ in pairs if tt == t) for t in TRACKS}
    print(json.dumps({'file': FILE.name, 'counts': counts, 'matches_file': ok}))
    if not ok:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
