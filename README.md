# Egyptian Blue VIL Imaging Comparative Pixel-based Analysis — Repository

A reproducible image-processing pipeline for analysing Visible-Induced Luminescence
(VIL) imaging of Egyptian Blue mockup samples. Produced as part of an M.Sc. thesis
in Conservation and Restoration of Cultural Heritage at the University of Amsterdam.


## Research context

Egyptian Blue (cuprorivaite, CaCuSi4O6) is an ancient synthetic pigment that emits
strong near-infrared luminescence when excited by visible light — a property exploited
in VIL imaging to detect its presence in cultural heritage objects non-invasively.

This project investigates the **detection limits and methodological limitations of VIL
imaging** through controlled mockup samples informed (to a limited extent) by the
Book of the Dead of Qenna. It asks: under what conditions does Egyptian Blue remain
detectable by VIL, and how does the signal change after artificial ageing?



## Thesis summary

**Title:** xx

**Author:** Ignacio Sánchez Abenante

**Programme:** M.Sc. Conservation and Restoration of Cultural Heritage

**Institution:** University of Amsterdam

**Year:** 2026

Two sets of mockup samples were prepared — one on papyrus support (SRA) and one on
paper support (SRB) — containing swatches representing: different pigment formulations,
mixtures with attenuating materials (orpiment, carbon, ash) at varying concentration
ratios, stratigraphic overlays (carbon, iron oxide, orpiment), and alterations (animal
glue, consolidants). All swatches were imaged by VIL before and after artificial ageing.
The pipeline quantifies the luminescence signal of each swatch relative to a reference
control and produces comparative statistics and figures used in the thesis.



## Repository structure

```
thesis_comparative-analysis_repository/
├── SRApapyrus_2/                    — dataset SRA (papyrus support)
│   ├── *.tif                        - Raw VIL swatch images, before and after ageing (input TIFF files)
│   ├── VILanalysis_auto.mo.py       — Marimo analysis notebook
│   ├── vil_outputs_figures/         — generated figures (PDF, PNG, SVG)
│   └── vil_outputs_tables/          — generated tables (CSV, TXT)
├── SRBpaper_2/                      — dataset SRB (paper support)
│   ├── *.tif
│   ├── VILanalysis_auto.mo.py
│   ├── vil_outputs_figures/
│   └── vil_outputs_tables/
├── README.md                       — this file
├── CITATION.cff                    — machine-readable citation metadata
├── requirements.txt                — Python dependencies
├── TRANSPARENCY.md                 — AI and coding-assistance statement
├── LICENSE                         — MIT (code); data note included
└── .gitignore
```


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
| Pigment | `P.00`,`P.01`, `G.01` | Egyptian Blue sources: F5EG2* (P.00 = control), F5EG2 finer (G.01) and Kremer pigmente (P.01) |
| Mixture | `M.ORP`, `M.CAR`, `M.ASH` | Egyptian Blue mixed with orpiment, carbon, or ash at 1:9, 1:1, 9:1 ratios |
| Stratigraphy | `S.CAR`, `S.FEO`, `S.ORP` | Egyptian Blue with carbon, iron oxide, or orpiment overlay |
| Alteration | `A.01`, `A.02` | Egyptian Blue with animal glue / + gampi japanese paper |

***add info about artist-researchers if they agree** 


## Requirements

- Python ≥ 3.11, < 3.13
- See [`requirements.txt`](requirements.txt)



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


### Key methodological choices

- **Raw pixel values throughout** — no normalisation at load time. 8-bit RGB → red channel (0–255); 16-bit grayscale → single channel (0–65 535).
- **Z-score outlier masking** — pixels with |Z| > 2.0 σ (configurable via `ZSCORE_THRESHOLD`) are excluded per image to remove flakes, gaps, and sensor artefacts without applying a cross-swatch threshold.
- **Normalised signal** — swatch mean ÷ control mean × 100 %. The control swatch is `P.00` (Egyptian Blue, FGEG2, unaged).


## Known limitations

1. **Z-score masking is per-image.** Outlier exclusion (flakes, gaps, artefacts)
   is computed independently for each TIFF. The threshold (2.0 σ by default) was
   chosen by visual inspection; different images may require tuning.

2. **No detection threshold applied.** Earlier versions used Otsu thresholding.
   This was removed (see the `WHY THERE IS NO DETECTION THRESHOLD` note in the
   notebook header) because it introduced asymmetric bias in cross-swatch comparison.
   `area_fraction_pct` is used as a threshold-free brightness measure instead.

3. **Spatial registration assumed for ageing pairs.** The jointplot analysis
   (Figures 5–6) treats pixel (i, j) in the unaged image as corresponding to the
   same physical location in the aged image. This assumes the images are spatially
   registered; any misalignment will broaden the joint density estimate. Spatially co-
   registration here was obtained with the help of Robbert Erdmann, and Hugin softwear       (Version: 2019.2.0.b690aa0334b5).  

4. **Subsampling.** The jointplot uses a maximum of 60 000 pixel
   pairs shared across all registered pairs. For swatches with very few valid
   pixels, the plotted density may not be fully representative.

5. **Single ageing protocol.** The artificial ageing conditions are described in
   the thesis. Results may not generalise to other ageing protocols or real-world
   degradation pathways.

6. **Flat-field correction** Illumination during capturing of VIL images was geometrically heterogenous, i.e., not evenly distributed. To account for this, images were flat-field corrected:  the VIL image was divided by a normalised flat-field reference image (uniform paper target, same optical setup, no LWP filter).



## Acknowledgements

- **Robbert Erdmann** (University of Amsterdam) — developement of initial concept, code assistance, image co-registration (before and after images, personal sofwear) and scientific guidance throughout the project.
- **Agnes Brokerhof** — (Rijksdienst voor het Cultureel Erfgoed, RCE) institutional support and equipment. Namely, VIL capturing device: Crime-lite AUTO ( foster+freeman, the).
- Additional coding assistance was provided by Anthropic Claude Sonnet 4.6
  (repository preparation, code assistance). See `TRANSPARENCY.md` for full details.



## Citation

If you use this code, please cite using [`CITATION.cff`](CITATION.cff) or the metadata below.



## License

This repository is shared for scientific reproducibility.  
Contact the author for reuse beyond personal research.

