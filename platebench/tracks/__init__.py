"""PlateBench tracks: registry, shared row writer and the rebuild command.

Each public track is rebuilt from its original source into data/<track>/ (git-ignored):

  data/<track>/test.jsonl    one row per photo: id, group, image, sha256, source, reference
  data/<track>/images/       the photos, stored upright as the phone passes them to the app

Rebuild one track:

  python -m platebench.tracks snapme --source /path/to/snapme_db_09Dec2022
  python -m platebench.tracks overhead --no-images      # references only, no photo download

The rebuilt photo ids must equal ids/<track>.txt in the same order, and where this repository carries
references (references/<track>.jsonl) the rebuilt references must match them; the command fails otherwise.
"""
import argparse
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
IDS = ROOT / 'ids'
REFERENCES = ROOT / 'references'
KEYS = ('calories', 'grams', 'protein', 'carbs', 'fat')


@dataclass(frozen=True)
class Track:
    name: str
    title: str
    photos: int
    license: str
    cluster: bool  # several photos share a reference group; intervals resample groups
    no_grams: bool  # the source has no mass


TRACKS = {t.name: t for t in (
    Track('overhead', 'Nutrition5k overhead (official test split)', 507, 'CC BY 4.0', False, False),
    Track('angled', 'Nutrition5k angled (one side-camera frame per test dish)', 675, 'CC BY 4.0', False, False),
    Track('nutritionverse', 'NutritionVerse-Real', 889, 'not stated', True, False),
    Track('snapme', 'SNAPMe', 1474, 'CC BY-SA 4.0', True, False),
    Track('jfb', 'January Food Benchmark', 1000, 'CC BY 4.0', False, True),
    Track('diningbench', 'DiningBench nutrition, merchant photos', 1650, 'CC BY-NC-ND 4.0', False, True),
    Track('diningbench-customer', 'DiningBench nutrition, first customer photo', 1458, 'CC BY-NC-ND 4.0', False, True),
    Track('omnifood8k', 'OmniFood8K (official test split)', 2368, 'none in download', False, False),
)}


def track_ids(track):
    return (IDS / f'{track}.txt').read_text().split()


def upright_jpeg(path):
    """The photo upright (EXIF orientation applied), RGB, JPEG quality 95."""
    from PIL import Image, ImageOps
    from pillow_heif import register_heif_opener
    register_heif_opener()  # some SNAPMe photos are iPhone HEIC files named .jpeg
    with Image.open(path) as image:
        upright = ImageOps.exif_transpose(image).convert('RGB')
        buffer = io.BytesIO()
        upright.save(buffer, 'JPEG', quality=95)
        return buffer.getvalue()


def write_track(track, rows, output, images=True):
    """rows yields dicts with id, group, source, reference, and image() returning bytes plus ext, or None.

    Rows with a zero-calorie reference are dropped (water, black coffee), except on the overhead track, which keeps
    its one 0 kcal test dish ("plate only") as the paper scored it. Returns a summary dict."""
    output.mkdir(parents=True, exist_ok=True)
    if images:
        (output / 'images').mkdir(exist_ok=True)
    kept, dropped = [], []
    for row in rows:
        if row['reference']['calories'] <= 0 and track != 'overhead':
            dropped.append(row['id'])
            continue
        out = {'id': row['id'], 'group': row['group'], 'source': row['source'],
               'reference': {k: float(row['reference'][k]) for k in KEYS}}
        if images:
            data, ext = row['image']()
            name = f"images/{row['id'].replace('@', '_')}.{ext}"
            (output / name).write_bytes(data)
            out.update(image=name, sha256=hashlib.sha256(data).hexdigest())
        kept.append(out)
    (output / 'test.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in kept))
    return check(track, kept) | {'dropped_zero_kcal': len(dropped)}


def check(track, rows):
    ids = [r['id'] for r in rows]
    expected = track_ids(track)
    if ids != expected:
        missing, extra = set(expected) - set(ids), set(ids) - set(expected)
        raise SystemExit(f'{track}: rebuilt ids differ from ids/{track}.txt ({len(missing)} missing, {len(extra)} extra'
                         + ('; same set, different order' if not missing and not extra else '')
                         + f'), missing e.g. {sorted(missing)[:3]}, extra e.g. {sorted(extra)[:3]}')
    ref_file = REFERENCES / f'{track}.jsonl'
    if ref_file.exists():
        published = {r['id']: r['reference'] for r in map(json.loads, ref_file.read_text().splitlines())}
        bad = [r['id'] for r in rows if any(abs(r['reference'][k] - v) > 1e-6 for k, v in published[r['id']].items())]
        if bad:
            raise SystemExit(f'{track}: {len(bad)} rebuilt references differ from references/{track}.jsonl, e.g. {bad[0]}')
    return {'track': track, 'photos': len(rows), 'groups': len({r['group'] for r in rows}), 'ids_match': True,
            'references_checked': ref_file.exists()}


def builders():
    from platebench.tracks import diningbench, jfb, nutrition5k, nutritionverse, omnifood8k, snapme
    return {'overhead': nutrition5k.overhead, 'angled': nutrition5k.angled, 'nutritionverse': nutritionverse.rows,
            'snapme': snapme.rows, 'jfb': jfb.rows, 'diningbench': diningbench.merchant,
            'diningbench-customer': diningbench.customer, 'omnifood8k': omnifood8k.rows}


def main():
    p = argparse.ArgumentParser(description='Rebuild one PlateBench track from its original source.')
    p.add_argument('track', choices=tuple(TRACKS))
    p.add_argument('--source', type=Path, help='local copy of the original dataset (see README); overhead downloads its own')
    p.add_argument('--output', type=Path, help='default: data/<track>')
    p.add_argument('--no-images', action='store_true', help='write references only (enough to score stored predictions)')
    args = p.parse_args()
    if args.track != 'overhead' and args.source is None:
        p.error('--source is required for this track')
    output = args.output or DATA / args.track
    rows = builders()[args.track](args.source, images=not args.no_images)
    print(json.dumps(write_track(args.track, rows, output, images=not args.no_images)))


if __name__ == '__main__':
    main()
