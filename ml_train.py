"""Headline -> (market) move / direction models. Rules: research/ml-rules.md section A (pre-registered; blob a6140e5).
  /opt/anaconda3/bin/python3 ml_train.py select   # fit grid on train, choose by VALIDATION only, pickle chosen models, print val table
  /opt/anaconda3/bin/python3 ml_train.py test     # load pickled models, score TEST once (refuses to run twice), print table + PASS/FAIL
Models: baseline (lexicon polarity for direction; market recent |move| rate for y_move), price-only HGB (p0, fills/h, fills/7d, hour),
text HGB (headline emb PCA32 + market-slug emb PCA16 + price features). Train = real + placebo rows of the train split; val/test = real rows."""
import itertools, json, os, sys
import numpy as np, pandas as pd, joblib
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.metrics import roc_auc_score
PRICE = ["p0", "pre60", "n7d", "hour"]
GRID = [dict(learning_rate=lr, max_leaf_nodes=nl, max_iter=150, l2_regularization=1.0, random_state=0) for lr, nl in itertools.product([0.05, 0.1], [15, 31])]
BAR_AUC, BAR_ACC = 0.05, 0.55

def wilson(k, n, z=1.959964):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)

def embed(D):
    f = "data/ml_emb.joblib"
    if os.path.exists(f): E = joblib.load(f)
    else:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer("all-MiniLM-L6-v2")
        ut, us = D.text.unique(), D.slug.unique()
        E = dict(text=dict(zip(ut, m.encode(list(ut), batch_size=256, normalize_embeddings=True, show_progress_bar=False).astype("float32"))),
                 slug=dict(zip(us, m.encode([s.replace("-", " ") for s in us], batch_size=256, normalize_embeddings=True, show_progress_bar=False).astype("float32"))))
        joblib.dump(E, f)
    return np.stack([E["text"][t] for t in D.text.values]), np.stack([E["slug"][s] for s in D.slug.values])

def feats(D, X, pca=None):
    ET, ES = X
    if pca is None:
        tr = (D.split == "train").values & ~D.is_placebo.values
        pca = (PCA(32, random_state=0).fit(ET[tr]), PCA(16, random_state=0).fit(ES[tr]))
    P = np.column_stack([D.p0, np.log1p(D.pre60), np.log1p(D.n7d), D.hour]).astype("float32")
    return P, np.hstack([P, pca[0].transform(ET), pca[1].transform(ES)]).astype("float32"), pca

def fit_best(Xtr, ytr, Xva, yva, metric):
    best = None
    for g in GRID:
        m = HGB(**g).fit(Xtr, ytr); s = metric(yva, m.predict_proba(Xva)[:, 1])
        print(f"   {g['learning_rate']:.2f}/{g['max_leaf_nodes']:>2}: val {s:.4f}", flush=True)
        if best is None or s > best[0]: best = (s, g, m)
    return best

def calib(y, p, nb=10):
    b = np.minimum((p * nb).astype(int), nb - 1)
    return [dict(bin=f"{i/nb:.1f}-{(i+1)/nb:.1f}", n=int((b == i).sum()), mean_pred=float(p[b == i].mean()) if (b == i).any() else None, observed=float(y[b == i].mean()) if (b == i).any() else None) for i in range(nb)]

def cluster_ci(correct, groups, B=2000, seed=7):
    rng = np.random.RandomState(seed); g = pd.Series(correct).groupby(groups).agg(["sum", "count"]).values
    idx = rng.randint(0, len(g), (B, len(g))); s = g[idx, 0].sum(1) / g[idx, 1].sum(1)
    return tuple(np.percentile(s, [2.5, 97.5]))

def main(stage):
    D = pd.read_parquet("data/ml_pairs.parquet"); X = embed(D)
    tr, va, te = [(D.split == s).values for s in ("train", "val", "test")]; real = ~D.is_placebo.values
    if stage == "select":
        P, F, pca = feats(D, X); M = dict(pca=pca); print(f"train rows {int((tr).sum()):,} (placebo {int((tr & ~real).sum()):,}); val real {int((va & real).sum()):,}")
        R = {}
        for name, A in (("price_only", P), ("text_emb", F)):
            print(f"[{name}] y_move AUC grid"); b = fit_best(A[tr], D.y_move.values[tr], A[va & real], D.y_move.values[va & real], roc_auc_score)
            M[name + "_move"] = b[2]; R[name + "_move"] = dict(val_auc=b[0], cfg=b[1])
            mv_tr, mv_va = tr & (D.y_move.values == 1) & real, va & (D.y_move.values == 1) & real     # direction: movers; train on real movers (placebo movers kept too)
            mv_tr = tr & (D.y_move.values == 1)
            print(f"[{name}] y_dir (up=1) grid on movers, metric = accuracy")
            acc = lambda y, p: float(((p > .5) == y).mean())
            b = fit_best(A[mv_tr], (D.y_dir.values[mv_tr] > 0).astype(int), A[mv_va], (D.y_dir.values[mv_va] > 0).astype(int), acc)
            M[name + "_dir"] = b[2]; R[name + "_dir"] = dict(val_acc=b[0], cfg=b[1])
        v = va & real
        R["baseline_move_val_auc"] = roc_auc_score(D.y_move.values[v], np.nan_to_num(D.rate.values[v], nan=0.0))
        mvv = v & (D.y_move.values == 1); call = mvv & (D.polarity.values != 0)
        R["baseline_dir_val"] = dict(acc_on_calls=float((np.sign(D.polarity.values[call]) == D.y_dir.values[call]).mean()), n_calls=int(call.sum()), n_movers=int(mvv.sum()))
        print(json.dumps(R, indent=1, default=float)); joblib.dump(M, "data/ml_models.joblib"); json.dump(R, open("results/ml_selected.json", "w"), indent=1, default=float)
        return
    # ---- test: once ----
    if os.path.exists("results/ml_test.json"): sys.exit("results/ml_test.json exists: test split was already scored once; refusing to score again.")
    M = joblib.load("data/ml_models.joblib"); P, F, _ = feats(D, X, M["pca"]); te = te & real; y = D.y_move.values[te]
    out = dict(n_test=int(te.sum()), base_rate_move=float(y.mean()), n_movers=int(y.sum()), models={})
    score = {"baseline": np.nan_to_num(D.rate.values[te], nan=0.0), "price_only": M["price_only_move"].predict_proba(P[te])[:, 1], "text_emb": M["text_emb_move"].predict_proba(F[te])[:, 1]}
    for k, s in score.items(): out["models"][k] = dict(auc_move=float(roc_auc_score(y, s)))
    out["calibration_text_emb"] = calib(y, score["text_emb"]); out["calibration_price_only"] = calib(y, score["price_only"])
    mv = te & (D.y_move.values == 1); yd = (D.y_dir.values[mv] > 0).astype(int); grp = np.char.add(np.char.add(D.cid.values[mv].astype(str), "_"), (D.t.values[mv] // 86400).astype(str))
    out["up_share_movers"] = float(yd.mean()); out["majority_class_acc"] = float(max(yd.mean(), 1 - yd.mean()))
    for k, A in (("price_only", P), ("text_emb", F)):
        ok = ((M[k + "_dir"].predict_proba(A[mv])[:, 1] > .5) == yd); lo, hi = wilson(int(ok.sum()), len(ok))
        out["models"][k].update(dir_acc=float(ok.mean()), dir_n=int(len(ok)), dir_wilson95=[lo, hi], dir_cluster_boot95=list(cluster_ci(ok, grp)))
    pol = D.polarity.values[mv]; c = pol != 0; ok = np.sign(pol[c]) == np.sign(yd[c] - .5); lo, hi = wilson(int(ok.sum()), int(c.sum()))
    out["models"]["baseline"].update(dir_acc=float(ok.mean()), dir_n=int(c.sum()), dir_coverage=float(c.mean()), dir_wilson95=[lo, hi])
    t = out["models"]["text_emb"]; b = out["models"]["baseline"]
    out["pass_auc"] = bool(t["auc_move"] >= b["auc_move"] + BAR_AUC); out["pass_dir"] = bool(t["dir_acc"] > BAR_ACC and t["dir_wilson95"][0] > 0.5)
    out["verdict"] = "PASS" if out["pass_auc"] and out["pass_dir"] else "FAIL"
    json.dump(out, open("results/ml_test.json", "w"), indent=1, default=float); print(json.dumps(out, indent=1, default=float))
if __name__ == "__main__": main(sys.argv[1])
