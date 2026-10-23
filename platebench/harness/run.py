"""Run a generative model on a rebuilt track the way the app calls it, and write a prediction file.

The model is served behind an OpenAI-compatible chat endpoint: llama.cpp's llama-server (the grammar is passed as
`grammar`, temperature 0.1, the app setting) or vLLM (the grammar is passed as structured outputs; pass
--server-kind vllm). Each photo gets PROMPT; if the answer does not parse, one retry with RETRY_PROMPT.

  python -m platebench.harness.run --track snapme --server http://127.0.0.1:8080 --model-name my-model \\
      --output predictions/snapme/my-model.jsonl

The output has one row per photo: {"id", "model", "kcal", "protein", "carbs", "fat", "grams", "attempt"}; a photo
with no parsable answer gets "kcal": null and is scored as 0 kcal.
"""
import argparse
import base64
import hashlib
import json
import urllib.request
from pathlib import Path

from platebench.harness.contract import GRAMMAR, OUTPUT_TOKENS, PROMPT, RETRY_PROMPT, TEMPERATURE, app_jpeg, parse_items, totals
from platebench.tracks import DATA


def chat(server, jpeg, prompt, kind, served_model, temperature, seed):
    payload = {'messages': [{'role': 'user', 'content': [
                   {'type': 'text', 'text': prompt},
                   {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(jpeg).decode()}}]}],
               'max_tokens': OUTPUT_TOKENS, 'temperature': temperature, 'seed': seed,
               'chat_template_kwargs': {'enable_thinking': False}}
    if kind == 'vllm':
        payload.update(model=served_model, structured_outputs={'grammar': GRAMMAR})
    else:
        payload.update(grammar=GRAMMAR)
    request = urllib.request.Request(server.rstrip('/') + '/v1/chat/completions', data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)['choices'][0]['message']['content']


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--track', required=True)
    p.add_argument('--data', type=Path, default=DATA)
    p.add_argument('--server', required=True)
    p.add_argument('--server-kind', choices=('llama', 'vllm'), default='llama')
    p.add_argument('--served-model', default=None, help='vLLM served model name')
    p.add_argument('--model-name', required=True, help='name written into each prediction row')
    p.add_argument('--temperature', type=float, default=TEMPERATURE)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    from PIL import Image
    root = args.data / args.track
    rows = [json.loads(line) for line in (root / 'test.jsonl').read_text().splitlines()]
    if 'image' not in rows[0]:
        raise SystemExit(f'{root} was rebuilt with --no-images; rebuild it with images to run a model')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w') as out:
        for row in rows:
            path = root / row['image']
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise SystemExit(f"{row['id']}: image checksum changed")
            with Image.open(path) as image:
                jpeg = app_jpeg(image)
            result = {'id': row['id'], 'model': args.model_name, 'kcal': None}
            for attempt, prompt in enumerate((PROMPT, RETRY_PROMPT), 1):
                raw = chat(args.server, jpeg, prompt, args.server_kind, args.served_model, args.temperature, args.seed)
                try:
                    result.update(totals(parse_items(raw)), attempt=attempt)
                    break
                except ValueError:
                    result['attempt'] = attempt
            out.write(json.dumps(result) + '\n')
            out.flush()


if __name__ == '__main__':
    main()
