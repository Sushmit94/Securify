import json, math
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, matthews_corrcoef

# SLM v2 on the FULL test set (from the Kaggle run)
SLM_N, SLM_ACC, SLM_AUC = 2715, 0.5514, 0.5489
MAJORITY_FULL = 1469 / 2715          # 0.541, always answering "Not vulnerable"

def wilson(p, n, z=1.96):            # 95% confidence interval for an accuracy
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

is_vul = lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ('vulnerable', 'true', '1')

sec = [json.loads(l) for l in open('securify_predictions.jsonl', encoding='utf-8') if l.strip()]
sec = [r for r in sec if not r.get('error')]           # drop rows where Securify crashed
n = len(sec)
y = np.array([is_vul(r['ground_truth']) for r in sec])
print(f'Securify rows evaluated: {n}  (errors dropped; check this is close to your N)\n')

systems = {'Securify (all layers)': [is_vul(r['prediction']) for r in sec],
           'Securify: static only': [bool(r['static']) for r in sec],
           'Securify: ML only':     [bool(r['ml']) for r in sec],
           'Securify: LLM only':    [bool(r['llm']) for r in sec],
           'Majority (same rows)':  [False] * n}

print(f"{'System':24} {'Acc':>6} {'95% CI':>15} {'Prec':>6} {'Rec':>6} {'F1':>6} {'MCC':>6}")
for name, p in systems.items():
    p = np.array(p)
    pr, rc, f1, _ = precision_recall_fscore_support(y, p, average='binary', zero_division=0)
    acc = accuracy_score(y, p); lo, hi = wilson(acc, n)
    print(f'{name:24} {acc:6.3f} {f"[{lo:.3f},{hi:.3f}]":>15} {pr:6.3f} {rc:6.3f} {f1:6.3f} {matthews_corrcoef(y, p):6.3f}')

lo, hi = wilson(SLM_ACC, SLM_N)
print(f"{'SLM v2 (full test)':24} {SLM_ACC:6.3f} {f'[{lo:.3f},{hi:.3f}]':>15}    n/a    n/a    n/a    n/a")
print(f"{'Majority (full test)':24} {MAJORITY_FULL:6.3f}")
print(f"\nSecurify AUC: {roc_auc_score(y, [float(r['score']) for r in sec]):.4f}   SLM v2 AUC: {SLM_AUC}")