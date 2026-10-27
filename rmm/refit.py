"""Refit the mentions models: the Python port of refit_models.R.

Same four logistic regressions, same walk-forward backtest, same calibration factor k:
  fundamental        our data only, including this quarter's release
  fundamental_early  same, without release information (used before the release is out)
  combined           price at call start + fundamental + 24h price move + release word + incentive
  combined_early     price ~24h before the call + fundamental (early) + incentive
Each combined model's disagreement with the price is scaled by k, learned walk-forward.

Differences from the R script, all deliberate:
  - It never touches the live model. A refit is a challenger: saved under
    outputs/models/vN_YYYY-MM-DD/ and, with --save, as version N in kalshi.model_versions. It goes
    live only through kalshi.promote_model(N), which only the database owner can run.
  - The out-of-fold folds are drawn with a port of R's own set.seed(2024) / sample() (rmm/rrng.py),
    so a Python refit gives the same coefficients as refit_models.R on the same data.
  - v_model_training now names its date column call_date_est; it is read as call_date.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import expit, logit

from .rrng import RRandom

MIN_TRAIN_CALLS = 60
CAL_MIN = 500
SEED = 2024

BASE_TERMS = ["r4", "said_prev", "avg_count", "no_hist", "multi", "ext", "politics", "analyst_rate4",
              "corpus_spike_z", "corpus_rare", "analysts_n", "said_yoy", "has_yoy", "peer_rate", "has_peer",
              "val", "val_neutral", "val_strong", "inc", "story0"]
F_FULL = BASE_TERMS + ["filing_said", "rel_head"]
F_EARLY = BASE_TERMS
B_FULL = ["lp", "lA", "move24", "has24", "filing_said", "inc"]
B_EARLY = ["lp24", "lA", "inc"]
STAGES = {  # stage -> (fundamental terms, combined terms, price column, model names)
    "call_start": (F_FULL, B_FULL, "lp", ("fundamental", "combined")),
    "early_24h": (F_EARLY, B_EARLY, "lp24", ("fundamental_early", "combined_early")),
}


def clip(p):
    return np.clip(p, 0.01, 0.99)


def prepare(rows: list[dict] | pd.DataFrame) -> pd.DataFrame:
    d = pd.DataFrame(rows).copy()
    if "call_date" not in d and "call_date_est" in d:
        d["call_date"] = d["call_date_est"]
    for c in set(F_FULL + ["won", "bid", "ask", "lp", "lp24", "move24_raw"]) & set(d.columns):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["call_date"] = pd.to_datetime(d["call_date"], errors="coerce")
    d = d[d["call_date"].notna()].sort_values(["call_date", "ticker"]).reset_index(drop=True)
    d["move24"] = d["move24_raw"].fillna(0.0)
    d["has24"] = d["move24_raw"].notna().astype(int)
    d["price"] = clip((d["bid"] + d["ask"]) / 2)
    d["month"] = d["call_date"].dt.strftime("%Y-%m")
    return d


# ---------------------------------------------------------------- R's glm and predict

@dataclass
class Fit:
    terms: list[str]
    params: pd.Series   # "(Intercept)" first, then terms
    se: pd.Series | None = None
    p_value: pd.Series | None = None
    sd: pd.Series | None = None    # each term's standard deviation in the rows it was fitted on

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        """P(YES); NaN where a term is missing, like predict.glm on new data."""
        X = x[self.terms].to_numpy(float)
        eta = self.params.iloc[0] + X @ self.params.iloc[1:].to_numpy()
        return expit(eta)


def fit(terms: list[str], x: pd.DataFrame) -> Fit:
    """glm(won ~ terms, binomial) with R's default na.omit."""
    m = x[terms + ["won"]].dropna()
    X = sm.add_constant(m[terms].to_numpy(float), has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = sm.GLM(m["won"].to_numpy(float), X, family=sm.families.Binomial()).fit()
    idx = ["(Intercept)"] + terms
    return Fit(terms, pd.Series(res.params, index=idx), pd.Series(res.bse, index=idx),
               pd.Series(res.pvalues, index=idx), pd.Series([np.nan] + list(m[terms].std(ddof=1)), index=idx))


def oof(terms: list[str], x: pd.DataFrame, k: int = 5) -> np.ndarray:
    """Out-of-fold fundamental log-odds, folds by call so a call never scores itself."""
    ev = x["event_ticker"].unique()
    fold = dict(zip(ev, RRandom(SEED).sample(list(np.resize(np.arange(1, k + 1), len(ev))))))
    f = x["event_ticker"].map(fold).to_numpy()
    out = np.full(len(x), np.nan)
    for i in range(1, k + 1):
        h = f == i
        out[h] = fit(terms, x[~h]).predict(x[h])
    return logit(clip(out))


def cal_k(p: np.ndarray, price: np.ndarray, y: np.ndarray) -> float:
    """won ~ offset(logit(price)) + k * (logit(p) - logit(price)), no intercept; k kept in [0.2, 1.2]."""
    dev = (logit(p) - logit(price)).reshape(-1, 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = sm.GLM(y.astype(float), dev, family=sm.families.Binomial(), offset=logit(price)).fit()
    return float(min(max(res.params[0], 0.2), 1.2))


# ---------------------------------------------------------------- backtest and final fit

@dataclass
class StageResult:
    stage: str
    backtest: pd.DataFrame      # ticker, stage, p_model, won, price
    k_final: float
    brier_model: float
    brier_price: float
    months: int


def walk_forward(d: pd.DataFrame, stage: str) -> StageResult:
    """Each month scored by models trained only on earlier months."""
    Ff, Bf, pcol, _ = STAGES[stage]
    pB = np.full(len(d), np.nan)
    has_p = d[pcol].notna()
    months = 0
    for mo in sorted(d["month"].unique()):
        tr = (d["month"] < mo) & has_p
        te = (d["month"] == mo) & has_p
        if d.loc[tr, "event_ticker"].nunique() < MIN_TRAIN_CALLS or not te.any():
            continue
        x = d[tr].copy()
        x["lA"] = oof(Ff, x)
        mA = fit(Ff, d[tr])
        y = d[te].copy()
        y["lA"] = logit(clip(mA.predict(y)))
        pB[te.to_numpy()] = fit(Bf, x).predict(y)
        months += 1
    s = ~np.isnan(pB)
    pr = expit(d.loc[s, pcol].to_numpy())
    won = d.loc[s, "won"].to_numpy()
    mon = d.loc[s, "month"].to_numpy()
    pBs = clip(pB[s])
    k = np.ones(s.sum())
    for mo in sorted(set(mon)):
        prv = mon < mo
        if prv.sum() >= CAL_MIN:
            k[mon == mo] = cal_k(pBs[prv], pr[prv], won[prv])
    k_final = cal_k(pBs, pr, won)
    p_model = np.round(clip(expit(logit(pr) + k * (logit(pBs) - logit(pr)))), 5)
    bt = pd.DataFrame({"ticker": d.loc[s, "ticker"].to_numpy(), "stage": stage, "p_model": p_model,
                       "won": won, "price": pr})
    return StageResult(stage, bt, k_final, float(np.mean((p_model - won) ** 2)),
                       float(np.mean((pr - won) ** 2)), months)


def final_fit(d: pd.DataFrame, k: dict[str, float]) -> pd.DataFrame:
    """Coefficients for all four models on every row, plus calibration_k, in model_coefficients' shape."""
    out = []

    def add(model: str, f: Fit) -> None:
        out.extend({"model": model, "term": t, "coef": float(np.format_float_positional(v, 8, fractional=False)),
                    "se": float(f.se[t]), "p_value": float(f.p_value[t]), "sd": float(f.sd[t])}
                   for t, v in f.params.items())

    add("fundamental", fit(F_FULL, d))
    add("fundamental_early", fit(F_EARLY, d))
    x = d.copy()
    x["lA"] = oof(F_FULL, x)
    add("combined", fit(B_FULL, x))
    x = d[d["lp24"].notna()].copy()
    x["lA"] = oof(F_EARLY, x)
    add("combined_early", fit(B_EARLY, x))
    out += [{"model": "combined", "term": "calibration_k", "coef": round(k["call_start"], 3)},
            {"model": "combined_early", "term": "calibration_k", "coef": round(k["early_24h"], 3)}]
    co = pd.DataFrame(out)
    co["trained_through"] = d["call_date"].max().strftime("%Y-%m-%d")
    return co


@dataclass
class Refit:
    data_rows: int
    trained_through: str
    stages: list[StageResult]
    coefficients: pd.DataFrame

    @property
    def backtest(self) -> pd.DataFrame:
        return pd.concat([s.backtest[["ticker", "stage", "p_model"]] for s in self.stages], ignore_index=True)


def run(rows, through: str | None = None) -> Refit:
    d = prepare(rows)
    if through:
        d = d[d["call_date"] <= pd.Timestamp(through)].reset_index(drop=True)
    stages = [walk_forward(d, s) for s in STAGES]
    co = final_fit(d, {s.stage: s.k_final for s in stages})
    return Refit(len(d), co["trained_through"].iloc[0], stages, co)


# ---------------------------------------------------------------- comparison and report

def compare(new: pd.DataFrame, live: pd.DataFrame) -> pd.DataFrame:
    live = live.assign(coef=pd.to_numeric(live["coef"]))[["model", "term", "coef"]]
    m = new[["model", "term", "coef"]].merge(live, on=["model", "term"], how="outer", suffixes=("_new", "_live"))
    m["diff"] = m["coef_new"] - m["coef_live"]
    return m.sort_values(["model", "term"]).reset_index(drop=True)


def render_md(r: Refit, version: str, cmp: pd.DataFrame | None, note: str = "") -> str:
    out = [f"# Model fit · {version}", "",
           f"Trained through **{r.trained_through}** on {r.data_rows:,} settled markets from "
           "`kalshi.v_model_training`. Python port of `refit_models.R` (`rmm/refit.py`). "
           "This is a challenger: nothing was written to the database.", ""]
    if note:
        out += [note, ""]
    out += ["## Walk-forward backtest", "",
            "Each month scored by models trained only on earlier months; k learned the same way.", "",
            "| Stage | Months | Markets | Brier model | Brier price | Model − price | k (all months) |",
            "|---|--:|--:|--:|--:|--:|--:|"]
    for s in r.stages:
        out.append(f"| {s.stage} | {s.months} | {len(s.backtest):,} | {s.brier_model:.4f} | {s.brier_price:.4f} "
                   f"| {s.brier_model - s.brier_price:+.4f} | {s.k_final:.3f} |")
    out += ["", "## Coefficients", ""]
    if cmp is not None:
        out += ["Compared with the live coefficients in `kalshi.model_coefficients`.", "",
                "| Model | Term | New | Live | Change |", "|---|---|--:|--:|--:|"]
        for _, x in cmp.iterrows():
            f = lambda v: "–" if pd.isna(v) else f"{v:+.4f}"
            out.append(f"| {x['model']} | {x['term']} | {f(x['coef_new'])} | {f(x['coef_live'])} | {f(x['diff'])} |")
    else:
        out += ["| Model | Term | Coef |", "|---|---|--:|"]
        out += [f"| {x['model']} | {x['term']} | {x['coef']:+.4f} |" for _, x in r.coefficients.iterrows()]
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- versions in the database

def metrics(r: Refit) -> dict:
    return {s.stage: {"months": s.months, "markets": len(s.backtest), "brier_model": round(s.brier_model, 5),
                      "brier_price": round(s.brier_price, 5), "k": round(s.k_final, 3)} for s in r.stages}


def next_version() -> int:
    from . import db
    return int(db.query("select coalesce(max(version), 0) + 1 as v from kalshi.model_versions")[0]["v"])


def save(r: Refit, version: int, notes: str = "") -> None:
    """Store the refit as challenger `version` (one transaction). Needs the rmm_rw role."""
    import json

    from . import db
    cols = ["model", "term", "coef", "se", "p_value", "sd"]
    co = r.coefficients[r.coefficients["term"] != "calibration_k"][cols]
    k = r.coefficients[r.coefficients["term"] == "calibration_k"][cols]
    db.transaction([
        ("insert into kalshi.model_versions (version, status, trained_through, fitted_at, source, metrics, notes) "
         "values ($1, 'challenger', $2::date, now(), 'rmm refit', $3::jsonb, $4)",
         [version, r.trained_through, json.dumps(metrics(r)), notes or None]),
        ("insert into kalshi.model_version_coefficients (version, model, term, coef, se, p_value, sd) "
         "select $1, model, term, coef, se, p_value, sd from jsonb_to_recordset($2::jsonb) "
         "as x(model text, term text, coef numeric, se numeric, p_value numeric, sd numeric)",
         [version, pd.concat([co, k]).to_json(orient="records")]),
        ("insert into kalshi.model_version_backtest (version, ticker, stage, p_model) "
         "select $1, ticker, stage, p_model from jsonb_to_recordset($2::jsonb) as x(ticker text, stage text, p_model numeric)",
         [version, r.backtest.to_json(orient="records")]),
    ])
