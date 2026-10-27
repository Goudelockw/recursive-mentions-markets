-- Variable strength and release reviews.
--   se / p_value / sd: each term's standard error, p-value and spread in the rows it was fitted on,
--   so the Models page can show how strong each variable is and what it does to the odds.
--   review: the comparison against the live model made when the version was created (rmm review).
--   risk_rules: the risk model (avoid_point_rules + their tests) in force when the version was reviewed.
alter table kalshi.model_version_coefficients add column se numeric, add column p_value numeric, add column sd numeric;
alter table kalshi.model_versions add column review jsonb, add column risk_rules jsonb;
