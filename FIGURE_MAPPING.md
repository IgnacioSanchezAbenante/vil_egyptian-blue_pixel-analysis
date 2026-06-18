# Figure and Table Mapping

This document maps each numbered figure and table in the thesis to its input data,
processing script, and output file, so that any result can be reproduced from scratch.

The same analysis pipeline runs for two experiments:

| Experiment | Directory | Support material |
|---|---|---|
| SRA | `SRApapyrus_2/` | Papyrus |
| SRB | `SRBpaper_2/` | Paper |

Both directories contain an identical script (`VILanalysis_auto.mo.py`).
All output paths below are **relative to the experiment directory**.

---

## How to reproduce

```bash
# Example: reproduce all SRA outputs
cd SRApapyrus_2
python VILanalysis_auto.mo.py      # headless, saves all figures and tables
# or
marimo run VILanalysis_auto.mo.py  # interactive
```

Repeat for `SRBpaper_2/`.

---

## Figures

### Figure 1 — Swatch image panel: control comparison

**Script cell:** `## 2./ FIGURE 1 — SWATCH IMAGE PANEL: CONTROL COMPARISON`

**Input data:**
- All swatch TIFFs listed in `SWATCH_REGISTRY` (e.g. `P00_control.tif`, `MORP01.tif`, …)
- Red channel (channel 0) extracted from 8-bit RGB TIFFs
- Z-score outlier mask applied per image (`ZSCORE_THRESHOLD = 2.0`)
- Global colour scale derived from the combined valid-pixel range across all swatches

**Output — combined panel:**
```
vil_outputs_figures/vil_images_panel_masked_ctrlcompare.pdf
vil_outputs_figures/vil_images_panel_masked_ctrlcompare.png
vil_outputs_figures/vil_images_panel_masked_ctrlcompare.svg   ← for Inkscape editing
```

**Output — individual control+swatch pairs (supplementary):**
```
vil_outputs_figures/vil_image/vil_image_{id}_ctrlcompare.pdf
vil_outputs_figures/vil_image/vil_image_{id}_ctrlcompare.png
```
One file per swatch (e.g. `vil_image_M.ORP.01_ctrlcompare.pdf`).

---

### Figure 2 — KDE intensity distributions (all swatches)

**Script cell:** `## 3./ FIGURE 2 — KDE INTENSITY DISTRIBUTIONS CURVE`

**Input data:**
- All swatch TIFFs in `SWATCH_REGISTRY`
- Red channel, Z-score masked (`ZSCORE_THRESHOLD = 2.0`)
- x-axis range: `HIST_XLIM = (0, 255)` (raw pixel units)
- Control distribution (`P00_control.tif`) shown as grey reference in every panel
- Group colour palette: Pigment `#4A90D9`, Mixture `#E07B3F`, Stratigraphy `#5BAD72`, Alteration `#9B6BB5`

**Output — combined panel:**
```
vil_outputs_figures/vil_kdecurves_all.pdf
vil_outputs_figures/vil_kdecurves_all.png
```

**Output — individual per-swatch KDE curves (supplementary):**
```
vil_outputs_figures/vil_kdecurve/vil_kdecurve_{id}.pdf
vil_outputs_figures/vil_kdecurve/vil_kdecurve_{id}.png
```
One file per swatch (e.g. `vil_kdecurve_M.ORP.01.pdf`).

---

### Figure 3 — Normalised VIL signal by swatch (bar chart)

**Script cell:** `## 4./ FIGURE 3 — NORMALISED VIL SIGNAL BY SWATCH (bar chart)`

**Input data:**
- `df` computed from all swatch TIFFs (see Table 1 below)
- Normalised signal = swatch mean ÷ control mean (`P.00`) × 100 %
- Error bars = ±1 σ of the pixel distribution within each swatch, converted to % of control mean
- Control baseline drawn at 100 %

**Output:**
```
vil_outputs_figures/vil_comparison_bar.pdf
vil_outputs_figures/vil_comparison_bar.png
```

---

### Figure 4 — Before/after ageing comparison (bar chart)

**Script cell:** `## 6./ FIGURE 4 - BEFORE/AFTER AGEING COMPARISON (bar chart)`

**Input data:**
- Paired TIFFs from `AGEING_PAIRS`: each swatch has an unaged file (e.g. `MORP01.tif`) and an aged file (e.g. `MORP01_aged.tif`)
- Same Z-score masking and channel as the main analysis
- Δ = aged normalised signal − unaged normalised signal (percentage points)

**Output — figure:**
```
vil_outputs_figures/vil_ageing_comparison.pdf
vil_outputs_figures/vil_ageing_comparison.png
```

**Output — data table (see also Table 3 below):**
```
vil_outputs_tables/vil_ageing_comparison.csv
```

---

### Figure 5 — Before/after ageing: joint density plot by variable group

**Script cell:** `## 7./ FIGURE 5 + TABLE 3 - BEFORE/AFTER AGEING: REGISTERED SWATCH DENSITY JOINTPLOT`

**Input data:**
- Same paired TIFFs as Figure 4 (`AGEING_PAIRS`)
- Pixel pairs are spatially registered (pixel (i,j) unaged ↔ pixel (i,j) aged)
- Combined Z-score mask: pixels outlying in *either* timepoint are excluded
- 60 000 pixel pairs total, shared evenly across all pairs (`_BUDGET = 60_000`, `seed = 42`)
- x-axis = unaged pixel value; y-axis = aged pixel value; diagonal y = x = no change
- Coloured by variable group using `GROUP_COLOURS`

**Output — combined panel (all groups):**
```
vil_outputs_figures/vil_ageing_jointplot_grouped.pdf
vil_outputs_figures/vil_ageing_jointplot_grouped.png
```

**Output — individual per-group jointplots (supplementary):**
```
vil_outputs_figures/vil_before-after_jointplot/vil_before-after_jointplot_pigment.pdf
vil_outputs_figures/vil_before-after_jointplot/vil_before-after_jointplot_mixture.pdf
vil_outputs_figures/vil_before-after_jointplot/vil_before-after_jointplot_stratigraphy.pdf
vil_outputs_figures/vil_before-after_jointplot/vil_before-after_jointplot_alteration.pdf
```
(`.png` counterparts for each.)

---

### Figure 6 — Before/after ageing: joint density plot per swatch (individual colours)

**Script cell:** `## 7.1./ FIGURE 6 - BEFORE/AFTER AGEING: REGISTERED SWATCH DENSITY JOINTPLOT (individual subgroup separated)`

**Input data:**
- Same pixel-pair dataset as Figure 5 (no additional computation)
- Each swatch label assigned a unique colour (`sns.color_palette("tab10")`)

**Output — combined panel (all swatches):**
```
vil_outputs_figures/vil_ageing_jointplot_perswatch.pdf
vil_outputs_figures/vil_ageing_jointplot_perswatch.png
```

**Output — individual per-group jointplots with per-swatch colours (supplementary):**
```
vil_outputs_figures/vil_before-after_jointplot/vil_before-after_jointplot_pigment_perswatch.pdf
vil_outputs_figures/vil_before-after_jointplot/vil_before-after_jointplot_mixture_perswatch.pdf
vil_outputs_figures/vil_before-after_jointplot/vil_before-after_jointplot_stratigraphy_perswatch.pdf
vil_outputs_figures/vil_before-after_jointplot/vil_before-after_jointplot_alteration_perswatch.pdf
```
(`.png` counterparts for each.)

---

## Tables

### Table 1 — Full per-swatch statistics

**Script cell:** `## 1.1/ TABLE 1 — FULL STATISTICS RESULTS (print + CSV)`

**Input data:**
- All swatch TIFFs in `SWATCH_REGISTRY`
- Red channel, Z-score masked; metrics computed on valid (non-masked) pixels only

**Columns:** `id`, `group`, `label`, `normalised_signal_pct`, `area_fraction_pct`, `mean_raw`, `median_raw`, `std_raw`, `p10`, `p90`, `skewness`, `cv`, `n_pixels`, `n_masked`, `pct_masked`, `file_found`

**Output:**
```
vil_outputs_tables/vil_stats-results_table.csv
```

---

### Table 2 — Group-level luminescence summary

**Script cell:** `## 5./ TABLE 2 SUMMARY OF ANALYSES PER VARIABLE GROUP (print)`

**Input data:**
- `df` from Table 1 (same run)
- Groups: Pigment, Mixture, Stratigraphy, Alteration

**Columns:** `group`, `control_id`, `min_signal_pct`, `max_signal_pct`, `greatest_attenuation_label`, `greatest_attenuation_pct`

**Output:**
```
vil_outputs_tables/vil_luminescence_overview.csv
vil_outputs_tables/vil_luminescence_overview.txt   ← human-readable version
```

---

### Table 3 — Per-swatch ageing delta summary

**Script cell:** `## 7./ FIGURE 5 + TABLE 3 ...` (saved at end of the Figure 5 cell)

**Input data:**
- Same paired pixel data as Figure 5
- Δmean and Δmedian computed from the subsampled pixel-pair DataFrame

**Columns:** `id`, `label`, `group`, `n_pairs`, `mean_unaged`, `mean_aged`, `delta_mean`, `median_unaged`, `median_aged`, `delta_median`

**Output:**
```
vil_outputs_tables/vil_ageing_swatch_summary.csv
```

---

## Reproducibility notes

- **Pixel values are never normalised** at load time. All metrics and figures use raw 8-bit red-channel values (0–255).
- **Z-score masking is per-image** (`ZSCORE_THRESHOLD = 2.0`). Changing this value will alter all figures and tables.
- **Figure 5 and Figure 6 use a fixed random seed** (`seed = 42`) for subsampling pixel pairs. Results are exactly reproducible with the same seed.
- **Both experiments use the same script.** `diff SRApapyrus_2/VILanalysis_auto.mo.py SRBpaper_2/VILanalysis_auto.mo.py` returns no meaningful difference.
- **marimo version:** the script was generated with marimo `0.23.3` (`__generated_with = "0.23.3"`). Use `marimo>=0.23` as specified in `requirements.txt`.
