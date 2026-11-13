# Changelog

## 0.1.0 - 2026-11-13

First release.

- `datecut gap`: success before and after a cutoff, Newcombe hybrid score interval for the
  difference, counts on each side, refusal below `--min-side`
- `datecut strata`: Mantel-Haenszel common odds ratio with the Robins-Breslow-Greenland
  interval, the Cochran-Mantel-Haenszel test and a homogeneity test with Tarone's correction
- `datecut did`: difference in differences against the pool of other systems, bootstrap
  over items or over whole strata
- `datecut adjust`: logistic model with a leave-one-system-out difficulty covariate,
  fitted by iteratively reweighted least squares, with the adjusted gap on the
  probability scale
- `datecut scan`: adjusted gap over candidate dates with a permutation band for the
  maximum
- `datecut trend`, `datecut power`, `datecut summary`
- Benjamini-Hochberg adjusted p-values across systems; Markdown and JSON output
- Fetch scripts and a report script for LiveCodeBench and SWE-bench Verified public results
