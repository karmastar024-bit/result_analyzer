"""Shared chart specifications rendered interactively or into PDF images."""

from dataclasses import dataclass
from io import BytesIO
import textwrap
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import gaussian_kde
from core.subjects_config import COLORS, PASS_PERCENT


@dataclass
class Chart:
    """Portable chart definition: screen and PDF share exactly the same data."""

    title: str
    kind: str
    data: pd.DataFrame
    x: str = ""
    y: str = ""
    group: str | None = None
    pass_line: bool = False


def interactive(chart: Chart) -> go.Figure:
    """Plotly figures with readable labels and explicit numerical hover data."""
    d = chart.data
    if chart.kind == "distribution":
        values = d[chart.x].dropna()
        fig = go.Figure(
            go.Histogram(
                x=values,
                xbins=dict(start=0, end=100, size=10),
                name="Students",
                marker_color="#3288D1",
                hovertemplate="Score bin %{x}%<br>Students %{y}<extra></extra>",
            )
        )
        if len(values) >= 2 and values.nunique() > 1:
            grid = np.linspace(0, 100, 250)
            density = gaussian_kde(values)(grid) * len(values) * 10
            fig.add_trace(
                go.Scatter(
                    x=grid, y=density, name="KDE (count scale)", line_color="#D84B9B"
                )
            )
        for name, val, color in [
            ("Mean", values.mean(), "#2C9B73"),
            ("Median", values.median(), "#E88A32"),
        ]:
            if pd.notna(val):
                fig.add_vline(
                    x=val,
                    line_color=color,
                    annotation_text=f"{name} {val:.2f}",
                    annotation_position="top left"
                    if name == "Mean"
                    else "bottom right",
                )
        fig.add_vrect(
            x0=0, x1=PASS_PERCENT, fillcolor="red", opacity=0.08, line_width=0
        )
        fig.update_xaxes(title="Score (%)", range=[0, 100])
        fig.update_yaxes(title="Students (KDE scaled to bin counts)")
    elif chart.kind == "heatmap":
        fig = px.imshow(
            d,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="Blues",
            labels={
                "x": d.columns.name or "Subject",
                "y": d.index.name or "Section",
                "color": chart.y,
            },
        )
    elif chart.kind == "box":
        fig = px.box(
            d,
            x=chart.x,
            y=chart.y,
            color=chart.group,
            points="outliers",
            color_discrete_map=COLORS,
            labels={chart.y: "Score (%)"},
        )
    else:
        fig = px.bar(
            d,
            x=chart.x,
            y=chart.y,
            color=chart.group,
            barmode="group",
            text_auto=".2f",
            color_discrete_map=COLORS,
            hover_data={c: ":.2f" for c in d.select_dtypes("number").columns},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=dict(text=chart.title, font_size=18),
        template="plotly_dark",
        paper_bgcolor="#142c3d",
        plot_bgcolor="#142c3d",
        margin=dict(t=80, b=100),
        legend_title_text=chart.group or "",
        font=dict(size=13, color="#d5e3ea", family="Source Sans 3, sans-serif"),
        colorway=["#75b8c7", "#d9b477", "#a3e1d2", "#a89cdb"],
        height=470,
    )
    fig.update_xaxes(showgrid=False, automargin=True, title_standoff=18)
    fig.update_yaxes(
        gridcolor="#314958", zerolinecolor="#496170", automargin=True, title_standoff=18
    )
    if chart.pass_line:
        fig.add_hline(
            y=PASS_PERCENT,
            line_dash="dash",
            line_color="#C13B43",
            annotation_text="Pass threshold 40%",
        )
    return fig


def image_bytes(chart: Chart) -> bytes:
    """Render a static counterpart with matplotlib, without a browser dependency."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from core.pdf_report import font_path
    from matplotlib.font_manager import FontProperties

    font = FontProperties(fname=str(font_path())) if font_path() else None
    with plt.rc_context({"font.size": 10}):
        fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
        d = chart.data
        if chart.kind == "distribution":
            values = d[chart.x].dropna()
            ax.hist(
                values, bins=np.arange(0, 101, 10), color="#3288D1", edgecolor="white"
            )
            if len(values) >= 2 and values.nunique() > 1:
                grid = np.linspace(0, 100, 250)
                ax.plot(
                    grid,
                    gaussian_kde(values)(grid) * len(values) * 10,
                    color="#D84B9B",
                    label="KDE",
                )
            for name, value, color in [
                ("Mean", values.mean(), "#2C9B73"),
                ("Median", values.median(), "#E88A32"),
            ]:
                if pd.notna(value):
                    ax.axvline(value, color=color, label=f"{name} {value:.2f}")
            ax.axvspan(0, PASS_PERCENT, color="red", alpha=0.08)
            ax.set(xlabel="Score (%)", ylabel="Students", xlim=(0, 100))
            if len(values):
                ax.legend(fontsize=8)
        elif chart.kind == "heatmap":
            array = d.to_numpy(dtype=float)
            image = ax.imshow(np.ma.masked_invalid(array), aspect="auto", cmap="Blues")
            fig.colorbar(image, ax=ax, label=chart.y)
            ax.set_xticks(
                range(len(d.columns)),
                [textwrap.fill(str(c), 16) for c in d.columns],
                rotation=30,
                ha="right",
            )
            ax.set_yticks(range(len(d)), d.index)
            for r in range(len(d)):
                for c in range(len(d.columns)):
                    ax.text(
                        c,
                        r,
                        f"{array[r, c]:.2f}" if np.isfinite(array[r, c]) else "NA",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white"
                        if np.isfinite(array[r, c]) and image.norm(array[r, c]) > 0.55
                        else "black",
                    )
            ax.set(xlabel="Subject", ylabel="Section")
        elif chart.kind == "box":
            labels = list(d[chart.x].unique())
            arrays = [
                d.loc[d[chart.x].eq(v), chart.y].dropna().to_numpy() for v in labels
            ]
            ax.boxplot(arrays, tick_labels=[textwrap.fill(str(x), 16) for x in labels])
            ax.set(xlabel=chart.x, ylabel="Score (%)")
        else:
            if chart.group:
                pivot = d.pivot(index=chart.x, columns=chart.group, values=chart.y)
            else:
                pivot = d.set_index(chart.x)[[chart.y]]
            x = np.arange(len(pivot))
            width = 0.8 / max(1, len(pivot.columns))
            for j, group in enumerate(pivot.columns):
                values = pivot[group].to_numpy(dtype=float)
                bars = ax.bar(
                    x - 0.4 + width / 2 + j * width,
                    values,
                    width,
                    label=str(group),
                    color=COLORS.get(group),
                )
                ax.bar_label(
                    bars,
                    labels=[f"{v:.2f}" if np.isfinite(v) else "" for v in values],
                    fontsize=7,
                    padding=2,
                )
            ax.set_xticks(
                x,
                [textwrap.fill(str(v), 16) for v in pivot.index],
                rotation=25,
                ha="right",
            )
            ax.set(xlabel=chart.x, ylabel=chart.y)
            if chart.group:
                ax.legend(fontsize=8)
            ax.margins(y=0.2)
        if chart.pass_line:
            ax.axhline(PASS_PERCENT, color="#C13B43", linestyle="--", label="40% pass")
        ax.set_title(textwrap.fill(chart.title, 85), fontsize=12, fontproperties=font)
        if font:
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontproperties(font)
        output = BytesIO()
        fig.savefig(output, format="png", dpi=140)
        plt.close(fig)
        return output.getvalue()
