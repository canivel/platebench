"""The app's model contract: image preprocessing, prompt, retry prompt, output grammar and parser.

Every model is given the same JPEG bytes: the stored photo, converted to RGB, resized to 1024 px wide (height follows
the aspect ratio; small photos are enlarged) with bilinear filtering, saved as JPEG quality 90. A generative model gets
PROMPT with that JPEG (text first, then the image), the output grammar, a 1,536-token limit and temperature 0.1 on
llama.cpp. If the answer does not parse, it gets one more attempt with RETRY_PROMPT, which asks for a single
whole-meal item. A photo a model fails to answer counts as a 0 kcal prediction when scored.

Output version: nutrition-json-v2.
"""
import io
import json
import math
import re
from pathlib import Path

BASE_PROMPT = ('Estimate the foods and nutrition in this meal photo. Return only JSON: '
               '{"items":[{"name":"food name","grams":100,"calories":150,"protein":10,"carbs":20,"fat":3}]}. '
               'Use one item per visible food component. Values are for the estimated served portion, not per 100 grams. '
               'Do not include reasoning. /no_think')
PROMPT = (f'{BASE_PROMPT} Start with the largest visible foods, especially the main protein and starch. Do not list '
          'guessed seasonings or hidden ingredients. Keep names short. Return at most 8 items. Combine small toppings '
          'with their main food.')
RETRY_PROMPT = (f'{BASE_PROMPT} Return just ONE item for the entire meal, including all foods in its estimated weight '
                'and nutrition. Keep the name short.')
OUTPUT_VERSION = 'nutrition-json-v2'
OUTPUT_TOKENS = 1536
TEMPERATURE = 0.1
APP_WIDTH = 1024
APP_JPEG_QUALITY = 90
KEYS = ('grams', 'calories', 'protein', 'carbs', 'fat')

# GBNF grammar, exactly as the app passes it to llama.cpp (also in grammar.gbnf).
GRAMMAR = (Path(__file__).with_name('grammar.gbnf')).read_text(encoding='utf-8')

# Python equivalent of GRAMMAR, to check that an answer fits it.
_WS = r'[ \t\n\r]{0,4}'
_NUMBER = r'(?:0|[1-9][0-9]{0,4})(?:\.[0-9]{1,2})?'
_ITEM = ('\\{' + _WS + '"name"' + _WS + ':' + _WS + r'"[^"\\\x00-\x1f]{1,64}"'
         + ''.join(_WS + ',' + _WS + f'"{key}"' + _WS + ':' + _WS + _NUMBER for key in KEYS) + _WS + '\\}')
GRAMMAR_RE = re.compile('\\{' + _WS + '"items"' + _WS + ':' + _WS + '\\[' + _WS + _ITEM
                        + '(?:' + _WS + ',' + _WS + _ITEM + '){0,7}' + _WS + '\\]' + _WS + '\\}')


def app_jpeg(image):
    """The JPEG bytes the app hands to the model. image is a PIL image (any mode)."""
    from PIL import Image
    image = image.convert('RGB')
    image = image.resize((APP_WIDTH, round(image.height * APP_WIDTH / image.width)), Image.Resampling.BILINEAR)
    buffer = io.BytesIO()
    image.save(buffer, 'JPEG', quality=APP_JPEG_QUALITY)
    return buffer.getvalue()


def _number(obj, *names):
    for name in names:
        if name in obj:
            value = float(obj[name])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid {name}')
            return value
    raise ValueError(f'Missing {names[0]}')


def parse_items(raw):
    """Parse a model answer the way the app does. Returns a list of items; raises ValueError if it does not parse."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(raw):
        if char not in '{[':
            continue
        try:
            obj, _ = decoder.raw_decode(raw[index:])
            rows = obj.get('items', obj.get('ingredients', obj.get('foods', [obj]))) if isinstance(obj, dict) else obj
            if not isinstance(rows, list) or not rows:
                continue
            return [{'name': str(row.get('name', row.get('food', row.get('ingredient', 'Food')))),
                     'grams': _number(row, 'grams', 'portion_g', 'portion_grams', 'weight_g', 'mass_g'),
                     'calories': _number(row, 'calories', 'calories_kcal', 'kcal'),
                     'protein': _number(row, 'protein', 'protein_g'),
                     'carbs': _number(row, 'carbs', 'carbs_g', 'carbohydrate_g', 'carbohydrates'),
                     'fat': _number(row, 'fat', 'fat_g')} for row in rows]
        except (ValueError, TypeError, AttributeError, KeyError) as error:
            # A complete first item inside truncated outer JSON is not a meal.
            raise ValueError('Incomplete or invalid nutrition JSON') from error
    raise ValueError('No complete nutrition JSON')


def totals(items):
    """Plate totals of a parsed item list, in the prediction-file format."""
    return {'kcal': sum(i['calories'] for i in items), 'protein': sum(i['protein'] for i in items),
            'carbs': sum(i['carbs'] for i in items), 'fat': sum(i['fat'] for i in items),
            'grams': sum(i['grams'] for i in items)}
