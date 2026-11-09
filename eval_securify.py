# eval_securify.py  -- run from the Securify repo root with the venv's Python:
#   .\venv\Scripts\python.exe eval_securify.py
import asyncio, inspect, json, os, random, sys, tempfile

# ---- CONFIG: edit these ----------------------------------------------------
TEST_FILE = r'C:\Users\hp\OneDrive\Desktop\c++\slm-vuln-detection\data\processed\test.jsonl'     # same test.jsonl you uploaded to Kaggle as TestData
OUT_FILE = 'securify_predictions.jsonl'
N = 500                                   # None = full test set (resumes from OUT_FILE)
PASS_PATH = True                          # True: pipeline function takes a file path; False: takes code text
FUNC_NAME = None                          # e.g. 'scan_file'; None = try common names
# -----------------------------------------------------------------------------

from backend.services import pipeline     # adapt if your module lives elsewhere

if FUNC_NAME is None:
    for cand in ('scan_file', 'scan_code', 'scan', 'analyze_file', 'analyze', 'run_pipeline', 'run'):
        if callable(getattr(pipeline, cand, None)):
            FUNC_NAME = cand
            break
if FUNC_NAME is None:
    sys.exit('No scan function found. Available names: ' +
             str([n for n in dir(pipeline) if not n.startswith('_')]) + '\nSet FUNC_NAME above.')
scan = getattr(pipeline, FUNC_NAME)
print('Using pipeline function:', FUNC_NAME)

if not os.path.exists(TEST_FILE):
    sys.exit(f'TEST_FILE not found: {TEST_FILE}')

def to_dict(report):
    if inspect.iscoroutine(report):
        report = asyncio.run(report)
    for attr in ('model_dump', 'dict'):            # pydantic objects
        if hasattr(report, attr):
            return getattr(report, attr)()
    return report

def run_securify(code: str) -> dict:
    path = None
    try:
        if PASS_PATH:
            with tempfile.NamedTemporaryFile('w', suffix='.c', delete=False, encoding='utf-8') as f:
                f.write(code); path = f.name
            report = to_dict(scan(path))
        else:
            report = to_dict(scan(code))
    finally:
        if path and os.path.exists(path):
            os.unlink(path)
    findings = report.get('findings', []) if isinstance(report, dict) else []
    src = lambda name: any(name in f.get('sources', []) for f in findings)
    return {'any': len(findings) > 0,
            'score': max([f.get('confidence', 0) for f in findings], default=0.0),
            'static': src('static_analysis'), 'ml': src('ml_classifier'), 'llm': src('llm_reasoning'),
            '_report': report}

rows = [json.loads(l) for l in open(TEST_FILE, encoding='utf-8') if l.strip()]
ids = list(range(len(rows)))
if N:
    random.Random(42).shuffle(ids); ids = sorted(ids[:N])
json.dump(ids, open('subset_ids.json', 'w'))        # reuse these ids for every other system

done = set()
if os.path.exists(OUT_FILE):
    done = {json.loads(l)['id'] for l in open(OUT_FILE, encoding='utf-8') if l.strip()}

EMPTY = {'any': False, 'score': 0.0, 'static': False, 'ml': False, 'llm': False}
n_err, streak, shown = 0, 0, False

with open(OUT_FILE, 'a', encoding='utf-8') as out:
    for n, i in enumerate(ids):
        if str(i) in done:
            continue
        row = rows[i]
        try:
            r = run_securify(row['code']); err = None; streak = 0
            if not shown:                            # check once that the report schema matches
                print('First report (check "findings" and "sources" keys exist):')
                print(json.dumps(r['_report'], indent=2, default=str)[:1500]); shown = True
        except Exception as e:
            r, err = dict(EMPTY), f'{type(e).__name__}: {e}'[:300]
            n_err += 1; streak += 1
            if n_err <= 3: print(f'ERROR on row {i}: {err}')
            if streak >= 5 and n_err == streak:      # first 5 rows all failed -> adapter is wrong
                sys.exit('First 5 rows all failed. Fix the adapter before running more.')
        out.write(json.dumps({'id': str(i), 'ground_truth': row['response'],
                              'prediction': 'Vulnerable' if r['any'] else 'Not vulnerable',
                              'score': r['score'], 'static': r['static'], 'ml': r['ml'], 'llm': r['llm'],
                              'error': err}) + '\n')
        out.flush()
        if (n + 1) % 25 == 0:
            print(f'{n+1}/{len(ids)}  (errors so far: {n_err})')

print(f'Done. Errors: {n_err}. Results in {OUT_FILE}')