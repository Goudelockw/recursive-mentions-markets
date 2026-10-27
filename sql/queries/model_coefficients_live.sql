-- The live model coefficients, for comparing a refit against. Read-only.
select model, term, coef, trained_through from kalshi.model_coefficients order by model, term;
