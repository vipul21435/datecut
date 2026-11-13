## LiveCodeBench code generation, split at 2024-06-30

28 systems, 553 items before and 502 after the split.

| quantity (min / median / max over systems) | value | intervals excluding 0 |
| --- | --- | --- |
| plain gap, points | -39.2 / -20.1 / -5.6 | 28 of 28 |
| adjusted gap, points | -21.6 / +0.4 / +7.6 | 7 of 28 |
| difference in differences, points | -19.5 / +0.3 / +15.3 | 14 of 28 |
| share of the plain gap removed, % | +45 / +102 / +236 | |

The adjusted gap is smaller in size than the plain gap for 27 of 28 systems; 5 of 28 adjusted gaps have a BH-adjusted p below 0.05.

Gaps in percentage points, after minus before. `removed %` is the share of the plain gap that the difficulty adjustment removes.

| system | cutoff | n before | n after | plain gap | interval | adjusted gap | interval | diff in diff | interval | removed % | p (adjusted) | p (BH) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude-3-Haiku | 2024-06-30 | 553 | 502 | -5.6 | -10.6 to -0.5 | +7.6 | +3.9 to +11.2 | +15.3 | +10.5 to +19.6 | 236 | <0.0001 | 0.0012 |
| Claude-3.5-Sonnet-20241022 | 2024-06-30 | 553 | 502 | -23.6 | -29.3 to -17.7 | -2.4 | -6.1 to +1.3 | -3.4 | -7.5 to +0.8 | 90 | 0.1976 | 0.3688 |
| Claude-Opus-4 | 2024-06-30 | 553 | 502 | -26.6 | -32.2 to -20.9 | -2.0 | -5.8 to +1.8 | -6.5 | -10.5 to -2.6 | 93 | 0.2970 | 0.4523 |
| Claude-Opus-4 (Thinking) | 2024-06-30 | 553 | 502 | -23.0 | -28.3 to -17.5 | +2.4 | -0.8 to +5.6 | -2.7 | -6.1 to +0.6 | 110 | 0.1533 | 0.3067 |
| Claude-Sonnet-4 | 2024-06-30 | 553 | 502 | -21.0 | -26.7 to -15.1 | +3.4 | -0.5 to +7.2 | -0.7 | -4.7 to +3.5 | 116 | 0.0977 | 0.2279 |
| Claude-Sonnet-4 (Thinking) | 2024-06-30 | 553 | 502 | -22.1 | -27.5 to -16.5 | +3.4 | -0.0 to +6.7 | -1.8 | -5.3 to +1.8 | 115 | 0.0579 | 0.1848 |
| DeepSeek-R1-0528 | 2024-06-30 | 553 | 502 | -20.0 | -24.3 to -15.7 | -4.2 | -6.5 to -1.9 | +0.4 | -2.0 to +2.5 | 79 | 0.0002 | 0.0016 |
| DeepSeek-V3 | 2024-06-30 | 553 | 502 | -39.2 | -44.5 to -33.4 | -21.6 | -26.0 to -17.1 | -19.5 | -23.3 to -15.2 | 45 | <0.0001 | <0.0001 |
| EXAONE-4.0-32B | 2024-06-30 | 553 | 502 | -19.9 | -24.5 to -15.1 | +0.2 | -1.8 to +2.3 | +0.5 | -1.6 to +2.8 | 101 | 0.8341 | 0.8982 |
| GPT-4-Turbo-2024-04-09 | 2024-06-30 | 553 | 502 | -15.6 | -21.2 to -9.7 | +3.1 | +0.0 to +6.1 | +5.0 | +0.6 to +9.1 | 120 | 0.0500 | 0.1848 |
| GPT-4O-2024-08-06 | 2024-06-30 | 553 | 502 | -16.0 | -21.6 to -10.1 | +3.0 | -0.2 to +6.1 | +4.6 | +0.6 to +8.7 | 119 | 0.0689 | 0.1848 |
| GPT-4O-mini-2024-07-18 | 2024-06-30 | 553 | 502 | -15.3 | -20.9 to -9.6 | +2.5 | -0.7 to +5.7 | +5.2 | +0.9 to +9.5 | 116 | 0.1227 | 0.2642 |
| Gemini-2.5-Flash-04-17 | 2024-06-30 | 553 | 502 | -25.0 | -30.0 to -19.9 | -3.4 | -7.0 to +0.2 | -4.8 | -8.4 to -1.3 | 86 | 0.0624 | 0.1848 |
| Gemini-2.5-Flash-05-20 | 2024-06-30 | 553 | 502 | -24.2 | -29.1 to -19.1 | -1.6 | -4.9 to +1.7 | -3.9 | -7.2 to -0.8 | 93 | 0.3406 | 0.4768 |
| Gemini-2.5-Pro-05-06 | 2024-06-30 | 553 | 502 | -18.4 | -22.9 to -13.9 | +0.8 | -2.1 to +3.6 | +2.0 | -0.9 to +5.0 | 104 | 0.6104 | 0.7121 |
| Gemini-2.5-Pro-06-05 | 2024-06-30 | 553 | 502 | -18.6 | -23.0 to -14.3 | -1.5 | -4.4 to +1.4 | +1.8 | -1.3 to +4.9 | 92 | 0.3069 | 0.4523 |
| Grok-3-Mini (High) | 2024-06-30 | 553 | 502 | -19.4 | -24.3 to -14.4 | -3.9 | -8.1 to +0.4 | +1.0 | -3.2 to +4.9 | 80 | 0.0726 | 0.1848 |
| O3 (High) | 2024-06-30 | 553 | 502 | -16.5 | -20.8 to -12.2 | -1.8 | -5.1 to +1.6 | +4.0 | +0.6 to +7.4 | 89 | 0.3055 | 0.4523 |
| O3-Mini-2025-01-31 (High) | 2024-06-30 | 553 | 502 | -16.8 | -21.7 to -11.8 | +4.1 | +0.7 to +7.5 | +3.7 | +0.3 to +7.1 | 124 | 0.0244 | 0.1138 |
| O3-Mini-2025-01-31 (Low) | 2024-06-30 | 553 | 502 | -23.0 | -28.3 to -17.5 | +0.6 | -3.0 to +4.3 | -2.7 | -6.4 to +0.8 | 103 | 0.7296 | 0.8171 |
| O3-Mini-2025-01-31 (Med) | 2024-06-30 | 553 | 502 | -21.0 | -26.1 to -15.8 | +1.1 | -2.4 to +4.6 | -0.7 | -4.2 to +2.8 | 105 | 0.5473 | 0.6663 |
| O4-Mini (High) | 2024-06-30 | 553 | 502 | -11.9 | -16.0 to -7.9 | +1.8 | -1.3 to +4.9 | +8.8 | +5.4 to +12.4 | 115 | 0.2686 | 0.4523 |
| O4-Mini (Low) | 2024-06-30 | 553 | 502 | -20.4 | -25.4 to -15.4 | +1.1 | -2.2 to +4.5 | -0.1 | -3.4 to +3.4 | 106 | 0.5035 | 0.6663 |
| O4-Mini (Medium) | 2024-06-30 | 553 | 502 | -17.1 | -21.5 to -12.7 | -0.0 | -2.9 to +2.9 | +3.4 | +0.4 to +6.5 | 100 | 0.9998 | 0.9998 |
| OpenCodeReasoning-Nemotron-1.1-32B | 2024-06-30 | 553 | 502 | -20.2 | -25.0 to -15.2 | +0.6 | -1.2 to +2.4 | +0.2 | -2.0 to +2.3 | 103 | 0.5392 | 0.6663 |
| OpenReasoning-Nemotron-32B | 2024-06-30 | 553 | 502 | -19.5 | -24.2 to -14.8 | -0.0 | -1.8 to +1.8 | +0.9 | -1.3 to +3.0 | 100 | 0.9961 | 0.9998 |
| Qwen3-235B-A22B | 2024-06-30 | 553 | 502 | -24.5 | -29.2 to -19.8 | -4.6 | -7.7 to -1.5 | -4.3 | -7.3 to -1.0 | 81 | 0.0035 | 0.0194 |
| XBai-o4-medium | 2024-06-30 | 553 | 502 | -25.9 | -30.5 to -21.2 | -5.7 | -8.7 to -2.7 | -5.7 | -8.8 to -2.7 | 78 | 0.0003 | 0.0019 |

## LiveCodeBench cutoff scan, month-end candidates

Permutation band for the largest |z|: 2.66 to 2.95 across systems (a single pre-chosen date would use 1.96). The largest |z| is outside the band for 11 of 28 systems, and for 9 after the Benjamini-Hochberg adjustment across systems.

Scan statistic: largest |z| of the after-date term over the candidate dates; 1000 permutations of item dates across all items, seed 0.

| system | items | candidate dates | best date | largest \|z\| | 95 % permutation band | p (maximum) | p (BH) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude-3-Haiku | 1055 | 22 | 2024-10-31 | 5.71 | 2.81 | 0.0010 | 0.0056 |
| Claude-3.5-Sonnet-20241022 | 1055 | 22 | 2024-03-31 | 4.03 | 2.80 | 0.0010 | 0.0056 |
| Claude-Opus-4 | 1055 | 22 | 2024-12-31 | 2.66 | 2.77 | 0.0729 | 0.1571 |
| Claude-Opus-4 (Thinking) | 1055 | 22 | 2024-10-31 | 2.03 | 2.83 | 0.3516 | 0.5448 |
| Claude-Sonnet-4 | 1055 | 22 | 2024-03-31 | 2.64 | 2.77 | 0.0649 | 0.1515 |
| Claude-Sonnet-4 (Thinking) | 1055 | 22 | 2024-07-31 | 2.06 | 2.80 | 0.3087 | 0.5402 |
| DeepSeek-R1-0528 | 1055 | 22 | 2024-05-31 | 3.90 | 2.80 | 0.0010 | 0.0056 |
| DeepSeek-V3 | 1055 | 22 | 2024-06-30 | 9.12 | 2.75 | 0.0010 | 0.0056 |
| EXAONE-4.0-32B | 1055 | 22 | 2024-07-31 | 1.67 | 2.87 | 0.5524 | 0.7031 |
| GPT-4-Turbo-2024-04-09 | 1055 | 22 | 2023-10-31 | 3.50 | 2.79 | 0.0080 | 0.0320 |
| GPT-4O-2024-08-06 | 1055 | 22 | 2023-09-30 | 2.85 | 2.81 | 0.0430 | 0.1093 |
| GPT-4O-mini-2024-07-18 | 1055 | 22 | 2024-10-31 | 2.82 | 2.66 | 0.0310 | 0.0867 |
| Gemini-2.5-Flash-04-17 | 1055 | 22 | 2023-10-31 | 3.31 | 2.77 | 0.0100 | 0.0350 |
| Gemini-2.5-Flash-05-20 | 1055 | 22 | 2025-02-28 | 1.54 | 2.87 | 0.6563 | 0.7657 |
| Gemini-2.5-Pro-05-06 | 1055 | 22 | 2023-06-30 | 1.50 | 2.95 | 0.7143 | 0.8000 |
| Gemini-2.5-Pro-06-05 | 1055 | 22 | 2024-01-31 | 1.95 | 2.88 | 0.4076 | 0.5448 |
| Grok-3-Mini (High) | 1055 | 22 | 2024-07-31 | 1.92 | 2.85 | 0.4086 | 0.5448 |
| O3 (High) | 1055 | 22 | 2024-08-31 | 1.30 | 2.85 | 0.8521 | 0.9177 |
| O3-Mini-2025-01-31 (High) | 1055 | 22 | 2023-10-31 | 3.33 | 2.83 | 0.0140 | 0.0435 |
| O3-Mini-2025-01-31 (Low) | 1055 | 22 | 2024-02-29 | 2.22 | 2.87 | 0.2318 | 0.4635 |
| O3-Mini-2025-01-31 (Med) | 1055 | 22 | 2024-10-31 | 1.96 | 2.80 | 0.3706 | 0.5448 |
| O4-Mini (High) | 1055 | 22 | 2024-06-30 | 1.11 | 2.77 | 0.9131 | 0.9469 |
| O4-Mini (Low) | 1055 | 22 | 2025-02-28 | 1.56 | 2.79 | 0.6224 | 0.7577 |
| O4-Mini (Medium) | 1055 | 22 | 2023-05-31 | 0.99 | 2.85 | 0.9590 | 0.9590 |
| OpenCodeReasoning-Nemotron-1.1-32B | 1055 | 22 | 2023-06-30 | 1.91 | 2.81 | 0.3946 | 0.5448 |
| OpenReasoning-Nemotron-32B | 1055 | 22 | 2023-06-30 | 2.10 | 2.86 | 0.3077 | 0.5402 |
| Qwen3-235B-A22B | 1055 | 22 | 2024-10-31 | 4.16 | 2.77 | 0.0010 | 0.0056 |
| XBai-o4-medium | 1055 | 22 | 2024-09-30 | 3.95 | 2.84 | 0.0020 | 0.0093 |

## LiveCodeBench power at the split

Smallest drop detectable at 80 % power (min / median / max over systems): 4.8 / 6.3 / 8.6 points.

## SWE-bench Verified, issues created after against before 2020-12-31

135 submissions, 254 items before and 246 after; 9 repositories have items on both sides.

| quantity (min / median / max over submissions) | value | intervals excluding the null |
| --- | --- | --- |
| plain gap, points | -24.5 / -5.5 / +3.4 | 30 of 135 |
| crude odds ratio | 0.28 / 0.77 / 1.15 | |
| Mantel-Haenszel odds ratio across repositories | 0.38 / 0.90 / 2.24 | 4 of 135 |

Homogeneity test p below 0.05 for 20 of 135 submissions.

## SWE-bench Verified trend, rolling windows of 100 issues

The system shown is the submission with the most resolved instances (first by name among ties); the pool is every other submission.

### 20251205_sonar-foundation-agent_claude-opus-4-5

| from | to | n | 20251205_sonar-foundation-agent_claude-opus-4-5 % | band | pool % | band | system - pool | band |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2013-01-25 | 2019-06-21 | 100 | 78.0 | 68.9 to 85.0 | 56.0 | 49.9 to 62.0 | +22.0 | +15.4 to +28.6 |
| 2019-01-21 | 2020-01-05 | 100 | 84.0 | 75.6 to 89.9 | 55.4 | 49.0 to 61.7 | +28.6 | +22.3 to +34.9 |
| 2019-06-25 | 2020-07-19 | 100 | 85.0 | 76.7 to 90.7 | 51.5 | 45.7 to 57.3 | +33.5 | +27.7 to +39.3 |
| 2020-01-09 | 2020-12-27 | 100 | 83.0 | 74.5 to 89.1 | 51.6 | 46.1 to 57.1 | +31.4 | +25.9 to +36.9 |
| 2020-07-20 | 2021-06-26 | 100 | 82.0 | 73.3 to 88.3 | 50.8 | 44.6 to 57.0 | +31.2 | +25.2 to +37.3 |
| 2020-12-27 | 2022-01-31 | 100 | 76.0 | 66.8 to 83.3 | 48.2 | 41.7 to 54.8 | +27.8 | +21.0 to +34.5 |
| 2021-07-01 | 2022-07-23 | 100 | 73.0 | 63.6 to 80.7 | 48.5 | 42.1 to 54.9 | +24.5 | +18.1 to +30.9 |
| 2022-02-01 | 2023-01-21 | 100 | 78.0 | 68.9 to 85.0 | 49.5 | 43.2 to 55.9 | +28.5 | +22.1 to +34.8 |
| 2022-08-04 | 2023-08-07 | 100 | 78.0 | 68.9 to 85.0 | 50.3 | 43.7 to 56.9 | +27.7 | +21.6 to +33.8 |
