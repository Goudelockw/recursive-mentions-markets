# Model fit · v2

Trained through **2026-10-26** on 6,222 settled markets from `kalshi.v_model_training`. Python port of `refit_models.R` (`rmm/refit.py`). This is a challenger: nothing was written to the database.

## Walk-forward backtest

Each month scored by models trained only on earlier months; k learned the same way.

| Stage | Months | Markets | Brier model | Brier price | Model − price | k (all months) |
|---|--:|--:|--:|--:|--:|--:|
| call_start | 12 | 5,070 | 0.1595 | 0.1626 | -0.0032 | 0.669 |
| early_24h | 12 | 4,854 | 0.1684 | 0.1726 | -0.0042 | 0.758 |

## Coefficients

Compared with the live coefficients in `kalshi.model_coefficients`.

| Model | Term | New | Live | Change |
|---|---|--:|--:|--:|
| combined | (Intercept) | -0.0607 | -0.0791 | +0.0183 |
| combined | calibration_k | +0.6690 | +0.7110 | -0.0420 |
| combined | filing_said | +0.2916 | +0.3154 | -0.0238 |
| combined | has24 | -0.4196 | -0.4438 | +0.0242 |
| combined | inc | +0.1901 | +0.2014 | -0.0114 |
| combined | lA | +0.1846 | +0.1814 | +0.0032 |
| combined | lp | +0.9177 | +0.9326 | -0.0149 |
| combined | move24 | -0.1925 | -0.2053 | +0.0128 |
| combined_early | (Intercept) | -0.4335 | -0.4784 | +0.0448 |
| combined_early | calibration_k | +0.7580 | +0.7960 | -0.0380 |
| combined_early | inc | +0.1983 | +0.2206 | -0.0223 |
| combined_early | lA | +0.2955 | +0.2807 | +0.0149 |
| combined_early | lp24 | +0.8438 | +0.8645 | -0.0207 |
| fundamental | (Intercept) | -0.9505 | -0.9706 | +0.0201 |
| fundamental | analyst_rate4 | +0.1077 | +0.1001 | +0.0076 |
| fundamental | analysts_n | +0.0137 | +0.0215 | -0.0078 |
| fundamental | avg_count | +0.8261 | +0.8486 | -0.0224 |
| fundamental | corpus_rare | +0.0249 | -0.0182 | +0.0432 |
| fundamental | corpus_spike_z | +0.1778 | +0.1789 | -0.0011 |
| fundamental | ext | -0.0266 | -0.0292 | +0.0027 |
| fundamental | filing_said | +0.5965 | +0.6255 | -0.0291 |
| fundamental | has_peer | +0.1377 | +0.0844 | +0.0534 |
| fundamental | has_yoy | -0.2573 | -0.1977 | -0.0596 |
| fundamental | inc | +0.3954 | +0.4021 | -0.0067 |
| fundamental | multi | -2.3358 | -2.3160 | -0.0198 |
| fundamental | no_hist | +1.4406 | +1.5212 | -0.0806 |
| fundamental | peer_rate | +0.0810 | +0.0762 | +0.0048 |
| fundamental | politics | -0.2681 | -0.2669 | -0.0012 |
| fundamental | r4 | +0.0684 | +0.0505 | +0.0178 |
| fundamental | rel_head | +0.8921 | +0.8050 | +0.0871 |
| fundamental | said_prev | +0.6560 | +0.6467 | +0.0093 |
| fundamental | said_yoy | +0.1814 | +0.1961 | -0.0147 |
| fundamental | story0 | -0.3871 | -0.4191 | +0.0320 |
| fundamental | val | -0.0134 | -0.0049 | -0.0085 |
| fundamental | val_neutral | -0.0461 | -0.0444 | -0.0016 |
| fundamental | val_strong | +0.3040 | +0.3162 | -0.0122 |
| fundamental_early | (Intercept) | -0.9536 | -0.9860 | +0.0324 |
| fundamental_early | analyst_rate4 | +0.0912 | +0.0826 | +0.0086 |
| fundamental_early | analysts_n | +0.0086 | +0.0159 | -0.0073 |
| fundamental_early | avg_count | +0.9122 | +0.9317 | -0.0195 |
| fundamental_early | corpus_rare | +0.0112 | -0.0316 | +0.0428 |
| fundamental_early | corpus_spike_z | +0.1791 | +0.1799 | -0.0009 |
| fundamental_early | ext | -0.0600 | -0.0574 | -0.0026 |
| fundamental_early | has_peer | +0.1695 | +0.1265 | +0.0430 |
| fundamental_early | has_yoy | -0.2180 | -0.1558 | -0.0622 |
| fundamental_early | inc | +0.4139 | +0.4229 | -0.0089 |
| fundamental_early | multi | -2.0110 | -2.0637 | +0.0526 |
| fundamental_early | no_hist | +1.4929 | +1.5810 | -0.0880 |
| fundamental_early | peer_rate | +0.0950 | +0.0916 | +0.0034 |
| fundamental_early | politics | -0.3080 | -0.3157 | +0.0077 |
| fundamental_early | r4 | +0.0556 | +0.0367 | +0.0189 |
| fundamental_early | said_prev | +0.6652 | +0.6570 | +0.0082 |
| fundamental_early | said_yoy | +0.1679 | +0.1868 | -0.0188 |
| fundamental_early | story0 | -0.4087 | -0.4438 | +0.0351 |
| fundamental_early | val | -0.0180 | -0.0108 | -0.0072 |
| fundamental_early | val_neutral | -0.0500 | -0.0485 | -0.0015 |
| fundamental_early | val_strong | +0.3499 | +0.3608 | -0.0109 |
