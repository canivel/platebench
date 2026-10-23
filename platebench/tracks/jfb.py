"""January Food Benchmark (arXiv 2508.09966), CC BY 4.0.

1,000 phone photos from January app users who consented to research use. GPT-4o drafted each log, the user
corrected it and one human annotator corrected it again; not weighed. Totals and macros, no mass (grams are stored
as 0 and are not scored).

--source is the extracted food-scan-benchmark-dataset folder from the public S3 bucket
january-food-image-dataset-public (it holds food_scan_bench_v1.csv and fsb_images/).
"""
import csv

from platebench.tracks import upright_jpeg


def rows(source, images=True):
    with (source / 'food_scan_bench_v1.csv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            reference = {'calories': float(row['total_calories']), 'grams': 0.0, 'protein': float(row['total_protein']),
                         'carbs': float(row['total_carbs']), 'fat': float(row['total_fat'])}
            path = source / 'fsb_images' / row['image_filename']
            yield {'id': f"jfb-{row['image_id']}", 'group': f"jfb-{row['image_id']}",
                   'source': f"s3://january-food-image-dataset-public/food-scan-benchmark-dataset.tar.gz#fsb_images/{row['image_filename']}",
                   'reference': reference, 'image': lambda path=path: (upright_jpeg(path), 'jpg')}
