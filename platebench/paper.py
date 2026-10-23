"""Reproduce the paper's public-track numbers from the stored predictions and compare them with the printed values.

  python -m platebench.paper            # needs references for all eight tracks (data/ or references/)

Checks Table "all tracks" (kcal MAE on the full public tracks, G5 seed range) and Table "holdout" (MAE, interval,
bias, median relative error, share within 20%, paired differences against CalorieK and against the previous Plum
candidate, and the macro MAE quoted in the text). A value matches when it is equal at the precision the paper prints.
Exit status 1 if anything differs.
"""
import json
import sys

from platebench.score import entry, load_track, score
from platebench.tracks import TRACKS

TRACK_ORDER = ['overhead', 'angled', 'nutritionverse', 'snapme', 'jfb', 'diningbench', 'diningbench-customer', 'omnifood8k']

# Table "all tracks": kcal MAE, in TRACK_ORDER.
ALL_TRACKS = {
    'CalorieK': '104.9 57.2 657.2 158.0 178.5 312.7 320.3 228.1',
    'Boba': '108.5 83.3 680.7 197.5 241.4 472.2 458.1 259.7',
    'Qwen3.8-27B zero-shot': '92.7 102.7 427.7 135.8 132.2 226.0 236.5 143.0',
    'E2 Q8_0': '72.3 65.7 584.3 158.9 194.2 368.6 344.5 243.2',
    'R1E': '52.9 54.7 576.8 137.3 149.5 297.9 288.9 180.5',
    'J5': '49.8 47.4 462.3 133.7 135.2 227.2 243.4 189.7',
    'E2-D-J5 list (t0.1)': '52.1 53.9 480.8 136.4 152.2 272.1 286.6 205.8',
    'G5 (Grape 1 recipe)': '50.1 48.7 525.5 136.6 143.9 232.0 239.6 167.9',
    'Previous Plum candidate (G5 seed mean)': '48.4 46.8 509.3 132.9 135.8 226.6 235.2 169.4',
    'Plum 1 total (G5 seed mean)': '45.3 43.9 490.3 131.2 131.6 219.0 231.0 173.0',
}
G5_RANGE = '49.6-50.6 48.1-49.3 517-534 136.2-136.9 142.0-145.8 229.7-234.2 237.6-241.6 163.6-172.1'

# Table "holdout": MAE [CI], bias, median relative error %, within 20 %, vs CalorieK [CI], vs previous [CI].
HOLDOUT = {
    'snapme': {
        'Plum 1': '126.0 111.6 141.7 -34 40.6 25.3 -28.5 -38.2 -19.2 -1.5 -4.9 +1.7',
        'Previous Plum candidate': '127.4 112.7 143.3 -33 43.4 24.3 -27.0 -36.9 -17.3',
        'Grape 1': '131.2 117.0 146.8 -34 43.7 24.3 -23.2 -33.0 -13.3 +3.8 +1.8 +5.9',
        'J5': '131.2 115.8 147.3 -33 42.7 26.4 -23.2 -33.2 -13.2 +3.8 -4.2 +11.8',
        'R1E': '133.5 118.6 149.4 -41 44.1 23.6 -21.0 -28.8 -13.2 +6.0 -0.7 +12.4',
        'Qwen3.8-27B zero-shot': '132.5 116.4 153.1 +28 36.8 25.3 -22.0 -39.8 +0.2 +5.0 -10.0 +23.9',
        'CalorieK': '154.5 138.1 172.5 -46 49.5 21.3 _ _ _ +27.0 +17.3 +36.9',
        'Boba': '190.1 167.2 213.5 -77 57.3 15.2 +35.6 +20.1 +51.9 +62.6 +44.2 +81.6',
    },
    'jfb': {
        'Plum 1': '133.4 118.1 148.5 -14 25.4 39.5 -36.7 -53.9 -19.8 -7.0 -13.8 -0.7',
        'Previous Plum candidate': '140.4 123.4 158.2 -7 26.8 38.5 -29.7 -48.7 -10.9',
        'Grape 1': '147.8 129.3 167.4 -5 27.1 39.5 -22.3 -41.7 -1.9 +7.4 +4.1 +10.9',
        'J5': '134.5 119.3 149.8 -25 24.6 37.5 -35.7 -53.2 -18.6 -5.9 -21.5 +8.7',
        'R1E': '144.6 126.9 162.8 -75 27.2 37.0 -25.5 -40.8 -10.0 +4.2 -9.8 +17.7',
        'Qwen3.8-27B zero-shot': '142.4 122.0 165.1 +55 22.6 45.5 -27.7 -53.3 -0.8 +2.0 -17.7 +22.6',
        'CalorieK': '170.1 151.7 189.1 -104 33.1 26.5 _ _ _ +29.7 +10.9 +48.7',
        'Boba': '241.9 216.3 269.3 -194 48.7 17.5 +71.8 +53.1 +91.5 +101.5 +80.3 +126.0',
    },
}
# Holdout macro MAE (g), protein / carbs / fat, quoted in the results text.
HOLDOUT_MACROS = {
    'snapme': {'Plum 1 list scaled to the Plum 1 total': '6.8 15.4 7.6', 'CalorieK': '10.1 20.1 8.6'},
    'jfb': {'Plum 1 list scaled to the Plum 1 total': '9.0 17.3 9.6', 'CalorieK': '12.1 21.6 10.1'},
}


def same(value, printed):
    """True when value printed at the paper's precision equals the printed string."""
    decimals = len(printed.split('.')[1]) if '.' in printed else 0
    return float(f'{value:.{decimals}f}') == float(printed)


class Report:
    def __init__(self):
        self.checked, self.bad = 0, []

    def check(self, where, value, printed):
        self.checked += 1
        if not same(value, printed):
            self.bad.append(f'{where}: computed {value:.3f}, paper {printed}')


def scaled_list_macros(track):
    """Plum 1's food list scaled so its kcal sum equals the Plum 1 total (rule used when the holdout was read).

    An empty or 0 kcal list keeps Grape's single whole-meal item, so Grape's macro heads are used for that photo."""
    import numpy as np
    lst, grape = track.file('e2-d-j5-list-t0.1'), track.file('g5-seed13')
    total = track.predict({'g5-seed13': 0.55, 'j5': 0.45})
    out = {m: [] for m in ('protein', 'carbs', 'fat')}
    for i, t in zip(track.ids, total):
        s = float(lst[i].get('kcal') or 0.0)
        src, scale = (lst[i], t / s) if s > 0 else (grape[i], 1.0)
        for m in out:
            out[m].append(abs(float(src.get(m) or 0.0) * scale - float(track.rows[i]['reference'][m])))
    return {m: float(np.mean(v)) for m, v in out.items()}


def main():
    report = Report()
    lines = ['Table all tracks (kcal MAE, full public tracks):', '',
             '| Model | ' + ' | '.join(TRACK_ORDER) + ' |', '| --- |' + ' --- |' * len(TRACK_ORDER)]
    tracks = {name: load_track(name) for name in TRACK_ORDER}
    for name, printed in ALL_TRACKS.items():
        cells = []
        for track, value in zip(TRACK_ORDER, printed.split()):
            s = score(tracks[track], entry(name))
            report.check(f'all tracks / {name} / {track}', s['mae'], value)
            cells.append(f"{s['mae']:.1f}" + ('' if same(s['mae'], value) else f' (paper {value})'))
        lines.append(f'| {name} | ' + ' | '.join(cells) + ' |')
    cells = []
    for track, printed in zip(TRACK_ORDER, G5_RANGE.split()):
        low, high = score(tracks[track], entry('G5 (Grape 1 recipe)'))['mae_seed_range']
        plow, phigh = printed.split('-')
        report.check(f'G5 seed range / {track} / low', low, plow)
        report.check(f'G5 seed range / {track} / high', high, phigh)
        decimals = len(plow.split('.')[1]) if '.' in plow else 0
        cells.append(f'{low:.{decimals}f}-{high:.{decimals}f}')
    lines.append('| G5 seed range | ' + ' | '.join(cells) + ' |')
    against = {'CalorieK': entry('CalorieK'), 'previous': entry('Previous Plum candidate')}
    for track_name, rows in HOLDOUT.items():
        track = load_track(track_name, holdout='only')
        lines += ['', f'Table holdout, {track_name} ({len(track.ids)} photos, {len(set(track.groups))} groups):', '',
                  '| Model | MAE [95% CI] | Bias | Med. rel. | Within 20% | vs CalorieK | vs previous |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for name, printed in rows.items():
            s = score(track, entry(name), against)
            values = [s['mae'], *s['mae_ci95'], s['bias'], s['median_rel_pct'], s['within20_pct'],
                      s['vs CalorieK']['diff'], *s['vs CalorieK']['ci95'], s['vs previous']['diff'], *s['vs previous']['ci95']]
            for k, (value, p) in enumerate(zip(values, printed.split())):
                if p != '_':
                    report.check(f'holdout / {track_name} / {name} / field {k}', value, p)
            d = lambda key: f"{s[key]['diff']:+.1f} [{s[key]['ci95'][0]:+.1f}, {s[key]['ci95'][1]:+.1f}]"
            lines.append(f"| {name} | {s['mae']:.1f} [{s['mae_ci95'][0]:.1f}, {s['mae_ci95'][1]:.1f}] | {s['bias']:+.0f} | "
                         f"{s['median_rel_pct']:.1f}% | {s['within20_pct']:.1f}% | "
                         f"{'' if name == 'CalorieK' else d('vs CalorieK')} | {'' if name == 'Previous Plum candidate' else d('vs previous')} |")
        for name, printed in HOLDOUT_MACROS[track_name].items():
            got = scaled_list_macros(track) if name.startswith('Plum') else score(track, entry(name))['macro_mae_g']
            values = [got['protein'], got['carbs'], got['fat']]
            for m, value, p in zip(('protein', 'carbs', 'fat'), values, printed.split()):
                report.check(f'holdout macros / {track_name} / {name} / {m}', value, p)
            lines.append(f'Macro MAE (g), {name}: ' + ' / '.join(f'{v:.1f}' for v in values))
    lines += ['', f'{report.checked} printed values checked, {len(report.bad)} differ.'] + report.bad
    print('\n'.join(lines))
    sys.exit(1 if report.bad else 0)


if __name__ == '__main__':
    main()
