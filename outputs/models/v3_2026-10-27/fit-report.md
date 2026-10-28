# Model fit · v3

Trained through **2026-10-27** on 6,288 settled markets from `kalshi.v_model_training`. Python port of `refit_models.R` (`rmm/refit.py`). This is a challenger: nothing was written to the database.

## Walk-forward backtest

Each month scored by models trained only on earlier months; k learned the same way.

| Stage | Months | Markets | Brier model | Brier price | Model − price | k (all months) |
|---|--:|--:|--:|--:|--:|--:|
| call_start | 12 | 5,136 | 0.1585 | 0.1618 | -0.0033 | 0.675 |
| early_24h | 12 | 4,920 | 0.1672 | 0.1717 | -0.0045 | 0.772 |

## Coefficients

Compared with the live coefficients in `kalshi.model_coefficients`.

| Model | Term | New | Live | Change |
|---|---|--:|--:|--:|
| combined | (Intercept) | -0.0401 | -0.0607 | +0.0207 |
| combined | calibration_k | +0.6750 | +0.6690 | +0.0060 |
| combined | filing_said | +0.3665 | +0.2916 | +0.0749 |
| combined | has24 | -0.4162 | -0.4196 | +0.0034 |
| combined | inc | +0.1650 | +0.1901 | -0.0251 |
| combined | lA | +0.2055 | +0.1846 | +0.0209 |
| combined | lp | +0.9112 | +0.9177 | -0.0065 |
| combined | move24 | -0.1851 | -0.1925 | +0.0074 |
| combined_early | (Intercept) | -0.4129 | -0.4335 | +0.0207 |
| combined_early | calibration_k | +0.7720 | +0.7580 | +0.0140 |
| combined_early | inc | +0.1815 | +0.1983 | -0.0168 |
| combined_early | lA | +0.3034 | +0.2955 | +0.0079 |
| combined_early | lp24 | +0.8504 | +0.8438 | +0.0066 |
| fundamental | (Intercept) | -1.2744 | -0.9505 | -0.3239 |
| fundamental | analyst_rate4 | +0.1035 | +0.1077 | -0.0042 |
| fundamental | analysts_n | +0.0000 | +0.0137 | -0.0137 |
| fundamental | avg_count | +1.0283 | +0.8261 | +0.2022 |
| fundamental | corpus_rare | +0.0000 | +0.0249 | -0.0249 |
| fundamental | corpus_spike_z | +0.1656 | +0.1778 | -0.0122 |
| fundamental | ext | +0.0000 | -0.0266 | +0.0266 |
| fundamental | filing_said | +0.0000 | +0.5965 | -0.5965 |
| fundamental | has_peer | +0.1732 | +0.1377 | +0.0355 |
| fundamental | has_yoy | +0.0000 | -0.2573 | +0.2573 |
| fundamental | inc | +0.4191 | +0.3954 | +0.0237 |
| fundamental | multi | -2.1283 | -2.3358 | +0.2076 |
| fundamental | no_hist | +1.7450 | +1.4406 | +0.3045 |
| fundamental | peer_rate | +0.0933 | +0.0810 | +0.0123 |
| fundamental | politics | +0.0000 | -0.2681 | +0.2681 |
| fundamental | r4 | +0.0000 | +0.0684 | -0.0684 |
| fundamental | rel_head | +1.3495 | +0.8921 | +0.4574 |
| fundamental | said_prev | +0.7241 | +0.6560 | +0.0681 |
| fundamental | said_yoy | +0.0000 | +0.1814 | -0.1814 |
| fundamental | story0 | -0.3956 | -0.3871 | -0.0085 |
| fundamental | val | -0.0009 | -0.0134 | +0.0125 |
| fundamental | val_neutral | -0.0426 | -0.0461 | +0.0035 |
| fundamental | val_strong | +0.2788 | +0.3040 | -0.0252 |
| fundamental_early | (Intercept) | -1.2793 | -0.9536 | -0.3257 |
| fundamental_early | analyst_rate4 | +0.0957 | +0.0912 | +0.0046 |
| fundamental_early | analysts_n | +0.0000 | +0.0086 | -0.0086 |
| fundamental_early | avg_count | +1.0631 | +0.9122 | +0.1509 |
| fundamental_early | corpus_rare | +0.0000 | +0.0112 | -0.0112 |
| fundamental_early | corpus_spike_z | +0.1690 | +0.1791 | -0.0100 |
| fundamental_early | ext | +0.0000 | -0.0600 | +0.0600 |
| fundamental_early | has_peer | +0.1812 | +0.1695 | +0.0117 |
| fundamental_early | has_yoy | +0.0000 | -0.2180 | +0.2180 |
| fundamental_early | inc | +0.4346 | +0.4139 | +0.0206 |
| fundamental_early | multi | -1.9134 | -2.0110 | +0.0977 |
| fundamental_early | no_hist | +1.7573 | +1.4929 | +0.2644 |
| fundamental_early | peer_rate | +0.0987 | +0.0950 | +0.0038 |
| fundamental_early | politics | +0.0000 | -0.3080 | +0.3080 |
| fundamental_early | r4 | +0.0000 | +0.0556 | -0.0556 |
| fundamental_early | said_prev | +0.7241 | +0.6652 | +0.0589 |
| fundamental_early | said_yoy | +0.0000 | +0.1679 | -0.1679 |
| fundamental_early | story0 | -0.4038 | -0.4087 | +0.0049 |
| fundamental_early | val | +0.0017 | -0.0180 | +0.0198 |
| fundamental_early | val_neutral | -0.0383 | -0.0500 | +0.0117 |
| fundamental_early | val_strong | +0.3296 | +0.3499 | -0.0204 |
