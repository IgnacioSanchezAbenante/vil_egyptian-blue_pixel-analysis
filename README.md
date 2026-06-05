# Egyptian Blue VIL Analysis — Comparative Repository

Reproducible image-processing workflows and figures for the M.Sc. thesis:

> **Egyptian Blue detection using Visible-Induced Luminescence (VIL)**  
> Ignacio Sánchez Abenante  
> Conservation and Restoration of Cultural Heritage, University of Amsterdam, 2026

---

## Repository structure

```
thesis_comparative-analysis_repository/
├── SRApapyrus_2/               # Experiment SRA: papyrus support
│   ├── *.tif                   # Raw VIL swatch images (before and after ageing)
│   ├── VILanalysis_auto.mo.py  # Analysis notebook (marimo)
│   ├── vil_outputs_figures/    # Generated figures (PDF / PNG / SVG)
│   └── vil_outputs_tables/     # Generated tables (CSV / TXT)
├── SRBpaper_2/                 # Experiment SRB: paper support
│   ├── *.tif
│   ├── VILanalysis_auto.mo.py
│   ├── vil_outputs_figures/
│   └── vil_outputs_tables/
├── README.md
├── CITATION.cff
├── requirements.txt
└── .gitignore
```

---

## Analysis overview

`VILanalysis_auto.mo.py` is a [marimo](https://marimo.io) reactive notebook. It processes VIL swatch images in the same directory and produces:

| Output | Description |
|---|---|
| `vil_stats-results_table.csv` | Per-swatch metrics (mean, std, normalised signal, skewness, …) |
| `vil_luminescence_overview.csv/.txt` | Group-level signal summary |
| `vil_ageing_comparison.csv` | Before/after ageing Δ values per swatch |
| `vil_ageing_swatch_summary.csv` | Δmean and Δmedian per swatch pair |
| `vil_images_panel_masked_ctrlcompare.pdf/.png/.svg` | Swatch image panel vs control |
| `vil_kdecurves_all.pdf/.png` | KDE intensity distributions (all swatches) |
| `vil_comparison_bar.pdf/.png` | Normalised VIL signal bar chart |
| `vil_ageing_comparison.pdf/.png` | Before/after ageing bar chart |
| `vil_ageing_jointplot_grouped.pdf/.png` | Joint density plot by variable group |

### Swatch groups

| Group | Abbreviation prefix | Description |
|---|---|---|
| Pigment | `P`, `G` | Egyptian Blue pigment formulations |
| Mixture | `M.ORP`, `M.CAR`, `M.ASH` | Egyptian Blue mixed with orpiment, carbon, or ash at 1:9, 1:1, 9:1 ratios |
| Stratigraphy | `S.CAR`, `S.FEO`, `S.ORP` | Egyptian Blue with carbon, iron oxide, or orpiment overlay |
| Alteration | `A.01`, `A.02` | Egyptian Blue with animal glue / consolidant |

### Key methodological choices

- **Raw pixel values throughout** — no normalisation at load time. 8-bit RGB → red channel (0–255); 16-bit grayscale → single channel (0–65 535).
- **Z-score outlier masking** — pixels with |Z| > 2.0 σ (configurable via `ZSCORE_THRESHOLD`) are excluded per image to remove flakes, gaps, and sensor artefacts without applying a cross-swatch threshold.
- **No Otsu threshold** — using all valid pixels ensures every swatch is fully represented and directly comparable regardless of brightness.
- **Normalised signal** — swatch mean ÷ control mean × 100 %. The control swatch is `P.00` (Egyptian Blue, Haematite–Azurite, unaged).

---

## Requirements

- Python ≥ 3.11, < 3.13
- See [`requirements.txt`](requirements.txt)

---

## How to run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run interactively (reactive notebook):

```bash
cd SRApapyrus_2
marimo run VILanalysis_auto.mo.py
```

Run headless (saves all outputs silently):

```bash
cd SRApapyrus_2
python VILanalysis_auto.mo.py
```

Repeat for `SRBpaper_2/`.

---

## Configuration

All user-configurable parameters are in the first code cell of each notebook:

| Parameter | Purpose |
|---|---|
| `IMAGE_DIR` | Path to swatch TIFF files |
| `CONTROL_ID` | ID of the control swatch (`P.00`) |
| `CHANNEL` | Image channel (`0` = red, `None` = grayscale) |
| `HIST_XLIM` | x-axis range for KDE plots (raw pixel units) |
| `ZSCORE_THRESHOLD` | Outlier masking threshold (default `2.0`) |
| `SWATCH_REGISTRY` | List of swatches with id, filename, label, group |
| `AGEING_PAIRS` | Paired unaged/aged TIFF filenames |

---

## Citation

If you use this code, please cite using [`CITATION.cff`](CITATION.cff) or the metadata below.

---

## License

This repository is shared for scientific reproducibility.  
Contact the author for reuse beyond personal research.
