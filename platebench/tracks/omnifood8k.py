"""OmniFood8K (Yu et al., CVPR 2026, arXiv 2604.12356), released through the project page
yudongjian.github.io/OmniFood8K-food.

Chinese dishes on a white table, ingredients weighed, nutrients from the China food composition tables. The track is
the official test split (test_new333.txt). Each scene has six 640x480 camera views; one is used, chosen by
SHA-256 of the scene id modulo 6, so every view is represented. Energy is given in kJ and converted at 4.184 kJ per
kcal. Label lines are "scene grams kJ protein fat carbs". The download has no license file: this repository
publishes photo ids only, never images or labels.

--source is the extracted release folder (it holds test_new333.txt and 8036/<scene>/camera_<k>.jpg).
"""
import hashlib

from platebench.tracks import upright_jpeg


def rows(source, images=True):
    for line in (source / 'test_new333.txt').read_text().splitlines():
        if not line.strip():
            continue
        scene, grams, kj, protein, fat, carbs = line.split()[:6]
        view = int(hashlib.sha256(scene.encode()).hexdigest(), 16) % 6
        reference = {'calories': float(kj) / 4.184, 'grams': float(grams), 'protein': float(protein), 'carbs': float(carbs),
                     'fat': float(fat)}
        path = source / '8036' / scene / f'camera_{view}.jpg'
        yield {'id': f'omni-{scene}-cam{view}', 'group': f'omni-{scene}', 'source': f'omnifood8k:8036/{scene}/camera_{view}.jpg',
               'reference': reference, 'image': lambda path=path: (upright_jpeg(path), 'jpg')}
