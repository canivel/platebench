"""SNAPMe (Larke et al. 2023, Nutrients 15:4972), USDA Ag Data Commons doi:10.15482/USDA.ADC/1528346, CC BY-SA 4.0.

"Before" photos of home meals taken by 95 adults with the Bitesnap app. The reference of a photo is the sum of the
ASA24 food-record lines linked to it (self-reported, not weighed). The resampling group is the participant-day.

--source is the extracted snapme_db_09Dec2022 folder (it holds snapme_cs_db/).
"""
from collections import defaultdict
import csv

from platebench.tracks import KEYS, upright_jpeg


def rows(source, images=True):
    db = source / 'snapme_cs_db'
    lines = defaultdict(list)
    with (db / 'master_SNAPME_linkfile.csv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            lines[row['filename']].append(row)
    num = lambda row, key: float(row[key]) if row[key] not in ('', 'NA') else 0.0
    columns = {'grams': 'FoodAmt', 'calories': 'KCAL', 'protein': 'PROT', 'carbs': 'CARB', 'fat': 'TFAT'}
    for photo in sorted((db / 'before_photos').iterdir()):
        entries = lines.get(photo.name)
        if not entries:
            continue
        items = [{key: num(row, column) for key, column in columns.items()} for row in entries]
        reference = {key: sum(item[key] for item in items) for key in KEYS}
        yield {'id': f'snapme-{photo.stem}', 'group': f"snapme-{entries[0]['subject_id']}-day{entries[0]['snapme_study_day']}",
               'source': f'doi:10.15482/USDA.ADC/1528346 snapme_cs_db/before_photos/{photo.name}', 'reference': reference,
               'image': lambda photo=photo: (upright_jpeg(photo), 'jpg')}
