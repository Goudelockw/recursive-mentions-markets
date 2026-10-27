"""What every model term means. Used by the Models page and the release reviews.

kind:
  predictor  a real input; its coefficient is a finding
  fill-in    only switches off a default when data is missing; its coefficient is a correction
  binary     values are 0 / 1 (the effect is "when it is 1")
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Var:
    label: str
    meaning: str
    values: str
    source: str
    kind: str = "predictor"
    binary: bool = False


V = Var
DEFS: dict[str, Var] = {
    # ---- fundamental model: our data only
    "r4": V("Hit rate, last 4 calls",
            "How often the company cleared the market's mention bar on its last 4 calls, smoothed and on a log-odds scale: logit((said + 0.5) / (calls + 1)).",
            "−2.2 = said on none of 4 · 0 = half · +2.2 = all 4", "mv_word_counts"),
    "said_prev": V("Said on the last call", "The company cleared the mention bar on its most recent call.",
                   "1 = yes, 0 = no", "mv_word_counts", binary=True),
    "avg_count": V("Mentions per call", "Average mentions per call over the last 8 calls, as log(1 + average).",
                   "0 = never · 0.7 = 1 a call · 1.1 = 2 · 2.4 = 10", "mv_word_counts"),
    "no_hist": V("No transcript history", "We hold no earlier transcripts for the company, so every history feature reads as 'never said'.",
                 "1 = no history (fill-in)", "mv_word_counts", kind="fill-in", binary=True),
    "multi": V("Needs several mentions", "The market resolves YES only on 2+ or 3+ mentions, not 1.",
               "1 = multi-mention market", "markets", binary=True),
    "ext": V("Outside topic", "The word is an outside topic (macro, politics, another company), not the company's own business. Claude-labeled.",
             "1 = outside topic", "word_categories", binary=True),
    "politics": V("Politics word", "The word is about politics or geopolitics. Claude-labeled.", "1 = politics / geopolitics",
                  "word_categories", binary=True),
    "analyst_rate4": V("Analyst hit rate, last 4 calls", "How often an analyst said the word on the last 4 calls, smoothed, log-odds.",
                       "−2.2 = never · +2.2 = every call", "mv_word_features"),
    "corpus_spike_z": V("Spiking on other calls", "How much more other companies are saying it in the last 90 days than their 365-day pace (0 when fewer than 3 hits). Capped at ±5.",
                        "0 = normal · +2 = clearly spiking · negative = fading", "mv_word_corpus"),
    "corpus_rare": V("Rare word", "Said on under 10% of other companies' calls in the past 365 days.", "1 = rare",
                     "mv_word_corpus", binary=True),
    "analysts_n": V("Analysts per call", "Analysts asking questions per call, average of the last 4, scaled as (n − 9.5) / 3.",
                    "0 ≈ 9–10 analysts · +1 ≈ 12–13 · −1 ≈ 6–7", "mv_call_features"),
    "said_yoy": V("Said a year ago", "Cleared the bar on the company's call about a year earlier (same quarter).", "1 = yes (0 if no call a year back)",
                  "mv_word_context", binary=True),
    "has_yoy": V("Has a year-ago call", "We hold the company's call from about a year earlier.", "1 = yes (fill-in)",
                 "mv_word_context", kind="fill-in", binary=True),
    "peer_rate": V("Peer-industry rate", "Share of same-sector (2-digit SIC) companies' calls in the last 180 days that said it, log-odds; 0 with fewer than 3 peer calls.",
                   "−2.2 ≈ 10% · 0 ≈ 50% · +2.2 ≈ 90%", "mv_word_context"),
    "has_peer": V("Has peer calls", "At least 3 peer calls exist in that window.", "1 = yes (fill-in)", "mv_word_context",
                  kind="fill-in", binary=True),
    "val": V("Valence", "How good the topic is for the company. Claude-labeled.", "−2 very negative … 0 neutral … +2 very positive",
             "word_valence"),
    "val_neutral": V("Neutral word", "Valence is exactly 0.", "1 = neutral", "word_valence", binary=True),
    "val_strong": V("Strongly positive word", "Valence is +2: management loves to talk about it.", "1 = valence +2", "word_valence",
                    binary=True),
    "inc": V("Management incentive", "Would management bring it up unprompted? Claude-labeled.", "0 = no reason · 1 = maybe · 2 = wants to",
             "word_incentive"),
    "story0": V("Not central to the story", "The topic is not central to the company's story this quarter. Claude-labeled.",
                "1 = not central", "word_incentive", binary=True),
    "filing_said": V("In this quarter's release", "The word appears in this quarter's earnings press release (8-K / 6-K). Only known once the release is filed, so only in the call-start models.",
                     "1 = in the release", "filings", binary=True),
    "rel_head": V("In the release headline", "The word appears in the release's headline or highlights. Call-start models only.",
                  "1 = in the headline", "filings", binary=True),
    # ---- combined model
    "lp": V("Market price at call start", "The bid/ask midpoint just before the call, as log-odds.", "−2.2 ≈ 10¢ · 0 = 50¢ · +2.2 ≈ 90¢",
            "mv_precall_prices"),
    "lp24": V("Market price 24h before", "The midpoint about 24 hours before the call, as log-odds.", "−2.2 ≈ 10¢ · 0 = 50¢ · +2.2 ≈ 90¢",
              "mv_precall_prices"),
    "lA": V("Fundamental model's estimate", "The fundamental model's probability, as log-odds (fitted out-of-fold so it can't memorise).",
            "−2.2 ≈ 10% · 0 = 50% · +2.2 ≈ 90%", "this model"),
    "move24": V("Price move into the call", "Change in log-odds price from 24h before to call start. Capped at ±3; 0 when there was no earlier quote.",
                "+0.4 ≈ 50¢ → 60¢ · negative = price fell", "mv_precall_prices"),
    "has24": V("Had a price 24h before", "A quote existed 24 hours before the call.", "1 = yes (fill-in)", "mv_precall_prices",
               kind="fill-in", binary=True),
    "(Intercept)": V("Baseline", "The log-odds when every input is 0.", "–", "–", kind="fill-in"),
    "calibration_k": V("Calibration k", "How far the final probability moves from the market price toward the combined model, learned walk-forward.",
                       "0 = just the market · 1 = full model · e.g. 0.67 = two-thirds of the way", "this model", kind="setting"),
}

MODELS = {
    "fundamental": "Fundamental model, call start: our data only, including this quarter's release",
    "fundamental_early": "Fundamental model, 24h before: our data only, no release",
    "combined": "Combined model, call start: market price + fundamental + price move + release + incentive",
    "combined_early": "Combined model, 24h before: market price 24h before + fundamental + incentive",
}

RISK_POINTS = {
    "y_not_central": "YES favorite, but the topic isn't central to the story",
    "y_not_in_prepared": "YES favorite, but it wasn't in last call's prepared remarks",
    "y_few_mentions": "YES favorite with few mentions per call",
    "y_skipped_last_call": "YES favorite that wasn't said on the last call",
    "y_no_reason_to_say": "YES favorite, but management has no reason to say it",
    "y_no_analyst_last_call": "YES favorite that no analyst raised last call",
    "y_one_speaker": "YES favorite that only one speaker used",
    "n_mgmt_has_reason": "NO favorite, but management has a reason to say it",
    "n_mgmt_wants_it": "NO favorite, but management wants to say it",
    "n_other_exec_said_last": "NO favorite, but another executive said it last call",
    "n_two_plus_speakers": "NO favorite, but 2+ speakers used it",
    "n_said_before": "NO favorite for a word the company has said before",
    "price_fell_5c": "The favorite's price fell 5¢+ in the last 24h",
}


def label(term: str) -> str:
    return DEFS[term].label if term in DEFS else term
