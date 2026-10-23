<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img alt="PlateBench" src="assets/logo-light.svg" width="400">
  </picture>
</p>

<p align="center">
  <b>Calorie estimation from one meal photo, scored the way a phone app calls the model.</b>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache%202.0-blue.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB.svg?logo=python&amp;logoColor=white">
  <img alt="8 public tracks" src="https://img.shields.io/badge/tracks-8%20public-E8743B.svg">
  <img alt="arXiv: coming soon" src="https://img.shields.io/badge/arXiv-coming%20soon-B31B1B.svg?logo=arxiv&amp;logoColor=white">
  <a href="https://huggingface.co/canivel/grape-1-94m-onnx"><img alt="Grape 1 on Hugging Face" src="https://img.shields.io/badge/%F0%9F%A4%97%20Grape%201-94M%20ONNX-FFD21E.svg"></a>
  <a href="https://huggingface.co/canivel/plum-1-0.8b-gguf"><img alt="Plum 1 on Hugging Face" src="https://img.shields.io/badge/%F0%9F%A4%97%20Plum%201-0.8B%20GGUF-FFD21E.svg"></a>
</p>

PlateBench is an evaluation of calorie estimation from a single meal photo, set up the way a phone app calls the
model. It has eight public tracks from six datasets. Every model gets the same JPEG bytes, and generative models get
the same prompt, output grammar, retry rule and token limit. The headline metric is kcal mean absolute error (MAE)
with a 95% bootstrap interval, and models are compared by paired differences on the same photos.

## Quick start

```
git clone https://github.com/canivel/platebench && cd platebench
pip install -r requirements.txt
python -m platebench.tracks jfb --source /path/to/food-scan-benchmark-dataset --no-images
python -m platebench.score --track jfb --model "Plum 1" --model "Grape 1" --against CalorieK
```

The last command scores the stored predictions; no GPU and no model download needed.

## Leaderboard

kcal MAE on the full public tracks, lower is better (PC scores on public photos, not phone accuracy). Bold is the
best row per track. Models run with the app contract in `platebench/harness/`.

| Model | Size | Overhead | Angled | NutritionVerse | SNAPMe | JFB | DiningBench | DB customer | OmniFood8K |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Plum 1** (Grape 1 + 0.8B decision model) | 1.2 GB | **45.3** | **43.9** | 490.3 | **131.2** | **131.6** | **219.0** | **231.0** | 173.0 |
| Grape 1 recipe (G5, mean of 2 seeds) | 188 MB | 50.1 | 48.7 | 525.5 | 136.6 | 143.9 | 232.0 | 239.6 | 167.9 |
| J5 (0.8B, 26-option readout) | 1.0 GB | 49.8 | 47.4 | 462.3 | 133.7 | 135.2 | 227.2 | 243.4 | 189.7 |
| Qwen3.8-27B, zero-shot | server | 92.7 | 102.7 | **427.7** | 135.8 | 132.2 | 226.0 | 236.5 | **143.0** |
| CalorieK | SigLIP2-base regressor | 104.9 | 57.2 | 657.2 | 158.0 | 178.5 | 312.7 | 320.3 | 228.1 |
| Boba | 0.8B VLM | 108.5 | 83.3 | 680.7 | 197.5 | 241.4 | 472.2 | 458.1 | 259.7 |

SNAPMe and JFB here include the holdout photos. The paper's headline numbers are on the once-read holdout slice:
Plum 1 has 126.0 kcal MAE on SNAPMe and 133.4 on JFB, against 154.5 and 170.1 for CalorieK. Every row above can be
recomputed with `python -m platebench.paper`.

## What is in this repository

This repository holds what you need to rebuild the tracks, run a model with the app's contract, score it, and
check the numbers in the paper:

- scripts that rebuild each public track from its original source (`platebench/tracks/`)
- the photo-id list of every track and of the holdout slice (`ids/`)
- the image preprocessing, prompt, output grammar and answer parser (`platebench/harness/`)
- the scorer, with its bootstrap and paired-difference code (`platebench/score.py`)
- per-photo predictions of the models in the paper's holdout and all-tracks tables (`predictions/`)
- reference labels for the tracks whose license allows it (`references/`)

Benchmark images are not in this repository, and neither are reference labels for NutritionVerse, DiningBench or
OmniFood8K. You rebuild those from your own copy of each dataset.

Paper: "Distributional Readouts Make Small Vision-Language Models Better Calorie Estimators", Danilo Canivel,
Nomm.ai. arXiv link coming with the announcement. Models: [Grape 1](https://huggingface.co/canivel/grape-1-94m-onnx)
and [Plum 1](https://huggingface.co/canivel/plum-1-0.8b-gguf) (OpenRAIL-M).

## Tracks

| Track | Photos | Photos and reference | License | In this repo |
| --- | ---: | --- | --- | --- |
| `overhead` | 507 | Nutrition5k official test split, overhead camera; weighed | CC BY 4.0 | ids, references |
| `angled` | 675 | One side-camera video frame per test dish (calorie-lens-data); same labels | CC BY 4.0 | ids, references |
| `nutritionverse` | 889 | NutritionVerse-Real iPhone photos, about 4 per dish (225 dishes); weighed | not stated | ids |
| `snapme` | 1,474 | SNAPMe home meals of 95 adults; self-reported ASA24 records (275 participant-days) | CC BY-SA 4.0 | ids, references |
| `jfb` | 1,000 | January Food Benchmark app photos; GPT-4o draft corrected by user and annotator | CC BY 4.0 | ids, references |
| `diningbench` | 1,650 | DiningBench merchant photos of restaurant dishes; merchant or Gemini-3-Pro label | CC BY-NC-ND 4.0 | ids |
| `diningbench-customer` | 1,458 | First customer photo of the same DiningBench dishes | CC BY-NC-ND 4.0 | ids |
| `omnifood8k` | 2,368 | OmniFood8K official test split, one of six 640x480 views; weighed | none in download | ids |

Only NutritionVerse, OmniFood8K and Nutrition5k are weighed. SNAPMe and JFB measure agreement with what people
recorded or corrected. The overhead track keeps one test dish whose reference is 0 kcal ("plate only"), as the
paper scored it; the other tracks drop photos with a 0 kcal reference.

`ids/<track>.txt` lists the photo ids in the order the scorer uses. The order matters for the bootstrap: with the
same order and seed, intervals are reproduced exactly.

## Setup

Python 3.10 or newer.

```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

Scoring stored predictions needs only numpy. Rebuilding tracks with images needs Pillow and pillow-heif; the angled
track also needs pandas and pyarrow. Run every command from the repository root.

## Rebuild the tracks

Download each dataset from its original source, then rebuild it into `data/<track>/` (ignored by Git):

```
python -m platebench.tracks overhead                    # downloads from the public Nutrition5k bucket
python -m platebench.tracks angled --source /path/to/calorie-lens-data
python -m platebench.tracks nutritionverse --source /path/to/nutritionverse-real
python -m platebench.tracks snapme --source /path/to/snapme_db_09Dec2022
python -m platebench.tracks jfb --source /path/to/food-scan-benchmark-dataset
python -m platebench.tracks diningbench --source /path/to/DiningBench
python -m platebench.tracks diningbench-customer --source /path/to/DiningBench
python -m platebench.tracks omnifood8k --source /path/to/OmniFood8K
```

| Track | Source | What `--source` points to |
| --- | --- | --- |
| overhead | Nutrition5k, `gs://nutrition5k_dataset` (public HTTPS) | not needed |
| angled | Hugging Face `shalev396/calorie-lens-data`, revision `ed6c9cef52238fec71a70c51d7d9043814a78d8a` | folder with `dishes.parquet`, `items.parquet`, `side/` |
| nutritionverse | Kaggle `nutritionverse/nutritionverse-real` | extracted download (`nutritionverse_dish_metadata3.csv`, `nutritionverse-manual/`) |
| snapme | USDA Ag Data Commons, doi:10.15482/USDA.ADC/1528346 | extracted `snapme_db_09Dec2022` |
| jfb | S3 bucket `january-food-image-dataset-public`, `food-scan-benchmark-dataset.tar.gz` | extracted `food-scan-benchmark-dataset` |
| diningbench | Hugging Face `meituan/DiningBench` | folder with `nutrition_en.jsonl` and `images.tar.gz` extracted into `extract/` |
| omnifood8k | OmniFood8K release linked from the project page | extracted folder with `test_new333.txt` and `8036/` |

Each photo is stored upright (EXIF orientation applied) as a JPEG at quality 95; Nutrition5k overhead images stay
the original PNG. The command fails if the rebuilt ids differ from `ids/<track>.txt`, or if rebuilt references differ
from `references/<track>.jsonl`. Add `--no-images` to write references only, which is enough to score stored
predictions.

## Run a model

`platebench/harness/contract.py` is the app contract: resize to 1024 px wide with bilinear filtering and save as
JPEG quality 90; send the prompt text, then the image; constrain the answer with `grammar.gbnf`; allow 1,536 output
tokens; on a parse failure, retry once with the whole-meal prompt. `platebench/harness/run.py` runs a model served
behind an OpenAI-compatible endpoint (llama.cpp's llama-server or vLLM) on a rebuilt track:

```
python -m platebench.harness.run --track snapme --server http://127.0.0.1:8080 \
    --model-name my-model --output predictions/snapme/my-model.jsonl
```

A model that outputs plate totals directly (a regressor) can write the prediction file itself. The format is one
JSON object per line:

```
{"id": "snapme-0033c3304cdd98508a4afd6c7eaa", "model": "my-model", "kcal": 412.0, "protein": 20.1, "carbs": 45.0, "fat": 14.2}
```

`kcal` is required (use `null` for a photo the model failed to answer); macros are optional. Every photo of the
track needs a row.

## Score

```
python -m platebench.score --track snapme --predictions predictions/snapme/my-model.jsonl --against CalorieK
python -m platebench.score --track jfb --model "Plum 1" --model "Grape 1" --against CalorieK
python -m platebench.score --all                       # every registered model on every track with references
```

Rules:

- A photo without a prediction counts as 0 kcal. Failures are never dropped.
- Intervals: 2,000 bootstrap resamples, seed 0. NutritionVerse resamples dishes and SNAPMe resamples
  participant-days, because their photos are not independent; the other tracks resample photos.
- A paired difference is the mean over photos of |error of A| minus |error of B|, with its own interval from the
  same resampled photos. An interval that contains zero is a tie.
- Reported with MAE: bias, median absolute error, MAE as a share of the mean reference, median relative error,
  share of photos within 20% and within 100 kcal, and protein, carbs and fat MAE where the predictions carry them.
- `--holdout only` or `--holdout exclude` restricts SNAPMe and JFB to the holdout slice or its complement.

## Holdout slice

`ids/holdout-2026-10-19.txt` lists 296 SNAPMe photos (177 participant-days) and 200 JFB photos. The rule is in
`platebench/holdout.py`: within each reference-kcal quartile, take the first 20% of photos by SHA-256 of the photo
id. `python -m platebench.holdout` rebuilds the slice from the references and checks it against the file. The slice
was read once, for the paper's holdout table, and is spent: use the complement or a new rule for new decisions.

## Stored predictions and the paper tables

`predictions/<track>/<file>.jsonl` holds the per-photo predictions of the models in the paper's holdout and
all-tracks tables, on all eight public tracks. `models.json` describes each file and defines the named entries,
including blends (Plum 1 is 0.55 x Grape + 0.45 x J5 per photo) and seed means. Grape 1 is G5 seed 13. These are
research outputs scored on a PC, not phone accuracy: Grape was run by the training code with a bicubic resize, and
J5 in PyTorch.

To check the paper's public-track numbers, rebuild the eight tracks (references only is enough) and run:

```
python -m platebench.paper
```

It recomputes the all-tracks table (kcal MAE on the full tracks and the G5 seed range) and the holdout table (MAE,
interval, bias, median relative error, share within 20%, paired differences against CalorieK and against the
previous Plum candidate, and the holdout macro errors quoted in the text), and compares each value at the precision
the paper prints. All 288 values match.

Only the public tracks are part of this repository.

## Citation

```
@article{canivel2026platebench,
  title   = {Distributional Readouts Make Small Vision-Language Models Better Calorie Estimators},
  author  = {Canivel, Danilo},
  year    = {2026},
  note    = {arXiv: to be added}
}
```

When you use a track, also cite its dataset (see `NOTICE`).

## License

Code: Apache License 2.0 (`LICENSE`), Copyright 2026 Canivel LLC. The reference files in `references/` keep the
license of their source dataset: CC BY 4.0 for Nutrition5k and JFB, CC BY-SA 4.0 for SNAPMe. See `NOTICE`.
