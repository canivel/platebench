"""DiningBench nutrition subset (Meituan, ACL 2026, arXiv 2604.10425), Hugging Face meituan/DiningBench.

License CC BY-NC-ND 4.0: research use, no derivatives. This repository publishes photo ids and model predictions
only. The reference labels and images stay with the original release; this script reads them from your own copy.

merchant  One merchant photo per dish (1,650 dishes). Reference: merchant-supplied nutrition or a Gemini-3-Pro
          estimate checked against USDA FoodData Central. Totals only, no mass.
customer  The same dishes, the first customer photo (sorted by file name) of each dish that has one.

--source is a folder with nutrition_en.jsonl and the images.tar.gz archive extracted into extract/.
"""
import json
from pathlib import Path

from platebench.tracks import upright_jpeg


def _rows(source, customer):
    for line in (source / 'nutrition_en.jsonl').read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        truth = row['ground_truth']
        if customer:
            if not row['user_images']:
                continue
            image = sorted(row['user_images'])[0]
        else:
            image = row['standard_image']
        reference = {'calories': float(truth['calories']), 'grams': 0.0, 'protein': float(truth['protein']),
                     'carbs': float(truth['carbohydrates']), 'fat': float(truth['fat'])}
        path = source / 'extract' / image
        yield {'id': f'db-{Path(image).stem}', 'group': f"db-{row['id']}", 'source': f'hf:meituan/DiningBench/images.tar.gz#{image}',
               'reference': reference, 'image': lambda path=path: (upright_jpeg(path), 'jpg')}


def merchant(source, images=True):
    return _rows(source, customer=False)


def customer(source, images=True):
    return _rows(source, customer=True)
