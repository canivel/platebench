"""PlateBench scorer: kcal MAE with a 95% bootstrap interval, paired differences, relative metrics and macros.

References come from data/<track>/test.jsonl (rebuilt with `python -m platebench.tracks`) or, for the tracks whose
license allows it, from references/<track>.jsonl. Predictions are files in the format of predictions/<track>/*.jsonl.

Rules:
- Every prediction file must cover every photo of the track. A photo without a prediction ("kcal": null) counts as
  0 kcal and 0 g, so failures are never dropped.
- Interval: 2,000 bootstrap resamples, seed 0, 2.5th and 97.5th percentile of the resampled mean. NutritionVerse
  resamples dishes and SNAPMe resamples participant-days (their photos are not independent); other tracks resample
  photos.
- A paired difference is the mean of (|error of A| - |error of B|) over the same photos, with its own interval from
  the same resampling.
- An entry with several seeds (models.json) reports the mean of each metric over seeds; its interval and paired
  differences use the per-photo absolute error averaged over seeds.

  python -m platebench.score --track snapme --model "Plum 1" --against CalorieK --holdout only
  python -m platebench.score --track jfb --predictions my-model.jsonl --against CalorieK
  python -m platebench.score --all
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from platebench.tracks import DATA, REFERENCES, ROOT, TRACKS, track_ids

RESAMPLES = 2000
SEED = 0
MACROS = ('protein', 'carbs', 'fat')
PREDICTIONS = ROOT / 'predictions'
MODELS = json.loads((ROOT / 'models.json').read_text())


class Track:
    def __init__(self, name, rows, holdout=None):
        """rows: {id: {'group', 'reference'}}; holdout: None (all photos), 'only' or 'exclude'."""
        self.name = name
        ids = track_ids(name)
        if set(rows) != set(ids):
            raise SystemExit(f'{name}: references cover {len(rows)} photos, ids/{name}.txt has {len(ids)}')
        if holdout:
            from platebench.holdout import ids as holdout_ids
            held = holdout_ids()
            ids = [i for i in ids if (i in held) == (holdout == 'only')]
        self.ids = ids
        self.rows = rows
        cluster = TRACKS[name].cluster
        self.groups = [rows[i]['group'] if cluster else i for i in ids]
        self.files = {}

    def ref(self, key='calories'):
        return np.array([float(self.rows[i]['reference'][key]) for i in self.ids])

    def file(self, stem, root=PREDICTIONS):
        if stem not in self.files:
            path = stem if isinstance(stem, Path) else root / self.name / f'{stem}.jsonl'
            rows = {r['id']: r for r in map(json.loads, Path(path).read_text().splitlines()) if r}
            missing = [i for i in self.ids if i not in rows]
            if missing:
                raise SystemExit(f'{path}: no row for {len(missing)} photos of {self.name}, e.g. {missing[0]}')
            self.files[stem] = rows
        return self.files[stem]

    def predict(self, blend, key='kcal'):
        """Per-photo prediction of one seed: the weighted sum of the files' values (missing counts as 0)."""
        parts = {stem: self.file(stem) for stem in blend}
        return np.array([sum(w * float(parts[s][i].get(key) or 0.0) for s, w in blend.items()) for i in self.ids])


def load_track(name, data=DATA, holdout=None):
    path = data / name / 'test.jsonl'
    if path.exists():
        rows = {r['id']: r for r in map(json.loads, path.read_text().splitlines())}
    elif (REFERENCES / f'{name}.jsonl').exists():
        rows = {r['id']: r for r in map(json.loads, (REFERENCES / f'{name}.jsonl').read_text().splitlines())}
    else:
        raise SystemExit(f'No references for {name}: rebuild the track with `python -m platebench.tracks {name} ...`')
    return Track(name, rows, holdout)


def boot(values, groups, seed=SEED):
    """95% interval of the mean of values; whole groups are resampled."""
    rng = random.Random(seed)
    clusters = defaultdict(list)
    for v, g in zip(values, groups):
        clusters[g].append(v)
    sums = np.array([sum(c) for c in clusters.values()])
    sizes = np.array([len(c) for c in clusters.values()])
    n = len(sums)
    means = []
    for _ in range(RESAMPLES):
        pick = [rng.randrange(n) for _ in range(n)]
        means.append(sums[pick].sum() / sizes[pick].sum())
    means.sort()
    return [float(means[int(0.025 * RESAMPLES)]), float(means[int(0.975 * RESAMPLES) - 1])]


def metrics(pred, ref):
    err = pred - ref
    ae = np.abs(err)
    rel = ae / np.maximum(ref, 1.0)
    return {'mae': float(ae.mean()), 'median_ae': float(np.median(ae)), 'bias': float(err.mean()),
            'mae_pct_of_mean_ref': float(100 * ae.mean() / ref.mean()), 'median_rel_pct': float(100 * np.median(rel)),
            'within20_pct': float(100 * np.mean(rel <= 0.2)), 'within100kcal_pct': float(100 * np.mean(ae <= 100))}


def entry(name):
    if name not in MODELS['entries']:
        raise SystemExit(f'Unknown entry {name!r}; known: {", ".join(MODELS["entries"])}')
    return MODELS['entries'][name]


def seed_errors(track, seeds):
    ref = track.ref()
    preds = [track.predict(b) for b in seeds]
    return preds, ref, np.mean([np.abs(p - ref) for p in preds], axis=0)


def score(track, seeds, against=None):
    """Metrics of one entry (a list of seed blends) on a track; against: {name: seeds} for paired differences."""
    preds, ref, ae = seed_errors(track, seeds)
    per_seed = [metrics(p, ref) for p in preds]
    out = {k: float(np.mean([m[k] for m in per_seed])) for k in per_seed[0]}
    out['photos'] = len(ref)
    out['groups'] = len(set(track.groups))
    if len(per_seed) > 1:
        out['mae_seed_range'] = [min(m['mae'] for m in per_seed), max(m['mae'] for m in per_seed)]
    out['mae_ci95'] = boot(ae, track.groups)
    for name, other in (against or {}).items():
        _, _, other_ae = seed_errors(track, other)
        diff = ae - other_ae
        out[f'vs {name}'] = {'diff': float(diff.mean()), 'ci95': boot(diff, track.groups)}
    if len(seeds) == 1 and len(seeds[0]) == 1:
        (stem,) = seeds[0]
        rows = track.file(stem)
        if all(m in rows[i] for i in track.ids for m in MACROS):
            out['macro_mae_g'] = {m: float(np.mean(np.abs(track.predict(seeds[0], m) - track.ref(m)))) for m in MACROS}
    return out


def fmt(s, against=()):
    line = (f"{s['mae']:.1f} [{s['mae_ci95'][0]:.1f}, {s['mae_ci95'][1]:.1f}]  bias {s['bias']:+.0f}  "
            f"med rel {s['median_rel_pct']:.1f}%  within 20% {s['within20_pct']:.1f}%")
    for name in against:
        d = s[f'vs {name}']
        line += f"  vs {name} {d['diff']:+.1f} [{d['ci95'][0]:+.1f}, {d['ci95'][1]:+.1f}]"
    return line


def main():
    p = argparse.ArgumentParser(description='Score PlateBench predictions.')
    p.add_argument('--track', choices=tuple(TRACKS))
    p.add_argument('--model', action='append', default=[], help='entry name from models.json (repeatable)')
    p.add_argument('--predictions', type=Path, action='append', default=[], help='a prediction file (repeatable)')
    p.add_argument('--against', action='append', default=[], help='entry for paired differences (repeatable)')
    p.add_argument('--holdout', choices=('only', 'exclude'), default=None)
    p.add_argument('--data', type=Path, default=DATA)
    p.add_argument('--all', action='store_true', help='every entry on every track that has references')
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    against = {name: entry(name) for name in args.against}
    result = {}
    if args.all:
        for name in TRACKS:
            try:
                track = load_track(name, args.data, args.holdout)
            except SystemExit as error:
                print(error)
                continue
            result[name] = {e: score(track, entry(e), against) for e in MODELS['entries']}
    else:
        if not args.track:
            p.error('--track is required unless --all')
        track = load_track(args.track, args.data, args.holdout)
        todo = {name: entry(name) for name in args.model}
        todo.update({str(path): [{path: 1.0}] for path in args.predictions})
        if not todo:
            p.error('give --model or --predictions')
        result[args.track] = {name: score(track, seeds, against) for name, seeds in todo.items()}
    if args.json:
        print(json.dumps(result, indent=1))
        return
    for name, scores in result.items():
        print(f'## {name}' + (f' (holdout {args.holdout})' if args.holdout else ''))
        for model, s in sorted(scores.items(), key=lambda kv: kv[1]['mae']):
            print(f'{model:40s} {fmt(s, against)}')
        print()


if __name__ == '__main__':
    main()
