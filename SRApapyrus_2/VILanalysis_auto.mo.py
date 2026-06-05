# /// script
# [project]
# name = "vil-analysis"
# version = "1.3.0"
# requires-python = ">=3.11,<3.13"
# dependencies = [
#     "marimo>=0.23",
#     "numpy",
#     "matplotlib",
#     "pillow",
#     "seaborn",
#     "scikit-image",
#     "scipy",
#     "pandas",
# ]
# ///

# =============================================================================
# VIL Mockup Analysis — Book of the Dead of Qenna, M.Sc. Thesis
# Ignacio Sánchez Abenante, UvA 2026
#
# PURPOSE
# -------
# Produces a comparison table and figures for all mockup swatches.
# All pixel values are kept in their NATIVE, RAW form — no normalisation.
#   · 8-bit RGB TIFFs  → values in [0, 255]  (red channel extracted)
#   · 16-bit grayscale → values in [0, 65535] (single channel)
#
# WHY THERE IS NO DETECTION THRESHOLD
# ------------------------------------
# Earlier versions of this script used an Otsu threshold to separate 'active'
# (signal) pixels from background before computing metrics.  That approach was
# removed for three reasons:
#
#   1. VISIBILITY — when a swatch has very few pixels above a threshold, the
#      threshold filter silently discards most of the data and the pipeline
#      reports 'too few active pixels', making that swatch incomparable to the
#      others.  Using ALL pixels means every swatch always contributes.
#
#   2. COMPARABILITY — the Otsu threshold is image-dependent.  Even a 'shared'
#      threshold from the control swatch can clip dim swatches differently than
#      bright ones, introducing asymmetric bias in the comparison.  Using the
#      full pixel distribution avoids this entirely.
#
#   3. SCIENTIFIC INTENT — for VIL analysis the interesting question is often
#      WHERE on the intensity axis the distribution sits, not just how many
#      pixels cross a binary cut-off.  The KDE shows this directly.
#
# area_fraction_pct and normalised_signal_pct are still computed and reported,
# now defined relative to the median of each swatch (see compute_metrics).
# This gives a meaningful 'bright fraction' without needing an external threshold.
#
# OUTPUTS
# -------
#   vil_outputs/vil_results_table.csv        — one row per swatch, raw metrics
#   vil_outputs/vil_summaries.csv            — full-sentence interpretations
#   vil_outputs/vil_images_panel.pdf/.png    — swatch images, inferno colormap
#   vil_outputs/vil_histograms_all.pdf/.png  — KDE histograms, group-coloured
#   vil_outputs/vil_comparison_bar.pdf/.png  — signal bar chart (% of control)
#   vil_outputs/vil_scatter.pdf/.png         — area fraction × mean scatter
#   vil_outputs/vil_statistical_tests.csv    — Mann-Whitney U vs control
#
# HOW TO RUN
# ----------
#   marimo run VIL_analysis.mo.py          (interactive notebook)
#   python VIL_analysis.mo.py              (headless, saves all outputs)
#
# CONFIGURATION
# -------------
# Edit IMAGE_DIR, CONTROL_ID, CHANNEL, HIST_XLIM, and SWATCH_REGISTRY in
# Cell 3 below.  Everything else is derived automatically.
# =============================================================================

import marimo

__generated_with = "0.23.3"
app = marimo.App(width="full", auto_download=["html", "ipynb"])


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Dependencies**

    Imports all required libraries for image loading (`PIL`), array manipulation (`numpy`, `pandas`), statistics (`scipy.stats`), and visualisation (`matplotlib`, `seaborn`).  Run this cell first — all subsequent cells depend on these packages.

    No output is produced; this cell initialises the Python environment only.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib.patches import Patch
    from PIL import Image
    from scipy import stats
    from pathlib import Path

    return Image, Patch, Path, mo, np, pd, plt, sns, stats


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # VIL Mockup Analysis

    **Egyptian blue discrepancies in mockup samples infromed (to a limited extent) by the Book of the Dead of Qenna**

    ###***Mockup ID = SRA02 (papyrus support, before and after ageing)**

    ## **0.0/ Configuration and image data import**

    This cell defines all user-configurable parameters — image directory, control ID, channel, KDE x-axis limits, Z-score threshold, swatch registry, ageing pairs, and output paths — and creates the output directories.  **Edit only this cell** to adapt the pipeline to a new dataset or acquisition session.

    Pixel values are kept **raw** throughout (no normalisation, no global threshold at load time):
    - 8-bit RGB → channel 0 (red), values 0–255
    - 16-bit grayscale → values 0–65 535

    **Output:** `OUT_FIGS/`, `OUT_FIGS/vil_image/`, `OUT_FIGS/vil_kdecurve/`, `OUT_FIGS/vil_before-after_jointplot/`, and `OUT_CSV/` directories are created here if they do not exist.

    **Why raw values?** Using all pixels ensures every swatch is fully represented and directly comparable regardless of brightness.  A fixed threshold would silently discard data from dim swatches, making cross-swatch comparisons unfair.  `area_fraction_pct` — the fraction of valid pixels above each swatch's own median — is used as a threshold-free measure of brightness asymmetry.
    """)
    return


@app.cell
def _(Path):

    # ── Where are the TIFF files? ────────────────────────────────────────────
    IMAGE_DIR = Path(".")   # absolute or relative path to swatch TIFFs

    # ── Which swatch is the control? ─────────────────────────────────────────
    # The control mean is used to compute normalised_signal_pct for every
    # other swatch (swatch mean / control mean × 100).
    # change per mockup support: papyrus (SRA)and paper (SRAB)
    CONTROL_ID = "P.00"

    # ── Channel to extract ────────────────────────────────────────────────────
    # 0 = red channel of an 8-bit RGB TIFF  (most appropiate for CL)
    # 1 = green,  2 = blue
    # None = grayscale / 16-bit single-channel TIFF (VIL)
    CHANNEL = 0

    # ── KDE x-axis limits ────────────────────────────────────────────────────
    # Match your expected signal range in raw pixel units so that all
    # KDE panels share the same x-axis and are directly comparable.
    # For 8-bit images (0, 255) shows the full range; (e.g ~(60, 220)  zooms in.
    # For 16-bit images this widen considerably (e.g. (0, 65535)). --> ASK ROB to normalise?
    HIST_XLIM = (0, 255)   # (x_min, x_max) in raw pixel value units

    # ── Z-score outlier threshold ─────────────────────────────────────────────
    # Pixels whose Z-score (distance from the image mean in units of std dev)
    # exceeds this value are masked and excluded from ALL calculations and plots.
    #
    # How to choose:
    #   2.0  → removes outermost ~5 % of a normal distribution  (conservative)
    #   1.5  → removes outermost ~13 %                           (moderate)
    #   1.0  → removes outermost ~32 %                           (aggressive)
    #
    # Use the red pixels in Figure 1 (vil_images_panel) to judge visually
    # whether the right pixels are being excluded before changing this.
    # ── ▼ CHANGE THIS VALUE TO TUNE THE FILTER ▼ ─────────────────────────────
    ZSCORE_THRESHOLD = 2.0
    # ── ▲ ────────────────────────────────────────────────────────────────────

    # ── Ghost-signal threshold for the bar chart annotation ──────────────────
    # Swatches below this % of the control mean are marked on the bar chart.
    # This is purely a visual annotation — it does NOT affect data processing.
    #revise with acc VIL data
    #GHOST_THRESHOLD_PCT = 20

    # ── Group colour palette ─────────────────────────────────────────────────
    # Used for KDE panels, scatter plot, and bar chart.
    #purpose: effective communication (contrast) and aestehtic coherence 
    # All swatches within the same group share one colour.
    GROUP_COLOURS = {
        "Pigment":      "#4A90D9",   # blue
        "Mixture":      "#E07B3F",   # amber
        "Stratigraphy": "#5BAD72",   # green
        "Alteration":   "#9B6BB5",   # purple
    }

    # ── Swactch registry ───────────────────────────────────────────────────────
    # One dict per swatch.  Keys:
    #   id     — unique ID matching Vriables Overview Table in Methodology chapter
    #   file   — TIFF filename (case-insensitive lookup)
    #   label  — readable label for plot axes
    #   group  — variable category (Pigment / Mixture / Stratigraphy / Alteration)
    SWATCH_REGISTRY = [
        # ── Pigment composition ───────────────────────────────────────────────
        {"id": "P.00",     "file": "P00_control.tif",     "label": "EB.HA control",       "group": "Pigment"},
        {"id": "P.01",     "file": "P01.tif",     "label": "EB Kremer",           "group": "Pigment"},
        {"id": "G.01",     "file": "G01.tif",     "label": "Finer",          "group": "Pigment"},

        # ── Stratigraphy ─────────────────────────────────────────────────────
        {"id": "S.CAR",    "file": "SCAR.tif",    "label": "Carbon overlay",      "group": "Stratigraphy"},
        {"id": "S.FEO",    "file": "SFEO.tif",    "label": "Iron oxide overlay",  "group": "Stratigraphy"},
        {"id": "S.ORP",    "file": "SORP.tif",    "label": "Orpiment overlay",    "group": "Stratigraphy"},

        # ── Pigment mixtures ─────────────────────────────────────────────────
        {"id": "M.ORP.01", "file": "MORP01.tif",  "label": "Orpiment 1:9",        "group": "Mixture"},
        {"id": "M.ORP.02", "file": "MORP02.tif",  "label": "Orpiment 1:1",        "group": "Mixture"},
        {"id": "M.ORP.03", "file": "MORP03.tif",  "label": "Orpiment 9:1",        "group": "Mixture"},
        {"id": "M.CAR.01", "file": "MCAR01.tif",  "label": "Carbon 1:9",          "group": "Mixture"},
        {"id": "M.CAR.02", "file": "MCAR02.tif",  "label": "Carbon 1:1",          "group": "Mixture"},
        {"id": "M.CAR.03", "file": "MCAR03.tif",  "label": "Carbon 9:1",          "group": "Mixture"},
        {"id": "M.ASH.01", "file": "MASH01.tif",  "label": "Ash 1:9",             "group": "Mixture"},
        {"id": "M.ASH.02", "file": "MASH02.tif",  "label": "Ash 1:1",             "group": "Mixture"},
        {"id": "M.ASH.03", "file": "MASH03.tif",  "label": "Ash 9:1",             "group": "Mixture"},

        # ── Alteration / added materials ─────────────────────────────────────
        {"id": "A.01",     "file": "A01.tif",     "label": "Animal glue",         "group": "Alteration"},
        {"id": "A.02",     "file": "A02.tif",     "label": "Glue + JP",           "group": "Alteration"},
    ]

    # ── Ageing pairs ─────────────────────────────────────────────────────────
    # Each dict matches a swatch id from SWATCH_REGISTRY to its unaged and aged TIFF filenames.  
    AGEING_PAIRS = [
        # ── Pigment ──────────────────────────────────────────────────────────
        {"id": "P.00",     "label": "EB.HA control",      "unaged_file": "P00_control.tif",  "aged_file": "P00_control_aged.tif"},
        {"id": "P.01",     "label": "EB Kremer",           "unaged_file": "P01.tif",          "aged_file": "P01_aged.tif"},
        {"id": "G.01",     "label": "HA Finer",          "unaged_file": "G01.tif",          "aged_file": "G01_aged.tif"},

        # ── Stratigraphy ──────────────────────────────────────────────────────
        {"id": "S.CAR",    "label": "Carbon overlay",     "unaged_file": "SCAR.tif",         "aged_file": "SCAR_aged.tif"}, 
        {"id": "S.FEO",    "label": "Iron oxide overlay", "unaged_file": "SFEO.tif",         "aged_file": "SFEO_aged.tif"},
        {"id": "S.ORP",    "label": "Orpiment overlay",   "unaged_file": "SORP.tif",         "aged_file": "SORP_aged.tif"},


        # ── Mixture ───────────────────────────────────────────────────────────
        {"id": "M.ORP.01", "label": "Orpiment 1:9",       "unaged_file": "MORP01.tif",       "aged_file": "MORP01_aged.tif"},
        {"id": "M.ORP.02", "label": "Orpiment 1:1",       "unaged_file": "MORP02.tif",       "aged_file": "MORP02_aged.tif"},
        {"id": "M.ORP.03", "label": "Orpiment 9:1",       "unaged_file": "MORP03.tif",       "aged_file": "MORP03_aged.tif"},

        {"id": "M.CAR.01", "label": "Carbon 1:9",       "unaged_file": "MCAR01.tif",       "aged_file": "MCAR01_aged.tif"},
        {"id": "M.CAR.02", "label": "Carbon 1:1",       "unaged_file": "MCAR02.tif",       "aged_file": "MCAR02_aged.tif"},
        {"id": "M.CAR.03", "label": "Carbon 9:1",       "unaged_file": "MCAR03.tif",       "aged_file": "MCAR03_aged.tif"},

        {"id": "M.ASH.01", "label": "Ash 1:9",       "unaged_file": "MASH01.tif",       "aged_file": "MASH01_aged.tif"},
        {"id": "M.ASH.02", "label": "Ash 1:1",       "unaged_file": "MASH02.tif",       "aged_file": "MASH02_aged.tif"},
        {"id": "M.ASH.03", "label": "Ash 9:1",       "unaged_file": "MASH03.tif",       "aged_file": "MASH03_aged.tif"},

        # ── Alteration ────────────────────────────────────────────────────────
        {"id": "A.01",     "label": "Animal glue",        "unaged_file": "A01.tif",          "aged_file": "A01_aged.tif"},
        {"id": "A.02",     "label": "Animal glue + JP",          "unaged_file": "A02.tif",          "aged_file": "A02_aged.tif"},
    ]

    # ── Output directory ─────────────────────────────────────────────────────
    OUT_FIGS = Path("./vil_outputs_figures")
    OUT_FIGS.mkdir(exist_ok=True)

    # Subfolders for individual (per-swatch) saves
    OUT_IMG   = OUT_FIGS / "vil_image"
    OUT_HIST  = OUT_FIGS / "vil_kdecurve"
    OUT_JOINT = OUT_FIGS / "vil_before-after_jointplot"
    OUT_IMG.mkdir(exist_ok=True)
    OUT_HIST.mkdir(exist_ok=True)
    OUT_JOINT.mkdir(exist_ok=True)

    OUT_CSV = Path("./vil_outputs_tables")
    OUT_CSV.mkdir(exist_ok=True)
    return (
        AGEING_PAIRS,
        CHANNEL,
        CONTROL_ID,
        GROUP_COLOURS,
        HIST_XLIM,
        IMAGE_DIR,
        OUT_CSV,
        OUT_FIGS,
        OUT_HIST,
        OUT_IMG,
        OUT_JOINT,
        SWATCH_REGISTRY,
        ZSCORE_THRESHOLD,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **0.1/ CONTROL SWATCH — Z-SCORE BASELINE (print)**

    Loads the control swatch and applies the same **Z-score outlier mask** used throughout the rest of the notebook (threshold set in the configuration cell).  Masked pixels (|Z| > threshold) are excluded before computing the control mean.

    **Output:** control image shape, dtype, raw value range, number of masked pixels, and the valid-pixel mean.

    **Why this matters:** `control_mean` is the denominator for `normalised_signal_pct` in every downstream plot.  A stable, outlier-free reference mean is essential — if the control image contains flakes or artefacts that inflate or deflate its mean, every swatch's normalised value will be systematically biased.  Check that the masked-pixel count is small (ideally < 5 %) before proceeding.
    """)
    return


@app.cell
def _(
    CHANNEL,
    CONTROL_ID,
    IMAGE_DIR,
    SWATCH_REGISTRY,
    ZSCORE_THRESHOLD,
    find_file,
    load_channel,
    make_masked_image,
):
    _ctrl_entry = next(s for s in SWATCH_REGISTRY if s["id"] == CONTROL_ID)
    _ctrl_path  = find_file(IMAGE_DIR, _ctrl_entry["file"])

    if _ctrl_path is None:
        raise FileNotFoundError(
            f"Control file '{_ctrl_entry['file']}' not found in '{IMAGE_DIR}'.\n"
            "Update IMAGE_DIR or CONTROL_ID in the configuration cell."
        )

    control_img    = load_channel(_ctrl_path, CHANNEL)
    _ctrl_masked   = make_masked_image(control_img)   # 2-D masked array, outliers masked
    # np.ma.mean automatically ignores masked pixels — reference for normalised_signal_pct
    control_mean   = float(_ctrl_masked.mean())
    _n_masked_ctrl = int(_ctrl_masked.mask.sum()) if _ctrl_masked.mask is not False else 0

    print(f"Control swatch : {CONTROL_ID}  ('{_ctrl_path.name}')")
    print(f"  Image shape  : {control_img.shape}   dtype : {control_img.dtype}")
    print(f"  Value range  : {control_img.min()} – {control_img.max()}  (raw pixel units)")
    print(f"  Masked pixels: {_n_masked_ctrl} / {_ctrl_masked.size} excluded  "
          f"({_n_masked_ctrl / _ctrl_masked.size * 100:.1f}%,  |Z| > {ZSCORE_THRESHOLD}  σ)")
    print(f"  Control mean (valid pixels, raw) : {control_mean:.2f}")
    return (control_mean,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **0.2/ SWATCH METADATA — ALL SWATCHES (print)**

    Loads each TIFF listed in `SWATCH_REGISTRY`, extracts the configured channel, applies the Z-score outlier mask, and computes per-swatch summary statistics: mean, standard deviation, and normalised signal (swatch mean ÷ control mean × 100).

    **Output (printed):** one row per swatch with file-found status, image shape, masked-pixel count, raw mean, std, and normalised signal percentage.

    **How to interpret:** scan the output for:
    - **file_found = False** — TIFF not located in `IMAGE_DIR`; that swatch will be absent from all downstream figures and tables.  Check the filename in `SWATCH_REGISTRY` and the directory path.
    - **Masked pixels > ~10 %** — high outlier rate; likely indicates surface flaking, dust, or acquisition artefacts.  Examine the swatch spatially in Figure 1 (red pixels).
    - **Normalised signal near 0 %** — swatch produces negligible VIL response; a ghost-pigment candidate for thesis discussion.
    - **Normalised signal > 150 %** — swatch is substantially brighter than the control; note this in interpretation and verify it is not a processing artefact.
    """)
    return


@app.cell
def _(
    CHANNEL,
    IMAGE_DIR,
    SWATCH_REGISTRY,
    compute_metrics,
    control_mean,
    find_file,
    load_channel,
    pd,
):

    _EMPTY = {
        "mean_raw": None, "median_raw": None, "std_raw": None,
        "area_fraction_pct": None, "normalised_signal_pct": None,
        "p10": None, "p90": None, "skewness": None, "cv": None,
        "n_pixels": None, "n_masked": None, "pct_masked": None,
    }

    records = []
    missing = []

    for _entry in SWATCH_REGISTRY:
        _path = find_file(IMAGE_DIR, _entry["file"])

        if _path is None:
            missing.append(_entry["id"])
            records.append({
                "id": _entry["id"], "label": _entry["label"],
                "group": _entry["group"], **_EMPTY, "file_found": False,
            })
            continue

        try:
            _img     = load_channel(_path, CHANNEL)
            _metrics = compute_metrics(_img, control_mean)
            records.append({
                "id": _entry["id"], "label": _entry["label"],
                "group": _entry["group"], **_metrics, "file_found": True,
            })
            print(
                f"  ok  {_entry['id']:12s}  '{_path.name}'  "
                f"shape={_img.shape}  dtype={_img.dtype}  "
                f"mean={_metrics['mean_raw']:.1f}  "
                f"signal={_metrics['normalised_signal_pct']:.1f}%  "
                f"masked={_metrics['pct_masked']:.1f}%"
            )
        except Exception as _err:
            print(f"  ERR {_entry['id']:12s}  '{_path.name}'  {_err}")
            records.append({
                "id": _entry["id"], "label": _entry["label"],
                "group": _entry["group"], **_EMPTY, "file_found": False,
            })

    print(f"\n{'─' * 60}")
    print(f"  Found : {sum(r['file_found'] for r in records)} / {len(records)} swatches")
    if missing:
        print(f"  Missing IDs: {', '.join(missing)}")

    _col_order = [
        "id", "group", "label",
        "normalised_signal_pct", "area_fraction_pct",
        "mean_raw", "median_raw", "std_raw",
        "p10", "p90", "skewness", "cv",
        "n_pixels", "n_masked", "pct_masked", "file_found",
    ]
    df = pd.DataFrame(records)[_col_order]
    return (df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **1./ COMPUTE PER-SWATCH STATISTICS**

    Iterates over every swatch with a located TIFF, applies the Z-score outlier mask (|Z| > `ZSCORE_THRESHOLD`), and computes the following metrics on the **valid pixel set** (unmasked pixels only):

    | Metric | Description |
    |---|---|
    | `mean_raw` | Mean raw pixel value of valid pixels |
    | `std_raw` | Standard deviation of valid pixels |
    | `normalised_signal_pct` | Swatch mean ÷ control mean × 100 |
    | `area_fraction_pct` | Fraction of valid pixels above the swatch's own median (threshold-free brightness asymmetry) |
    | `skewness` | Fisher skewness of the valid-pixel distribution |
    | `n_valid` | Number of valid pixels after masking |

    **Output:** `df` updated with all metric columns; all downstream figures and CSV tables read from these values.

    **Why Z-score masking?** Pixels more than ±`ZSCORE_THRESHOLD` σ from the per-image mean are excluded before any statistic is computed.  These correspond to surface flakes, dust, gaps, or camera artefacts that would otherwise skew the mean and inflate the standard deviation.  The mask is applied per-image so no cross-swatch contamination occurs.  The excluded pixels are shown in red in Figure 1 for spatial verification.
    """)
    return


@app.cell
def _(Image, ZSCORE_THRESHOLD, np, stats):
    def load_channel(path, channel):
        """Load a TIFF and return a raw 2-D numpy array (no normalisation).

        Uses PIL so the native dtype is preserved:
          - uint8  for 8-bit RGB  (values 0–255)
          - uint16 for 16-bit grayscale (values 0–65535)

        Parameters
        ----------
        path    : path-like
        channel : int or None
            0/1/2  → extract R/G/B from an (H, W, C) RGB image
            None   → return as-is for single-channel images, or average
                     all channels for multi-channel inputs
        """
        arr = np.array(Image.open(str(path)))

        if arr.ndim == 2:
            return arr                              # single-channel (e.g. 16-bit)

        if channel is None:
            return arr.mean(axis=2).astype(arr.dtype)   # average channels
        return arr[:, :, channel]                   # extract R / G / B


    def make_masked_image(img_raw):
        """Return a 2-D np.ma.MaskedArray with outlier pixels masked.

        Pixels whose Z-score (distance from this image's own mean, measured in
        standard deviations) exceeds ZSCORE_THRESHOLD are masked.  Masked pixels:
          · are excluded from all np.ma arithmetic (mean, std, percentile …)
          · show as red in Figure 1 (image panel) so you can verify visually

        This removes localised artefacts — flaked overlay exposing underlying
        pigment, edge gaps, dust, hot/dead pixels — without applying a global
        signal threshold that would bias comparisons between swatches.

        Tune ZSCORE_THRESHOLD in the configuration cell (top of notebook).
          2.0 → ~5 % removed  (conservative, default)
          1.5 → ~13 % removed (moderate)
          1.0 → ~32 % removed (aggressive)

        Parameters
        ----------
        img_raw : 2-D integer array (uint8 or uint16)

        Returns
        -------
        np.ma.MaskedArray  shape = img_raw.shape, dtype = float64
            mask is True (excluded) where |Z| > ZSCORE_THRESHOLD
        """
        px    = img_raw.astype(float)
        flat  = px.ravel()
        sigma = flat.std()
        if sigma == 0:
            return np.ma.array(px, mask=False)
        z = (px - flat.mean()) / sigma
        # ── Z-SCORE MASK ──────────────────────────────────────────────────────
        # Pixels where |Z| > ZSCORE_THRESHOLD are excluded (mask=True).
        # Change ZSCORE_THRESHOLD in the CONFIGURATION CELL to tune this.
        return np.ma.array(px, mask=(np.abs(z) > ZSCORE_THRESHOLD))
        # ──────────────────────────────────────────────────────────────────────


    def compute_metrics(img_raw, control_mean):
        """Compute VIL intensity metrics using a Z-score masked array (±2 σ).

        make_masked_image() builds a 2-D masked array; .compressed() yields
        the 1-D array of valid pixel values used for all statistics.
        Extreme outliers (flaked overlay, edge gaps, sensor artefacts) are
        excluded per-image so swatches remain directly comparable.

        area_fraction_pct: fraction of valid pixels above the swatch's own
        median — threshold-free measure of right-skew / brightness.

        normalised_signal_pct: valid-pixel mean as % of the control's
        valid-pixel mean (both raw units).

        Parameters
        ----------
        img_raw      : 2-D integer array (uint8 or uint16)
        control_mean : float — valid-pixel mean of the control swatch (raw)
        """
        masked   = make_masked_image(img_raw)
        px       = masked.compressed()   # 1-D array of non-masked pixel values
        n_total  = masked.size
        n_masked = int(masked.mask.sum()) if masked.mask is not np.ma.nomask else 0

        mean_r   = float(np.mean(px))
        median_r = float(np.median(px))
        std_r    = float(np.std(px))
        # Fraction of valid pixels above the swatch's own median (threshold-free)
        area_pct = float((px > median_r).sum() / px.size * 100)
        # Signal relative to control mean (both raw units)
        norm_sig = float(mean_r / (control_mean + 1e-9) * 100)
        p10      = float(np.percentile(px, 10))
        p90      = float(np.percentile(px, 90))
        skew     = float(stats.skew(px))
        cv       = float(std_r / (mean_r + 1e-9))

        return {
            "mean_raw":              round(mean_r,   2),
            "median_raw":            round(median_r, 2),
            "std_raw":               round(std_r,    2),
            "area_fraction_pct":     round(area_pct, 2),
            "normalised_signal_pct": round(norm_sig, 1),
            "p10":                   round(p10,      2),
            "p90":                   round(p90,      2),
            "skewness":              round(skew,     3),
            "cv":                    round(cv,       3),
            "n_pixels":              int(px.size),      # valid pixels after masking
            "n_masked":              n_masked,           # excluded outlier count
            "pct_masked":            round(n_masked / n_total * 100, 1),
        }


    def find_file(directory, filename):
        exact = directory / filename
        if exact.exists():
            return exact
        needle = filename.lower()
        try:
            for f in directory.iterdir():
                if f.name.lower() == needle:
                    return f
        except (OSError, PermissionError):
            pass
        return None

    return compute_metrics, find_file, load_channel, make_masked_image


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **1.1/ TABLE 1 — FULL STATISTICS RESULTS (print + CSV)**

    Compiles all per-swatch statistics from Cell 1 into a structured table, prints it for immediate review, and exports it for external analysis.

    **Output:**
    - **Printed** in the notebook.
    - **`vil_stats-results_table.csv`** — one row per swatch, all metric columns; suitable for import into R, SPSS, or as supplementary data.

    **How to interpret:** use this table to:
    - Identify swatches with anomalously high or low `normalised_signal_pct` and prioritise them for thesis discussion.
    - Check `n_valid` — if a swatch has substantially fewer valid pixels than others, its statistics are less reliable and should be noted as a caveat.
    - Compare `std_raw` within groups: high within-group variance suggests spatially non-uniform luminescence (uneven pigment application or local surface damage).
    - Flag `skewness` > 1 as right-skewed distributions — bright-pixel dominated, indicating that high-intensity signal is spatially concentrated rather than spread uniformly across the swatch.
    """)
    return


@app.cell
def _(OUT_CSV, df):
    _csv_path = OUT_CSV / "vil_stats-results_table.csv"
    df.to_csv(_csv_path, index=False)
    print(f"Saved: {_csv_path}")

    # ---- CSV structured row ----
    _display_cols = ["id", "group", "label",
                     "normalised_signal_pct", "area_fraction_pct",
                     "mean_raw", "std_raw", "skewness", "n_masked", "pct_masked"]
    print("\n── Results table (found swatches only) ──")
    print(
        df[df["file_found"] == True][_display_cols]
        .rename(columns={
            "normalised_signal_pct": "signal_%ctrl",
            "area_fraction_pct":     "active_%", #bright
            "mean_raw":              "mean",
            "std_raw":               "std",
        })
        .to_string(index=False)
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **2./ FIGURE 1 — SWATCH IMAGE PANEL: CONTROL COMPARISON**

    Re-plots each swatch side-by-side with the **control** on a single shared **global colour scale**, derived from the combined min/max of all valid pixels across the control and every swatch.  This shared scale makes brightness differences relative to the control directly legible without relying on bar heights.

    **Output:** `vil_images_panel_masked_ctrlcompare.pdf/.png/.svg` (combined panel, `.svg` for Inkscape editing); one control+swatch pair saved individually to `vil_image/vil_image_{id}_ctrlcompare.pdf/.png`.

    **How to interpret:** the global colour scale is the critical feature of this figure — every panel uses the same min/max, so colour encodes absolute pixel value, not relative local brightness:
    - A swatch that appears substantially **darker** than the control carries a genuinely lower luminescence signal on the same physical scale.
    - A swatch with a similar colour range to the control is comparable in absolute pixel values, reinforcing a normalised signal near 100 % in Figure 3.
    - Compare the spatial distribution of red pixels (masked outliers) between the control and swatch panels: patterns shared across both may reflect a common source (e.g. illumination geometry); patterns unique to one swatch indicate surface heterogeneity specific to that material.
    """)
    return


@app.cell
def _(
    CHANNEL,
    CONTROL_ID,
    IMAGE_DIR,
    OUT_FIGS,
    OUT_IMG,
    SWATCH_REGISTRY,
    ZSCORE_THRESHOLD,
    df,
    find_file,
    load_channel,
    make_masked_image,
    plt,
):
    # -------------------------------
    # COLORMAP FOR MASKED PIXELS
    # -------------------------------
    _cmap_masked = plt.cm.viridis.copy()
    _cmap_masked.set_bad(color="red", alpha=0.6)   # excluded pixels shown in red


    # -------------------------------
    # LOAD CONTROL IMAGE
    # -------------------------------
    _ctrl_entry = next(s for s in SWATCH_REGISTRY if s["id"] == CONTROL_ID)
    _ctrl_path  = find_file(IMAGE_DIR, _ctrl_entry["file"])

    if _ctrl_path is None:
        raise FileNotFoundError(
            f"Control file '{_ctrl_entry['file']}' not found in '{IMAGE_DIR}'."
        )

    _control_img = load_channel(_ctrl_path, CHANNEL)


    # -------------------------------
    # LOAD ALL NON-CONTROL SWATCHES
    # -------------------------------
    _loaded_swatches = []

    for _, row in df[df["file_found"] == True].iterrows():

        if row["id"] == CONTROL_ID:
            continue

        entry = next(s for s in SWATCH_REGISTRY if s["id"] == row["id"])
        path  = find_file(IMAGE_DIR, entry["file"])

        if path is None:
            raise FileNotFoundError(
                f"Swatch file '{entry['file']}' not found."
            )

        img = load_channel(path, CHANNEL)

        _loaded_swatches.append({
            "row": row,
            "path": path,
            "img": img,
        })

    # -------------------------------
    # MASK ALL SWATCHES
    # -------------------------------
    _control_masked = make_masked_image(_control_img)

    for sw in _loaded_swatches:
        sw["masked"] = make_masked_image(sw["img"])


    # -------------------------------
    # GLOBAL COLOUR SCALE
    # (ignores masked pixels)
    # -------------------------------
    _all_masked = [_control_masked] + [
        sw["masked"] for sw in _loaded_swatches
    ]

    _global_vmin = min(float(img.min()) for img in _all_masked)
    _global_vmax = max(float(img.max()) for img in _all_masked)

    print(
        f"Global colour scale: "
        f"{_global_vmin:.2f} → {_global_vmax:.2f}"
    )

    # -------------------------------
    # PLOT: CONTROL vs EACH SWATCH
    # -------------------------------
    _n_rows = len(_loaded_swatches)

    fig, axes = plt.subplots(
        _n_rows,
        2,
        figsize=(9, max(_n_rows, 1) * 4),
        constrained_layout=True,
    )

    if _n_rows == 1:
        axes = [axes]


    for i, sw in enumerate(_loaded_swatches):

        axL = axes[i][0]
        axR = axes[i][1]

        imgR = sw["masked"]
        row  = sw["row"]
        path = sw["path"]

        # LEFT: control
        imL = axL.imshow(
            _control_masked,
            cmap=_cmap_masked,
            vmin=_global_vmin, #or 0 
            vmax=_global_vmax, #or 255/65350
        )

        # RIGHT: swatch
        imR = axR.imshow(
            imgR,
            cmap=_cmap_masked,
            vmin=_global_vmin,#or 0 
            vmax=_global_vmax, #or 255/65350
        )

        # titles
        axL.set_title(
            f"Control: {CONTROL_ID}\n"
            f"masked: {int(_control_masked.mask.sum())} px "
            f"({_control_masked.mask.mean()*100:.1f}%)",
            fontsize=8,
        )

        axR.set_title(
            f"{row['id']} — {row['label']}\n"
            f"masked: {int(imgR.mask.sum())} px "
            f"({imgR.mask.mean()*100:.1f}%)",
            fontsize=8,
        )
     # _axL.set_title(
     #            f"{_rowL['id']} — {_rowL['label']}\n"
     #            f"masked: {int(_imgL.mask.sum())} px  ({_imgL.mask.mean()*100:.1f}%)",
     #            fontsize=8,

        axL.axis("off")
        axR.axis("off")

        # shared colorbar for each row
        fig.colorbar(
            imR,
            ax=[axL, axR],
            orientation="vertical",
            fraction=0.02,
            label="Raw pixel value",
        )

        # Individual save — control + swatch pair
        _fig_s, (_ax_sL, _ax_sR) = plt.subplots(1, 2, figsize=(9, 4), constrained_layout=True)
        _im_sL = _ax_sL.imshow(_control_masked, cmap=_cmap_masked, vmin=_global_vmin, vmax=_global_vmax)
        _im_sR = _ax_sR.imshow(imgR, cmap=_cmap_masked, vmin=_global_vmin, vmax=_global_vmax)
        _ax_sL.set_title(
            f"Control: {CONTROL_ID}\n{_ctrl_path.name}\n"
            f"masked: {int(_control_masked.mask.sum())} px ({_control_masked.mask.mean()*100:.1f}%)",
            fontsize=8,
        )
        _ax_sR.set_title(
            f"{row['id']} — {row['label']}\n{path.name}\n"
            f"masked: {int(imgR.mask.sum())} px ({imgR.mask.mean()*100:.1f}%)",
            fontsize=8,
        )
        _ax_sL.axis("off")
        _ax_sR.axis("off")
        _fig_s.colorbar(_im_sR, ax=[_ax_sL, _ax_sR], orientation="vertical", fraction=0.02, label="Raw pixel value")
        _fig_s.suptitle(
            f"VIL swatch image — control comparison (±{ZSCORE_THRESHOLD}σ masking)\n"
            "Red pixels = outliers excluded",
            fontsize=9,
        )
        _fig_s.savefig(OUT_IMG / f"vil_image_{row['id']}_ctrlcompare.pdf", dpi=150, bbox_inches="tight")
        _fig_s.savefig(OUT_IMG / f"vil_image_{row['id']}_ctrlcompare.png", dpi=150, bbox_inches="tight")
        plt.close(_fig_s)


    fig.suptitle(
        f"VIL swatch images — control comparison (Z-score masked = ±{ZSCORE_THRESHOLD}σ)\n"
        "Red pixels = outliers excluded (artefacts / flakes / gaps)",
        fontsize=11,
    )

        # -------------------------
        # SAVE PDF AND PNG report
        # -------------------------

    fig.savefig(
        OUT_FIGS / "vil_images_panel_masked_ctrlcompare.pdf",
        dpi=150,
        bbox_inches="tight",
    )

    fig.savefig(
        OUT_FIGS / "vil_images_panel_masked_ctrlcompare.png",
        dpi=150,
        bbox_inches="tight",
    )

    fig.savefig(
        OUT_FIGS / "vil_images_panel_masked_ctrlcompare.svg", #inkscape
        dpi=150,
        bbox_inches="tight",
    )

    plt.show()

    print(
        f"Global colour scale: "
        f"{_global_vmin:.2f} → {_global_vmax:.2f}"
    )
    print("Saved: vil_images_panel_masked_ctrlcompare.pdf/.png/.svg | individuals → vil_image/")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **3./ FIGURE 2 — KDE INTENSITY DISTRIBUTIONS CURVE  (all swatches, original style)**

    Plots the **kernel density estimate (KDE)** of each swatch's valid-pixel intensity distribution after Z-score outlier exclusion.  Each panel overlays the control as a grey reference, so every swatch is read against the same baseline.  The x-axis is fixed across all panels (`HIST_XLIM`) for direct comparability.

    **Output:** `vil_kdecurves_all.pdf/.png` (combined panel); one KDE per swatch saved individually to `vil_kdecurve/vil_kdecurve_{id}.pdf/.png`.

    **How to read:**
    - **Grey filled curve** — control reference distribution; its peak position and width are the visual baseline.
    - **Dashed grey line** — control mean.
    - **Coloured curve** — swatch distribution, filled with the variable-group colour; **blue band** = ±1σ around the swatch mean; **blue dashed line** = swatch mean.
    - A swatch distribution shifted **right** of the control has higher mean luminescence; shifted **left** has lower.  A **narrower peak** indicates spatially uniform pixels; a **broader or bimodal peak** indicates heterogeneity.
    """)
    return


@app.cell
def _(
    CHANNEL,
    CONTROL_ID,
    GROUP_COLOURS,
    HIST_XLIM,
    IMAGE_DIR,
    OUT_FIGS,
    OUT_HIST,
    SWATCH_REGISTRY,
    df,
    find_file,
    load_channel,
    make_masked_image,
    plt,
    sns,
):
    _found2 = df[df["file_found"] == True]
    _n2     = len(_found2)
    _ncols2 = 4
    _nrows2 = -(-_n2 // _ncols2)   # ceiling division

    _fig2, _axes2 = plt.subplots(
        _nrows2, _ncols2,
        figsize=(_ncols2 * 4.5, _nrows2 * 3.5),
        constrained_layout=True,
    )
    _axes2 = _axes2.flatten()

    # Pre-load control distribution once — shown as grey reference in every panel
    _ctrl_e2      = next(s for s in SWATCH_REGISTRY if s["id"] == CONTROL_ID)
    _ctrl_masked  = make_masked_image(
        load_channel(find_file(IMAGE_DIR, _ctrl_e2["file"]), CHANNEL)
    )
    _ctrl_flat = _ctrl_masked.compressed()   # 1-D valid pixels (outliers masked)
    _ctrl_mu   = _ctrl_flat.mean()

    for _i, (_, _row) in enumerate(_found2.iterrows()):
        _ax = _axes2[_i]

        _entry   = next(s for s in SWATCH_REGISTRY if s["id"] == _row["id"])
        _masked  = make_masked_image(
            load_channel(find_file(IMAGE_DIR, _entry["file"]), CHANNEL)
        )
        _data = _masked.compressed()   # 1-D valid pixels — outliers (flakes, gaps) excluded

        _mu  = _data.mean()
        _sig = _data.std()

        # Grey control reference so every panel can be read against the same baseline
        if len(_ctrl_flat) > 0:
            sns.kdeplot(
                _ctrl_flat, ax=_ax,
                color="#cccccc", fill=True, alpha=0.30,
                linewidth=1.0, label="Control",
            )

            # Grey dotted control mean line
        _ax.axvline(
            _ctrl_mu,
            color="gray",
            lw=1.5,
    #        ls=(0, (5, 3)),   # classic clean dash
            ls="--",
            alpha=0.9,
            zorder=3,
        )

        # Swatch KDE — filled with the group colour
        _col = GROUP_COLOURS.get(_row["group"], "#555555")
        sns.kdeplot(
            _data, ax=_ax,
            color=_col,
            alpha=0.35,
            fill=True,
            linewidth=2.0,
            zorder=2,
        )

        # Fixed x-axis so all panels share the same scale → directly comparable
        _ax.set_xlim(*HIST_XLIM)

        # ±1 σ shaded band (blue, same style as original exploration script)
        _ax.axvspan(_mu - _sig, _mu + _sig, color="tab:blue", alpha=0.18, zorder=0)

        # Mean line
        _ax.axvline(_mu, color="tab:blue", lw=1.5, 
    #                ls=(0, (5, 3))   # classic clean dash
                    ls="--", 
                    zorder=3)

        # Mean / Std annotation box — top-right, blue border
        _ax.text(
            1.10, 1,
            f"μ=  {_mu:.2f}\nσ=  {_sig:.2f}",
            transform=_ax.transAxes,
            ha="right", va="top",
            fontsize=9,
            bbox=dict(
                boxstyle="round,pad=0.45",
                facecolor="white",
                edgecolor="steelblue",
                linewidth=1.2,
                alpha=0.95,
            ),
            zorder=4,
        )

        _ax.set_title(f"{_row['id']} — {_row['label']}", fontsize=8, pad=10) #vertical space
        _ax.set_ylabel("Density", fontsize=7)
        _ax.set_xlabel("Raw pixel value", fontsize=7)
        _ax.tick_params(labelsize=7)
        _ax.grid(alpha=0.15)
        _ax.spines["top"].set_visible(False)
        _ax.spines["right"].set_visible(False)

        # Individual save
        _fig_h, _ax_h = plt.subplots(figsize=(4.5, 3.5), constrained_layout=True)
        if len(_ctrl_flat) > 0:
            sns.kdeplot(_ctrl_flat, ax=_ax_h, color="#cccccc", fill=True, alpha=0.30, linewidth=1.0, label="Control")
        _ax_h.axvline(_ctrl_mu, color="gray", lw=1.5, ls="--", alpha=0.9, zorder=3)
        sns.kdeplot(_data, ax=_ax_h, color=_col, alpha=0.35, fill=True, linewidth=2.0, zorder=2)
        _ax_h.set_xlim(*HIST_XLIM)
        _ax_h.axvspan(_mu - _sig, _mu + _sig, color="tab:blue", alpha=0.18, zorder=0)
        _ax_h.axvline(_mu, color="tab:blue", lw=1.5, ls="--", zorder=3)
        _ax_h.text(
            1.1, 0.97, f"μ=  {_mu:.2f}\nσ=   {_sig:.2f}",
            transform=_ax_h.transAxes, ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor="steelblue", linewidth=1.2, alpha=0.95),
        )
        _ax_h.set_title(f"{_row['id']} — {_row['label']}", fontsize=8)
        _ax_h.set_ylabel("Density", fontsize=7)
        _ax_h.set_xlabel("Raw pixel value", fontsize=7)
        _ax_h.tick_params(labelsize=7)
        _ax_h.grid(alpha=0.15)
        _ax_h.spines["top"].set_visible(False)
        _ax_h.spines["right"].set_visible(False)
        _fig_h.suptitle(
            "VIL intensity distribution — Z-score filtered (±2σ), raw values\n"
            "(grey = control reference; blue dashed line = swatch mean(μ); blue band = SD ±1σ",
            fontsize=9,
        )
        _fig_h.savefig(OUT_HIST / f"vil_kdecurve_{_row['id']}.pdf", dpi=150, bbox_inches="tight")
        _fig_h.savefig(OUT_HIST / f"vil_kdecurve_{_row['id']}.png", dpi=150, bbox_inches="tight")
        plt.close(_fig_h)

    # Hide unused subplot panels
    for _j in range(_i + 1, len(_axes2)):
        _axes2[_j].set_visible(False)

    _fig2.suptitle(
        "VIL intensity distributions — Z-score filtered (±2 σ), raw values\n"
        "(grey = control reference; blue dashed line = swatch mean(μ); blue band = SD ±1σ",
        fontsize=11, y=1.10, #title space
    )
    #---
    # adjust if needed (like plotting single variables, title misaligns)
    #    x=0.25,      # horizontal center
    #    y=1.10,     # vertical position
    #    ha="center"
    #---
        # -------------------------
        # SAVE PDF AND PNG
        # -------------------------
    _fig2.savefig(OUT_FIGS / "vil_kdecurves_all.pdf", dpi=150, bbox_inches="tight")
    _fig2.savefig(OUT_FIGS / "vil_kdecurves_all.png", dpi=150, bbox_inches="tight")
    plt.show()
    print("Saved: vil_kdecurves_all.pdf / .png | individuals → vil_kdecurve/")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **4./ FIGURE 3 — NORMALISED VIL SIGNAL BY SWATCH (bar chart)**

    Summarises each swatch's VIL response as a single value: **mean pixel value ÷ control mean × 100 %**.  This normalisation anchors all swatches to the same control reference, making results comparable across acquisition sessions where absolute illumination may differ.

    **Output:** `vil_comparison_bar.pdf/.png` in `vil_outputs_figures/`.

    **How to read:**
    - **100 %** (dashed horizontal line) = control baseline.  A bar at exactly 100 % means the swatch is indistinguishable from the control in mean luminescence.
    - **Above 100 %** — swatch is brighter than the control (stronger VIL signal); relevant for mixtures or stratigraphies that may concentrate or amplify luminescence.
    - **Below 100 %** — swatch is dimmer.  Bars at or below the ghost-signal threshold (dotted line, configurable via `GHOST_THRESHOLD_PCT`) indicate materials with negligible VIL response — these are the key ghost-pigment candidates for thesis discussion.
    - **Colours** represent variable groups; bars of the same colour should be read together to assess group-level trends.
    - The ghost-signal threshold is a **visual annotation only** — it does not filter any data.  Its value is set in the configuration cell and should reflect the detection limit established from the acquisition setup.
    """)
    return


@app.cell
def _(GROUP_COLOURS, OUT_FIGS, Patch, control_mean, df, plt):
    _pbar = df[df["file_found"] == True].copy()
    _fig3, _ax3 = plt.subplots(figsize=(14, 5))

    # std_raw is in raw pixel units; divide by control_mean × 100 to match the
    # bar height scale (% of control mean).  This is ±1 std of the pixel
    # distribution within each swatch — wide bars = uneven / heterogeneous swatch.
    _err = _pbar["std_raw"] / control_mean * 100

    # _ax3.bar(
    #     range(len(_pbar)),
    #     _pbar["normalised_signal_pct"],
    #     yerr=_err,
    #     color=[GROUP_COLOURS.get(g, "#888888") for g in _pbar["group"]],
    #     width=0.7, edgecolor="white", linewidth=0.5,
    #     error_kw=dict(ecolor="#222222", elinewidth=1.2, capsize=5, capthick=1.2),
    # )
    _ax3.bar(
        range(len(_pbar)),
        _pbar["normalised_signal_pct"],
        yerr=_err,
        color=[GROUP_COLOURS.get(g, "#888888") for g in _pbar["group"]],
        alpha=0.9,
        width=0.72,
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
        error_kw=dict(
            ecolor="dimgray",
            elinewidth=1.0,
            capsize=3,
            capthick=1.0,
        ),
    )
    # Control baseline
    _ax3.axhline(100, color="#333333", lw=0.8, ls="--", label="Control baseline (100%)")

    # Ghost-signal annotation line > ASK ROB REMOVE? OR CHECK VIL
    #_ax3.axhline(GHOST_THRESHOLD_PCT, color="r", lw=0.8, ls=":",
    #             label=f"Ghost-signal annotation ({GHOST_THRESHOLD_PCT}%)")
    # _ax3.text(
    #     len(_pbar) - 0.4, GHOST_THRESHOLD_PCT + 1.5,
    #     f"ghost threshold ({GHOST_THRESHOLD_PCT}%)",
    #     ha="left", va="bottom", fontsize=8, color="#C0392B", # change to right / purple covers text 
    # )

    _ax3.set_xticks(range(len(_pbar)))
    _ax3.set_xticklabels(_pbar["label"], rotation=45, ha="right", fontsize=9)
    _ax3.set_ylabel("VIL signal (% of control mean, raw units)", fontsize=10)
    _ax3.set_ylim(0, max(120, (_pbar["normalised_signal_pct"] + _err).max() + 10))
    _ax3.set_title(
        "Normalised VIL signal by mockup variable\n"
        "(bar = mean ÷ control mean × 100 ;  error bar = ±1 σ, Z-score filtered pixels)",
        fontsize=11, pad=10,
    )

    _leg3 = [Patch(facecolor=c, label=g) for g, c in GROUP_COLOURS.items()] + [
        plt.Line2D([0], [0], color="#333333", ls="--", label="Control baseline"),
        plt.Line2D([0], [0], color="#C0392B", ls=":"),]
                   # label=f"Ghost annotation ({GHOST_THRESHOLD_PCT}%)"),
    # _ax3.legend(handles=_leg3, loc="upper right", fontsize=8, framealpha=0.9)
    # plt.subplots_adjust(right=0.78)

    _fig3.legend(
        handles=_leg3,
        loc="upper left",
        bbox_to_anchor=(0.95, 0.5),
        fontsize=8,
        framealpha=0.9,
    )

    _fig3.subplots_adjust(right=0.78)

    #removes margin
    _ax3.spines["top"].set_visible(False)
    _ax3.spines["right"].set_visible(False)
    _ax3.grid(axis="y", alpha=0.15)

    plt.tight_layout()
    _fig3.savefig(OUT_FIGS / "vil_comparison_bar.pdf", dpi=150, bbox_inches="tight")
    _fig3.savefig(OUT_FIGS / "vil_comparison_bar.png", dpi=150, bbox_inches="tight")
    plt.show()
    print("Saved: vil_comparison_bar.pdf / .png")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **5./ TABLE 2 SUMMARY OF ANALYSES PER VARIABLE GROUP (print)**

    Aggregates and prints a comprehensive synthesis of all computed statistics, organised by variable group.  This is the human-readable summary of the full analysis pipeline — all key metrics from Cells 1–6 gathered in one place for quick review and thesis cross-referencing.

    **Output (printed):** for each group and swatch: normalised signal %, raw mean ± std, skewness, area fraction, Mann-Whitney U result (U, p, |r|), and ageing Δ if available.

    **How to interpret:** use this summary to identify patterns across groups:
    - **Pigment group** — compare swatches to assess which formulations produce the strongest VIL response relative to the control.  Swatches with high signal and low std are reliable VIL-active materials.
    - **Mixture group** — look for a concentration-dependent trend (e.g. 9:1, 1:1, 1:9 ratios): if signal scales monotonically with pigment concentration, this supports a linear response model that can be cited in the thesis.
    - **Stratigraphy group** — swatches with an overlay material should show reduced signal if the overlay absorbs or scatters VIL emission; the degree of signal attenuation informs how detectable the underlying pigment is through different coating layers.
    - **Alteration group** — cross-reference Δ values from Cell 6: swatches with large ageing-induced changes should also show altered summary statistics here.
    """)
    return


@app.cell
def _(CONTROL_ID, OUT_CSV, df, pd):
    print("── Summary overview per variable group ──\n")
    print(f"The control swatch ({CONTROL_ID}) was assigned 100% signal intensity. "
          f"All other swatches are expressed as a percentage of its whole-image mean.\n")
    def _():
        # -------------------------
        # Build TEXT report
        # -------------------------
        lines = []

        lines.append("── Summary overview per variable group ──\n")
        lines.append(
            f"The control swatch ({CONTROL_ID}) was assigned 100% signal intensity. "
            "All other swatches are expressed as a percentage of its whole-image mean.\n"
        )

        # -------------------------
        # Build STRUCTURED CSV rows
        # -------------------------
        rows = []

        for _group in ["Pigment", "Mixture", "Stratigraphy", "Alteration"]:
            _gdf = df[(df["group"] == _group) & (df["file_found"] == True)].copy()
            if _gdf.empty:
                continue

            _min_sig = _gdf["normalised_signal_pct"].min()
            _max_sig = _gdf["normalised_signal_pct"].max()
            _min_row = _gdf.loc[_gdf["normalised_signal_pct"].idxmin()]
              # -------------------------
              # PRINT TXT
              # -------------------------
            print(f"[{_group}]")
            print(f"  Normalised signal ranged from {_min_sig:.0f}% to {_max_sig:.0f}% of the control.")
            print(f"  Greatest attenuation: {_min_row['label']} ({_min_sig:.0f}% of control).")
            print()


            # ---- TXT section ----
            lines.append(f"[{_group}]")
            lines.append(
                f"  Normalised signal ranged from {_min_sig:.0f}% to {_max_sig:.0f}% of the control."
            )
            lines.append(
                f"  Greatest attenuation: {_min_row['label']} ({_min_sig:.0f}% of control)."
            )
            lines.append("")

            # ---- CSV structured row ----
            rows.append({
                "group": _group,
                "control_id": CONTROL_ID,
                "min_signal_pct": round(_min_sig, 2),
                "max_signal_pct": round(_max_sig, 2),
                "greatest_attenuation_label": _min_row["label"],
                "greatest_attenuation_pct": round(_min_sig, 2),
            })
        # -------------------------
        # SAVE TXT
        # -------------------------
        txt_output = "\n".join(lines)
        txt_path = OUT_CSV / "vil_luminescence_overview.txt"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_output)

        # -------------------------
        # SAVE CSV
        # -------------------------
        csv_df = pd.DataFrame(rows)
        csv_path = OUT_CSV / "vil_luminescence_overview.csv"
        csv_df.to_csv(csv_path, index=False)

        print(f"Saved TXT: {txt_path}")
        return print(f"Saved CSV: {csv_path}")


    _()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **6./ FIGURE 4 - BEFORE/AFTER AGEING COMPARISON (bar chart)**

    Computes a paired comparison of each swatch's normalised VIL signal **before** (unaged) and **after** (aged) artificial ageing, using the file pairs defined in `AGEING_PAIRS` in the configuration cell.  The same Z-score masking and channel extraction as the main analysis are applied to both timepoints so that results are directly comparable.

    For each pair the pipeline:
    1. Loads both TIFFs and applies the combined Z-score mask (pixels outlying in **either** image are excluded).
    2. Computes normalised signal (mean ÷ control mean × 100) for each timepoint.
    3. Calculates Δ = aged − unaged for the normalised signal and for raw mean.
    4. Produces a two-panel figure: left = grouped bars (before vs after per swatch); right = Δ signal (red = loss, green = gain).

    **Output:**
    - `vil_ageing_comparison.pdf/.png` — two-panel figure.
    - `vil_ageing_comparison.csv` — before / after / Δ columns, one row per swatch pair.

    **How to interpret:** a **negative Δ** means luminescence decreased after ageing — the material became less VIL-active under the accelerated ageing protocol.  A **positive Δ** indicates increased luminescence, which may reflect chemical transformation (e.g. formation of a new luminescent species).  Compare the magnitude of Δ across groups: pigments with large negative Δ are most sensitive to ageing; stratigraphies or mixtures near zero Δ are stable.  Add new pairs to `AGEING_PAIRS` in the configuration cell as aged TIFFs become available — no code changes are needed.
    """)
    return


@app.cell
def _(
    AGEING_PAIRS,
    CHANNEL,
    IMAGE_DIR,
    OUT_CSV,
    OUT_FIGS,
    compute_metrics,
    control_mean,
    find_file,
    load_channel,
    np,
    pd,
    plt,
):
    # AGEING_PAIRS is now defined in the configuration cell — edit it there.

    # ── Load and compute metrics for every pair ───────────────────────────────
    _ageing_records = []

    for _pair in AGEING_PAIRS:
        _unaged_path = find_file(IMAGE_DIR, _pair["unaged_file"])
        _aged_path   = find_file(IMAGE_DIR, _pair["aged_file"])

        if _unaged_path is None:
            print(f"  SKIP {_pair['id']}: unaged file '{_pair['unaged_file']}' not found")
            continue
        if _aged_path is None:
            print(f"  SKIP {_pair['id']}: aged file '{_pair['aged_file']}' not found")
            continue

        _img_u = load_channel(_unaged_path, CHANNEL)
        _img_a = load_channel(_aged_path,   CHANNEL)

        _met_u = compute_metrics(_img_u, control_mean)
        _met_a = compute_metrics(_img_a, control_mean)

        _delta_sig  = round(_met_a["normalised_signal_pct"] - _met_u["normalised_signal_pct"], 1)
        _delta_area = round(_met_a["area_fraction_pct"]     - _met_u["area_fraction_pct"],     2)
        _delta_mean = round(_met_a["mean_raw"]              - _met_u["mean_raw"],               2)
        _delta_skew = round(_met_a["skewness"]              - _met_u["skewness"],               3)

        print(
            f"  ok  {_pair['id']:12s}  "
            f"unaged={_unaged_path.name!r}  aged={_aged_path.name!r}"
        )
        print(
            f"       signal  unaged={_met_u['normalised_signal_pct']:.1f}%  "
            f"aged={_met_a['normalised_signal_pct']:.1f}%  Δ={_delta_sig:+.1f}%"
        )

        _ageing_records.append({
            "id":    _pair["id"],
            "label": _pair["label"],
            # ── unaged ──
            "unaged_mean_raw":              _met_u["mean_raw"],
            "unaged_normalised_signal_pct": _met_u["normalised_signal_pct"],
            "unaged_area_fraction_pct":     _met_u["area_fraction_pct"],
            "unaged_skewness":              _met_u["skewness"],
            # ── aged ──
            "aged_mean_raw":              _met_a["mean_raw"],
            "aged_normalised_signal_pct": _met_a["normalised_signal_pct"],
            "aged_area_fraction_pct":     _met_a["area_fraction_pct"],
            "aged_skewness":              _met_a["skewness"],
            # ── deltas (aged − unaged) ──
            "delta_normalised_signal_pct": _delta_sig,
            "delta_area_fraction_pct":     _delta_area,
            "delta_mean_raw":              _delta_mean,
            "delta_skewness":              _delta_skew,
        })

    if not _ageing_records:
        print("No complete ageing pairs found — add aged TIFF files to IMAGE_DIR.")
    else:
        # ── Save CSV ──────────────────────────────────────────────────────────
        _age_df   = pd.DataFrame(_ageing_records)
        _age_path = OUT_CSV / "vil_ageing_comparison.csv"
        _age_df.to_csv(_age_path, index=False)
        print(f"\nSaved: {_age_path}")

        # ── Figure: paired bar chart (signal) + delta bar chart ───────────────
        _n     = len(_ageing_records)
        _x     = np.arange(_n)
        _width = 0.35

        _fig6, (_ax6a, _ax6b) = plt.subplots(
            1, 2,
            figsize=(max(9, _n * 3 + 3), 5),
            constrained_layout=True,
        )

        # Panel a — grouped before / after bars
        _ax6a.bar(
            _x - _width / 2,
            [r["unaged_normalised_signal_pct"] for r in _ageing_records],
            _width, label="Before ageing", color="#4A90D9", edgecolor="white",
        )
        _ax6a.bar(
            _x + _width / 2,
            [r["aged_normalised_signal_pct"] for r in _ageing_records],
            _width, label="After ageing", color="#E07B3F",
            edgecolor="white", hatch="///",
        )
        _ax6a.axhline(100, color="#333333", lw=0.8, ls="--", label="Control (100%)")
        _ax6a.set_xticks(_x)
        _ax6a.set_xticklabels(
            [r["label"] for r in _ageing_records], rotation=30, ha="right", fontsize=9,
        )
        _ax6a.set_ylabel("VIL signal (% of control)", fontsize=10)
        _ax6a.set_title("Normalised VIL signal — before vs after ageing", fontsize=10)
        _ax6a.legend(fontsize=8)
        _ax6a.spines["top"].set_visible(False)
        _ax6a.spines["right"].set_visible(False)
        _ax6a.grid(axis="y", alpha=0.15)

        # Panel b — Δ signal (aged − unaged)
        _deltas  = [r["delta_normalised_signal_pct"] for r in _ageing_records]
        _colours = ["#C0392B" if d < 0 else "#27AE60" for d in _deltas]
        _ax6b.bar(_x, _deltas, 0.55, color=_colours, edgecolor="white")
        _ax6b.axhline(0, color="#333333", lw=0.8, ls="--")
        _ax6b.set_xticks(_x)
        _ax6b.set_xticklabels(
            [r["label"] for r in _ageing_records], rotation=30, ha="right", fontsize=9,
        )
        _ax6b.set_ylabel("Δ VIL signal (percentage points)", fontsize=10)
        _ax6b.set_title(
            "Change in VIL signal after ageing\n(red = loss, green = gain)", fontsize=10,
        )
        _ax6b.spines["top"].set_visible(False)
        _ax6b.spines["right"].set_visible(False)
        _ax6b.grid(axis="y", alpha=0.15)

        _fig6.suptitle(
            "Before / after ageing comparison — VIL signal (% of control, all pixels, raw values)",
            fontsize=11,
        )
        _fig6.savefig(OUT_FIGS / "vil_ageing_comparison.pdf", dpi=150, bbox_inches="tight")
        _fig6.savefig(OUT_FIGS / "vil_ageing_comparison.png", dpi=150, bbox_inches="tight")
        plt.show()
        print("Saved: vil_ageing_comparison.pdf / .png")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **7./ FIGURE 5 + TABLE 3 - BEFORE/AFTER AGEING: REGISTERED SWATCH DENSITY JOINTPLOT WITH MARGINAL KDE CURVES (variable group)**

    Plots joint density estimates of pixel-pair values (unaged vs aged) for each individual swatch TIFF pair listed in `AGEING_PAIRS`.  Because images are spatially registered, pixel (i, j) in the unaged image corresponds to the same physical location in the aged image — this is a true pixel-pair comparison, not a population comparison.  A combined Z-score mask excludes pixels outlying in either timepoint.  The sample budget (60 000 pairs total) is shared evenly across pairs so no single swatch dominates the pooled plot.

    The **unaged image is placed on the x-axis** (reference baseline): the diagonal y = x is then the natural no-change anchor, and any systematic shift away from it directly encodes the direction and magnitude of luminescence change.

    **Output:**
    - `vil_ageing_jointplot_grouped.pdf/.png` — all groups combined (combined panel in `vil_outputs_figures/`).
    - `vil_before-after_jointplot/vil_before-after_jointplot_{group}.pdf/.png` — one jointplot per variable group.
    - `vil_ageing_swatch_summary.csv` — Δmean and Δmedian per swatch pair.

    **How to interpret:**
    - **Density below the diagonal** — luminescence decreased after ageing; **above** = increased.
    - **Group-level patterns** — if all swatches within a group shift in the same direction, the result is robust and generalisable to the material class.  Mixed directions within a group suggest material-specific or application-dependent sensitivity to the ageing protocol.
    - **Contour concentration vs spread** — tight contours close to the diagonal indicate small, consistent change; a broad diffuse cloud suggests heterogeneous ageing effects across the swatch surface.
    - **Marginal KDEs** — a visible shift in the aged marginal (right axis) relative to the unaged (top axis) confirms the direction of change.
    - Report Δmean from the CSV alongside the visual direction of the joint density shift for each swatch in the thesis.  Extend `AGEING_PAIRS` in the configuration cell as new aged TIFFs become available; plots update automatically.
    """)
    return


@app.cell
def _(
    AGEING_PAIRS,
    CHANNEL,
    GROUP_COLOURS,
    HIST_XLIM,
    IMAGE_DIR,
    OUT_CSV,
    OUT_FIGS,
    OUT_JOINT,
    SWATCH_REGISTRY,
    find_file,
    load_channel,
    make_masked_image,
    np,
    pd,
    plt,
    sns,
):
    # ── Build paired pixel DataFrame from all registered swatch pairs ────────
    # Each row = one pixel location; columns = unaged value, aged value, group.
    # Combined Z-score mask excludes pixels that are outliers in EITHER image.
    # Sample budget shared evenly across pairs so no single swatch dominates.

    _BUDGET         = 60_000   # total pixel pairs across all swatches
    _rng8b          = np.random.default_rng(42)
    _chunks         = []
    _skipped        = []
    pairs_df_ageing = pd.DataFrame()   # exported so Cell 8c can reuse it

    for _pair in AGEING_PAIRS:
        _pu = find_file(IMAGE_DIR, _pair["unaged_file"])
        _pa = find_file(IMAGE_DIR, _pair["aged_file"])

        if _pu is None or _pa is None:
            _miss = _pair["unaged_file"] if _pu is None else _pair["aged_file"]
            print(f"  SKIP {_pair['id']}: '{_miss}' not found")
            _skipped.append(_pair["id"])
            continue

        _img_u = load_channel(_pu, CHANNEL).astype(float)
        _img_a = load_channel(_pa, CHANNEL).astype(float)

        if _img_u.shape != _img_a.shape:
            print(f"  SKIP {_pair['id']}: shape mismatch {_img_u.shape} vs {_img_a.shape}")
            _skipped.append(_pair["id"])
            continue

        # np.ma.getmaskarray always returns a full boolean array (not scalar False)
        _mask = (
            np.ma.getmaskarray(make_masked_image(_img_u)) |
            np.ma.getmaskarray(make_masked_image(_img_a))
        )
        _px_u = _img_u[~_mask].ravel()
        _px_a = _img_a[~_mask].ravel()
        _n    = len(_px_u)

        # Subsample this pair's share of the total budget
        _share = max(500, _BUDGET // max(len(AGEING_PAIRS), 1))
        if _n > _share:
            _idx  = _rng8b.choice(_n, _share, replace=False)
            _px_u = _px_u[_idx]
            _px_a = _px_a[_idx]

        _entry = next((s for s in SWATCH_REGISTRY if s["id"] == _pair["id"]), None)
        _group = _entry["group"] if _entry else "Unknown"

        _chunks.append(pd.DataFrame({
            "px_unaged": _px_u,
            "px_aged":   _px_a,
            "group":     _group,
            "label":     _pair["label"],
            "id":        _pair["id"],
        }))
        print(
            f"  ok  {_pair['id']:12s}  [{_group}]  "
            f"valid pairs={_n}  sampled={len(_px_u)}  "
            f"Δmean={float(_px_a.mean() - _px_u.mean()):+.1f} px"
        )

    if not _chunks:
        print(
            "No registered swatch pairs loaded.\n"
            "Add entries to AGEING_PAIRS in the configuration cell."
        )
    else:
        pairs_df_ageing = pd.concat(_chunks, ignore_index=True)

        # Groups actually present in the loaded data (in canonical order)
        _groups_present = [
            g for g in ["Pigment", "Mixture", "Stratigraphy", "Alteration"]
            if g in pairs_df_ageing["group"].values
        ]
        _palette = {g: GROUP_COLOURS.get(g, "#888888") for g in _groups_present}

        _lim = HIST_XLIM   # shared axis limits match the rest of the notebook

        # ── PLOT 1: all groups combined, coloured by group ───────────────────
        _g8b = sns.jointplot(
            data=pairs_df_ageing,
            x="px_unaged",
            y="px_aged",
            hue="group",
            hue_order=_groups_present,
            palette=_palette,
            kind="kde",
            joint_kws=dict(thresh=0.05, levels=6, alpha=0.75),
            marginal_kws=dict(fill=True, alpha=0.4, common_norm=False),
            height=7,
            ratio=5,
        )

        # Diagonal reference: y = x → no change after ageing
        _g8b.ax_joint.plot(
            _lim, _lim,
            color="#333333", lw=1.0, ls="--", alpha=0.6,
            label="No change (y = x)",
        )
        _g8b.ax_joint.set_xlim(*_lim)
        _g8b.ax_joint.set_ylim(*_lim)
        _g8b.ax_joint.set_xlabel("Pixel value — unaged (raw)", fontsize=10)
        _g8b.ax_joint.set_ylabel("Pixel value — aged (raw)", fontsize=10)
        _g8b.ax_joint.grid(alpha=0.10)

        _g8b.ax_marg_x.set_title(
            "VIL luminescence — registered swatch pairs, all groups\n"
            "(Z-score filtered  ;  diagonal = no change after ageing)",
            fontsize=10, pad=8,
        )

        _g8b.figure.savefig(
            OUT_FIGS / "vil_ageing_jointplot_grouped.pdf",
            dpi=150, bbox_inches="tight",
        )
        _g8b.figure.savefig(
            OUT_FIGS / "vil_ageing_jointplot_grouped.png",
            dpi=150, bbox_inches="tight",
        )
        plt.show()
        print("Saved: vil_ageing_jointplot_grouped.pdf / .png")

        # ── PLOT 2: one jointplot per group ──────────────────────────────────
        for _grp in _groups_present:
            _gdf  = pairs_df_ageing[pairs_df_ageing["group"] == _grp]
            _col  = GROUP_COLOURS.get(_grp, "#888888")
            _labels = _gdf["label"].unique().tolist()

            _g_grp = sns.jointplot(
                data=_gdf,
                x="px_unaged",
                y="px_aged",
                kind="kde",
                color=_col,
                joint_kws=dict(thresh=0.05, levels=6, fill=True, alpha=0.75),
                marginal_kws=dict(fill=True, alpha=0.5),
                height=6,
                ratio=5,
            )

            _g_grp.ax_joint.plot(
                _lim, _lim,
                color="#333333", lw=1.0, ls="--", alpha=0.6,
                label="No change",
            )
            _g_grp.ax_joint.set_xlim(*_lim)
            _g_grp.ax_joint.set_ylim(*_lim)
            _g_grp.ax_joint.set_xlabel("Pixel value — unaged (raw)", fontsize=10)
            _g_grp.ax_joint.set_ylabel("Pixel value — aged (raw)", fontsize=10)
            _g_grp.ax_joint.grid(alpha=0.10)
            _g_grp.ax_joint.legend(fontsize=8, frameon=False)

            _g_grp.ax_marg_x.set_title(
                f"VIL ageing — {_grp}  ({', '.join(_labels)})\n"
                "(Z-score filtered ; diagonal = no change)",
                fontsize=9, pad=8,
            )

            _slug = _grp.lower()
            _g_grp.figure.savefig(
                OUT_JOINT / f"vil_before-after_jointplot_{_slug}.pdf",
                dpi=150, bbox_inches="tight",
            )
            _g_grp.figure.savefig(
                OUT_JOINT / f"vil_before-after_jointplot_{_slug}.png",
                dpi=150, bbox_inches="tight",
            )
            plt.show()
            print(f"Saved: vil_before-after_jointplot_{_slug}.pdf / .png  → vil_before-after_jointplot/")

        # ── Summary CSV: Δmean and Δmedian per swatch ───────────────────────
        _sum_rows = []
        for _pair in AGEING_PAIRS:
            if _pair["id"] in _skipped:
                continue
            _sdf = pairs_df_ageing[pairs_df_ageing["id"] == _pair["id"]]
            _sum_rows.append({
                "id":            _pair["id"],
                "label":         _pair["label"],
                "group":         _sdf["group"].iloc[0],
                "n_pairs":       len(_sdf),
                "mean_unaged":   round(float(_sdf["px_unaged"].mean()), 2),
                "mean_aged":     round(float(_sdf["px_aged"].mean()),   2),
                "delta_mean":    round(float(_sdf["px_aged"].mean() - _sdf["px_unaged"].mean()), 2),
                "median_unaged": round(float(_sdf["px_unaged"].median()), 2),
                "median_aged":   round(float(_sdf["px_aged"].median()),   2),
                "delta_median":  round(float(_sdf["px_aged"].median() - _sdf["px_unaged"].median()), 2),
            })
        _sum_df = pd.DataFrame(_sum_rows)
        _sum_path = OUT_CSV / "vil_ageing_swatch_summary.csv"
        _sum_df.to_csv(_sum_path, index=False)
        print(f"\nSaved: {_sum_path}")
        print(_sum_df.to_string(index=False))
    return (pairs_df_ageing,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **7.1./ FIGURE 6 - BEFORE/AFTER AGEING: REGISTERED SWATCH DENSITY JOINTPLOT WITH MARGINAL KDE CURVES (individual subgroup separated)**

    Same registered pixel pairs as Cell 8b, re-plotted with each **individual swatch assigned a unique colour** so that subgroups within the same variable group can be distinguished — for example, different EB formulations within the Pigment group, or different concentration ratios within the Mixture group.

    **Output:**
    - `vil_ageing_jointplot_perswatch.pdf/.png` — all swatches combined, one colour per swatch label (combined panel in `vil_outputs_figures/`).
    - `vil_before-after_jointplot/vil_before-after_jointplot_{group}_perswatch.pdf/.png` — one jointplot per group with swatch-level colour coding.

    **How to interpret:**
    - **Plot 1 (all swatches combined)** — use as a quick overview of overall spread and directionality.  Overlapping contours of different colours near the diagonal indicate similar ageing behaviour across swatches; diverging contours indicate material-specific responses.
    - **Plot 2 (per group)** — the more analytically useful view.  Within a group, swatches whose contours cluster together respond similarly to ageing; isolated contours indicate outlier behaviour worth investigating.  For the Mixture group, check whether concentration ratios (8:1, 1:1, 1:8) produce systematically different shifts — a dose-response relationship would be an important finding.
    - Both plots use the same pixel-pair data as Cell 8b; the diagonal, axis limits, and Z-score masking are identical.  These figures are complementary to the group-level plots in 8b and should be cited together in the thesis when discussing within-group variability.
    """)
    return


@app.cell
def _(HIST_XLIM, OUT_FIGS, OUT_JOINT, pairs_df_ageing, plt, sns):
    if pairs_df_ageing.empty:
        print("No ageing data — run Cell 8b first (check AGEING_PAIRS config).")
    else:
        _lim = HIST_XLIM

        # Consistent colour per label across all plots in this cell
        _all_labels    = pairs_df_ageing["label"].unique().tolist()
        _label_palette = dict(
            zip(_all_labels, sns.color_palette("tab10", len(_all_labels)))
        )

        _groups_present = [
            g for g in ["Pigment", "Mixture", "Stratigraphy", "Alteration"]
            if g in pairs_df_ageing["group"].values
        ]

        # ── PLOT 1: all swatches combined, one colour per label ──────────────
        _g8c = sns.jointplot(
            data=pairs_df_ageing,
            x="px_unaged",
            y="px_aged",
            hue="label",
            hue_order=_all_labels,
            palette=_label_palette,
            kind="kde",
            joint_kws=dict(thresh=0.05, levels=5, alpha=0.60),
            marginal_kws=dict(fill=True, alpha=0.25, common_norm=False),
            height=7,
            ratio=5,
        )

        # Legend title and position
        if _g8c.ax_joint.legend_ is not None:
            _g8c.ax_joint.legend_.set_title("Colour legend")
            sns.move_legend(
                _g8c.ax_joint,
                "upper left",
                bbox_to_anchor=(1.2, 1),
                frameon=True,
            )

        _g8c.figure.subplots_adjust(right=0.80)
    
        _g8c.ax_joint.plot(
            _lim, _lim,
            color="#333333", lw=1.0, ls="--", alpha=0.6, label="No change (y = x)",
        )
        _g8c.ax_joint.set_xlim(*_lim)
        _g8c.ax_joint.set_ylim(*_lim)
        _g8c.ax_joint.set_xlabel("Pixel value — unaged (raw)", fontsize=10)
        _g8c.ax_joint.set_ylabel("Pixel value — aged (raw)", fontsize=10)
        _g8c.ax_joint.grid(alpha=0.10)
        _g8c.ax_marg_x.set_title(
            "VIL luminescence — all swatches, per-swatch colour\n"
            "(Z-score filtered  ;  diagonal = no change after ageing)",
            fontsize=10, pad=8,
        )
        _g8c.figure.savefig(
            OUT_FIGS / "vil_ageing_jointplot_perswatch.pdf",
            dpi=150, bbox_inches="tight",
        )
        _g8c.figure.savefig(
            OUT_FIGS / "vil_ageing_jointplot_perswatch.png",
            dpi=150, bbox_inches="tight",
        )
        plt.show()
        print("Saved: vil_ageing_jointplot_perswatch.pdf / .png")

        # ── PLOT 2: one jointplot per group, swatches coloured individually ──
        for _grp in _groups_present:
            _gdf           = pairs_df_ageing[pairs_df_ageing["group"] == _grp]
            _labels_in_grp = _gdf["label"].unique().tolist()
            _pal           = {lbl: _label_palette[lbl] for lbl in _labels_in_grp}

            _g_grp = sns.jointplot(
                data=_gdf,
                x="px_unaged",
                y="px_aged",
                hue="label",
                hue_order=_labels_in_grp,
                palette=_pal,
                kind="kde",
                joint_kws=dict(thresh=0.05, levels=6, alpha=0.75),
                marginal_kws=dict(fill=True, alpha=0.4, common_norm=False),
                height=6,
                ratio=5,
            )

            # Legend title and position
            if _g_grp.ax_joint.legend_ is not None:
                _g_grp.ax_joint.legend_.set_title("Colour legend")
            #     sns.move_legend(
            #         _g_grp.ax_joint,
            #         "upper left",
            #         bbox_to_anchor=(1.05, 1),
            #         frameon=True,
            #     )

            # _g_grp.figure.subplots_adjust(right=0.80)

            _g_grp.ax_joint.plot(
                _lim, _lim,
                color="#333333", lw=1.0, ls="--", alpha=0.6, label="No change",
            )
            _g_grp.ax_joint.set_xlim(*_lim)
            _g_grp.ax_joint.set_ylim(*_lim)
            _g_grp.ax_joint.set_xlabel("Pixel value — unaged (raw)", fontsize=10)
            _g_grp.ax_joint.set_ylabel("Pixel value — aged (raw)", fontsize=10)
            _g_grp.ax_joint.grid(alpha=0.10)
            _g_grp.ax_marg_x.set_title(
                f"VIL ageing — {_grp}  (per swatch)\n"
                "(Z-score filtered  ;  diagonal = no change)",
                fontsize=9, pad=8,
            )

            _slug = _grp.lower()
            _g_grp.figure.savefig(
                OUT_JOINT / f"vil_before-after_jointplot_{_slug}_perswatch.pdf",
                dpi=150, bbox_inches="tight",
            )
            _g_grp.figure.savefig(
                OUT_JOINT / f"vil_before-after_jointplot_{_slug}_perswatch.png",
                dpi=150, bbox_inches="tight",
            )
            plt.show()
            print(f"Saved: vil_before-after_jointplot_{_slug}_perswatch.pdf / .png  → vil_before-after_jointplot/")
    return


if __name__ == "__main__":
    app.run()
