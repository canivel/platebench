"""Nutrition5k tracks (Thames et al., CVPR 2021, CC BY 4.0).

overhead  The official test split (rgb_test_ids.txt), the RealSense overhead RGB image of each test dish that has one,
          with the totals from the released dish metadata CSVs (cafe1 and cafe2). Downloaded from the public
          Google Cloud bucket; --source is not needed. Images are kept as the original PNG.
angled    One side-camera video frame per official test dish, from calorie-lens-data (shalev396/calorie-lens-data on
          Hugging Face, revision below, CC BY 4.0), which repackages Nutrition5k with corrected ingredient labels and
          frames from the four side-angle videos. The camera and frame are chosen by a SHA-256 hash of the dish id, so
          the choice is deterministic. --source is a local copy of that dataset revision (dishes.parquet,
          items.parquet, side/*.parquet).
"""
import csv
import hashlib
import io
import urllib.error
import urllib.request
from collections import defaultdict

BASE = 'https://storage.googleapis.com/nutrition5k_dataset/nutrition5k_dataset/'
FIELDS = ('calories', 'grams', 'fat', 'carbs', 'protein')  # CSV order after the dish id
LENS_REVISION = 'ed6c9cef52238fec71a70c51d7d9043814a78d8a'
LENS_SOURCE = f'https://huggingface.co/datasets/shalev396/calorie-lens-data/tree/{LENS_REVISION}'
LENS_REFERENCE = {'kcal': 'calories', 'mass': 'grams', 'fat': 'fat', 'carb': 'carbs', 'protein': 'protein'}


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def exists(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=60):
            return True
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise


def official_test_ids():
    return sorted(set(fetch(BASE + 'dish_ids/splits/rgb_test_ids.txt').decode().split()))


def overhead(source=None, images=True):
    metadata = {}
    for cafe in ('cafe1', 'cafe2'):
        for row in csv.reader(io.StringIO(fetch(BASE + f'metadata/dish_metadata_{cafe}.csv').decode())):
            if row and row[0].startswith('dish_'):
                metadata[row[0]] = dict(zip(FIELDS, map(float, row[1:6])))
    for dish in official_test_ids():
        if dish not in metadata:
            continue
        url = BASE + f'imagery/realsense_overhead/{dish}/rgb.png'
        if not exists(url):  # some test dishes have no overhead RGB image
            continue
        yield {'id': dish, 'group': dish, 'source': url, 'reference': metadata[dish],
               'image': lambda url=url: (fetch(url), 'png')}


def pick(key, count, options):
    """Deterministic sample of count options, by SHA-256 of key:option."""
    return sorted(options, key=lambda option: hashlib.sha256(f'{key}:{option}'.encode()).hexdigest())[:count]


def angled(source, images=True):
    import pandas as pd
    import pyarrow.parquet as pq
    test_ids = set(official_test_ids())
    dishes = pd.read_parquet(source / 'dishes.parquet').set_index('dish_id')
    named = defaultdict(list)
    for row in pd.read_parquet(source / 'items.parquet').itertuples():
        named[row.dish_id].append(str(row.name).strip())
    labels = {}
    for dish, info in dishes.iterrows():
        if info['split'] != 'test':
            continue
        if dish not in test_ids:
            raise ValueError(f'{dish}: calorie-lens test dish is not on the official Nutrition5k test list')
        if not named[dish] or not all(named[dish]):  # no named ingredients
            continue
        if info['kcal'] <= 0:
            continue
        labels[dish] = {app: float(info[column]) for column, app in LENS_REFERENCE.items()}
    shards = sorted((source / 'side').glob('*.parquet'))
    frames = defaultdict(lambda: defaultdict(list))
    for shard in shards:
        for record in pq.read_table(shard, columns=['dish_id', 'camera', 'frame']).to_pylist():
            if record['dish_id'] in labels:
                frames[record['dish_id']][record['camera']].append(record['frame'])
    wanted = {}
    for dish, cameras in frames.items():
        camera = pick(dish, 1, cameras)[0]
        frame = pick(f'{dish}:{camera}', 1, cameras[camera])[0]
        wanted[(dish, camera, frame)] = None
    columns = ['dish_id', 'camera', 'frame'] + (['image'] if images else [])
    rows = []
    for shard in shards:
        for record in pq.read_table(shard, columns=columns).to_pylist():
            key = (record['dish_id'], record['camera'], record['frame'])
            if key in wanted:
                data = record['image']['bytes'] if images else None
                rows.append({'id': f'{key[0]}@side-{key[1]}{key[2]}', 'group': key[0],
                             'source': f'{LENS_SOURCE}/{shard.relative_to(source).as_posix()}', 'reference': labels[key[0]],
                             'image': lambda data=data: (data, 'jpg')})
    yield from sorted(rows, key=lambda row: row['id'])
