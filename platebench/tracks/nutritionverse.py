"""NutritionVerse-Real (Tai et al. 2023, arXiv 2401.08598).

Kaggle dataset nutritionverse/nutritionverse-real. iPhone photos of arranged dishes from random angles; every
ingredient weighed, nutrients from packaging or the Canadian Nutrient File. Labels are per dish, so the photos of one
dish share a reference and the dish is the resampling group. No license is stated: this repository publishes photo
ids only, never images or labels.

--source is the extracted Kaggle download (it holds nutritionverse_dish_metadata3.csv and nutritionverse-manual/).
"""
import csv
import re
from pathlib import Path

from platebench.tracks import upright_jpeg


def rows(source, images=True):
    root = source / 'nutritionverse-manual' / 'nutritionverse-manual'
    dishes = {}
    with (source / 'nutritionverse_dish_metadata3.csv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            dishes[row['dish_id']] = {'calories': float(row['total_calories']), 'grams': float(row['total_food_weight']),
                                      'protein': float(row['total_protein']), 'carbs': float(row['total_carbohydrates']),
                                      'fat': float(row['total_fats'])}
    with (root / 'updated-manual-dataset-splits.csv').open() as f:
        files = sorted(row['file_name'] for row in csv.DictReader(f))
    for name in files:
        dish = re.match(r'dish_(\d+)_', name).group(1)
        path = root / 'images' / name
        yield {'id': f'nv-{Path(name).stem.split(".rf.")[0]}', 'group': f'nv-dish-{dish}',
               'source': f'kaggle:nutritionverse/nutritionverse-real/{name}', 'reference': dishes[dish],
               'image': lambda path=path: (upright_jpeg(path), 'jpg')}
