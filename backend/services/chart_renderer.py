"""
chart_renderer.py
─────────────────
Implements the Graph-Type Decision Map.

Decision rules (keyword → chart type):
  gender / sex            → pie
  marital                 → pie
  age / education / qual  → bar (vertical)
  concern / level / satis → stacked_bar
  cross / crosstab / xtab → grouped_bar  (or heatmap if large)
  rank / statement/reason → horizontal_bar
  symbol-only instruction → symbol_label  (text annotation, no chart)
  fallback                → bar

Each function returns the absolute path to a PNG image.
"""

import os
import re
import textwrap
from typing import Dict, Any, Optional

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless rendering
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Decision map keywords ──────────────────────────────────────────────────────
DECISION_MAP = [
    (re.compile(r"\b(gender|sex)\b", re.I),                   "pie"),
    (re.compile(r"\b(marital|married|single)\b", re.I),        "pie"),
    (re.compile(r"\b(age|education|edu|qual|qualification)\b", re.I), "bar"),
    (re.compile(r"\b(concern|level|satisfaction|rating)\b", re.I),    "stacked_bar"),
    (re.compile(r"\b(cross|crosstab|x[-\s]?tab|pivot)\b", re.I),      "grouped_bar"),
    (re.compile(r"\b(rank|ranked|statement|reason|why)\b", re.I),     "horizontal_bar"),
]
SYMBOL_RE = re.compile(r"^[\s↑↓→←▲▼◀▶⬆⬇⬅➡★☆✓✗✔✘%#@&\*\+\-=<>!?~^|•·…]+$")

PALETTE = ["#6C63FF", "#48CFAD", "#F7C948", "#FF6B6B", "#5DADE2",
           "#A3CB38", "#FF8C00", "#EC407A", "#26C6DA", "#AB47BC"]


def decide_chart_type(raw_text: str, instr_type: str) -> str:
    if instr_type == "symbol" or SYMBOL_RE.match(raw_text.strip()):
        return "symbol_label"
    for pattern, chart_type in DECISION_MAP:
        if pattern.search(raw_text):
            return chart_type
    return "bar"  # fallback


# ── Label & Value Extractors ───────────────────────────────────────────────────

def _labels_values(data: Optional[Dict]) -> tuple:
    """Extract labels and numeric values from matched data dict, filtering out base rows."""
    if not data:
        labels = ["A", "B", "C", "D", "E"]
        values = [30, 25, 20, 15, 10]
        return labels, values

    cols = list(data.keys())
    labels_raw = data[cols[0]]
    
    # Identify column to plot (Total or first numeric column after Label)
    val_col = "Total" if "Total" in cols else (cols[1] if len(cols) > 1 else cols[0])
    values_raw = data[val_col]

    labels = []
    values = []

    for lbl, val in zip(labels_raw, values_raw):
        lbl_str = str(lbl).strip()
        # Exclude base/sample size rows
        if "base:" in lbl_str.lower():
            continue
        labels.append(lbl_str)
        
        # Clean and scale value
        try:
            v_num = float(val) if val is not None and not pd.isna(val) else 0.0
            # If values are proportions (between 0 and 1), scale to percentages
            if v_num > 0 and v_num <= 1.0:
                v_num *= 100.0
            values.append(v_num)
        except Exception:
            values.append(0.0)

    # limit to top 10 categories to avoid clutter
    return labels[:10], values[:10]


def _style_fig(fig, ax, title: str):
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.tick_params(colors="white", labelsize=8)
    ax.spines["bottom"].set_color("#444")
    ax.spines["left"].set_color("#444")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(textwrap.fill(title, 40), color="white", fontsize=9, pad=8)


# ── Renderers ──────────────────────────────────────────────────────────────────

def render_pie(data, title: str, out_path: str):
    labels, values = _labels_values(data)
    fig, ax = plt.subplots(figsize=(5, 4), dpi=120)
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.1f%%",
        colors=PALETTE[:len(values)], startangle=90,
        textprops={"color": "white", "fontsize": 8},
        wedgeprops={"edgecolor": "#1a1a2e", "linewidth": 1.5},
    )
    for at in autotexts:
        at.set_color("white")
    ax.set_title(textwrap.fill(title, 40), color="white", fontsize=9, pad=8)
    fig.patch.set_facecolor("#1a1a2e")
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)


def render_bar(data, title: str, out_path: str):
    labels, values = _labels_values(data)
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    bars = ax.bar(range(len(labels)), values, color=PALETTE[:len(values)],
                  edgecolor="#1a1a2e", linewidth=1.2)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right", color="white", fontsize=7)
    ax.set_ylabel("Percentage (%)", color="white", fontsize=8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{val:.1f}%" if val > 0 else "0%", ha="center", va="bottom", color="white", fontsize=7)
    _style_fig(fig, ax, title)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)


def render_horizontal_bar(data, title: str, out_path: str):
    labels, values = _labels_values(data)
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    y_pos = range(len(labels))
    bars = ax.barh(y_pos, values, color=PALETTE[:len(values)], edgecolor="#1a1a2e")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color="white", fontsize=7)
    ax.set_xlabel("Percentage (%)", color="white", fontsize=8)
    
    # Add values on the bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}%" if val > 0 else "0%", ha="left", va="center", color="white", fontsize=7)
                
    _style_fig(fig, ax, title)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)


def render_stacked_bar(data, title: str, out_path: str):
    import pandas as pd
    if data and len(data) >= 3:
        # Extract row labels, filter out base rows
        cols = list(data.keys())
        lbls_raw = data[cols[0]]
        
        # Series: keep only valid breakdown categories (e.g. columns containing Age or Gender)
        valid_cols = [c for c in cols[1:] if "total" not in c.lower()]
        if not valid_cols:
            valid_cols = cols[1:6] # fallback
            
        labels = [str(l) for l, v in zip(lbls_raw, data[cols[0]]) if "base:" not in str(l).lower()][:8]
        
        series = {}
        for c in valid_cols[:5]:
            vals = []
            for l, val in zip(lbls_raw, data[c]):
                if "base:" in str(l).lower():
                    continue
                try:
                    v_num = float(val) if val is not None and not pd.isna(val) else 0.0
                    if v_num > 0 and v_num <= 1.0:
                        v_num *= 100.0
                    vals.append(v_num)
                except Exception:
                    vals.append(0.0)
            series[c] = vals[:8]
    else:
        labels = ["Q1", "Q2", "Q3", "Q4", "Q5"]
        series = {
            "Strongly Agree": [40, 35, 50, 45, 30],
            "Agree": [30, 25, 20, 25, 35],
            "Neutral": [15, 20, 15, 15, 20],
            "Disagree": [10, 15, 10, 10, 10],
            "Strongly Disagree": [5, 5, 5, 5, 5],
        }
        
    fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
    bottom = np.zeros(len(labels))
    for i, (name, vals) in enumerate(series.items()):
        # Pad values if length mismatch
        if len(vals) < len(labels):
            vals = vals + [0.0] * (len(labels) - len(vals))
        ax.bar(range(len(labels)), vals[:len(labels)], bottom=bottom,
               label=name, color=PALETTE[i % len(PALETTE)], edgecolor="#1a1a2e")
        bottom += np.array(vals[:len(labels)])
        
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right", color="white", fontsize=7)
    ax.legend(loc="upper right", fontsize=6, facecolor="#222", labelcolor="white")
    _style_fig(fig, ax, title)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)


def render_grouped_bar(data, title: str, out_path: str):
    import pandas as pd
    if data and len(data) >= 3:
        cols = list(data.keys())
        lbls_raw = data[cols[0]]
        
        valid_cols = [c for c in cols[1:] if "total" not in c.lower()]
        if not valid_cols:
            valid_cols = cols[1:4]
            
        labels = [str(l) for l, v in zip(lbls_raw, data[cols[0]]) if "base:" not in str(l).lower()][:8]
        
        groups = {}
        for c in valid_cols[:3]:
            vals = []
            for l, val in zip(lbls_raw, data[c]):
                if "base:" in str(l).lower():
                    continue
                try:
                    v_num = float(val) if val is not None and not pd.isna(val) else 0.0
                    if v_num > 0 and v_num <= 1.0:
                        v_num *= 100.0
                    vals.append(v_num)
                except Exception:
                    vals.append(0.0)
            groups[c] = vals[:8]
    else:
        labels = ["G1", "G2", "G3", "G4"]
        groups = {"Group A": [20, 35, 30, 25], "Group B": [25, 30, 35, 20]}

    x = np.arange(len(labels))
    n = len(groups)
    width = 0.7 / n
    fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
    for i, (name, vals) in enumerate(groups.items()):
        if len(vals) < len(labels):
            vals = vals + [0.0] * (len(labels) - len(vals))
        ax.bar(x + i * width - (n - 1) * width / 2, vals[:len(labels)],
               width=width, label=name, color=PALETTE[i % len(PALETTE)])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right", color="white", fontsize=7)
    ax.legend(fontsize=6, facecolor="#222", labelcolor="white")
    _style_fig(fig, ax, title)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)


def render_symbol_label(raw_text: str, out_path: str):
    """Render a symbolic instruction as a styled text image."""
    fig, ax = plt.subplots(figsize=(3, 2), dpi=120)
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.axis("off")
    ax.text(0.5, 0.5, raw_text.strip(), transform=ax.transAxes,
            ha="center", va="center", fontsize=32, color="#F7C948",
            fontweight="bold")
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)


# ── Dispatcher ─────────────────────────────────────────────────────────────────
def render_chart(
    match_result: Dict[str, Any],
    out_dir: str,
) -> str:
    """
    Decide chart type and render it.
    Returns the absolute path to the generated PNG.
    """
    raw_text = match_result["raw_text"]
    instr_type = match_result["type"]
    matched_data = match_result.get("matched_table_data")
    title = match_result.get("matched_table") or raw_text[:50]

    chart_type = decide_chart_type(raw_text, instr_type)
    safe_id = f"slide{match_result['slide_number']}_shape{match_result['shape_id']}"
    out_path = os.path.join(out_dir, f"{safe_id}_{chart_type}.png")

    if chart_type == "pie":
        render_pie(matched_data, title, out_path)
    elif chart_type == "bar":
        render_bar(matched_data, title, out_path)
    elif chart_type == "horizontal_bar":
        render_horizontal_bar(matched_data, title, out_path)
    elif chart_type == "stacked_bar":
        render_stacked_bar(matched_data, title, out_path)
    elif chart_type == "grouped_bar":
        render_grouped_bar(matched_data, title, out_path)
    elif chart_type == "symbol_label":
        render_symbol_label(raw_text, out_path)
    else:
        render_bar(matched_data, title, out_path)

    return out_path
