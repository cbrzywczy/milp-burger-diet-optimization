"""
Generuje wszystkie tabele LaTeX i wykresy PDF z wyników solver'a + menu + norm.

Wejście:
- projekt/wyniki/results.json   (output solve_local.py)
- projekt/menu.csv
- projekt/normy.csv

Wyjście:
- projekt/latex/tables/tab_*.tex
- projekt/latex/figures/fig_*.pdf
"""

from __future__ import annotations
import csv, json, pathlib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from scipy.optimize import milp, LinearConstraint, Bounds

matplotlib.rcParams.update(
    {
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{lmodern}\usepackage[polish]{babel}",
        "font.family": "serif",
        "font.serif": ["Computer Modern Roman"],
        "axes.unicode_minus": True,
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.edgecolor": "#444",
        "axes.linewidth": 0.7,
        "axes.grid": False,
        "savefig.bbox": "tight",
        "savefig.dpi": 220,
    }
)


def pl(x, dec=2):
    """Format liczby w stylu PL: 24,99."""
    if x is None:
        return "--"
    s = f"{x:.{dec}f}"
    return s.replace(".", ",")


SOURCE_NOTE = "\n\\par\\smallskip\n{\\footnotesize Źródło: opracowanie własne.}\n"

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = json.loads((ROOT / "wyniki" / "results.json").read_text())
MENU_ROWS = list(csv.DictReader(open(ROOT / "menu.csv")))
MENU = {r["id"]: r for r in MENU_ROWS}
NORMS = {r["skladnik"]: r for r in csv.DictReader(open(ROOT / "normy.csv"))}
FIG = ROOT / "latex" / "figures"
TAB = ROOT / "latex" / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

KATEGORIA_PL = {
    "burger": "burger (wołowina)",
    "burger_kura": "burger (kurczak)",
    "wypasik": "wypasik",
    "wlap": "włap",
    "side": "dodatek",
    "napoj": "napój",
    "deser": "deser",
    "zestaw": "zestaw combo",
    "bundle": "box / mega deal",
}

KATEGORIA_ORDER = [
    "burger",
    "burger_kura",
    "wypasik",
    "wlap",
    "side",
    "napoj",
    "deser",
    "zestaw",
    "bundle",
]


def esc(s: str) -> str:
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


# ============== TABELE ==============


def tab_menu_summary():
    by = {}
    for r in MENU_ROWS:
        d = by.setdefault(r["kategoria"], {"n": 0, "ceny": [], "kcal": []})
        d["n"] += 1
        d["ceny"].append(float(r["cena_pln"]))
        d["kcal"].append(float(r["kcal"]))
    rows = []
    for kat in KATEGORIA_ORDER:
        if kat not in by:
            continue
        d = by[kat]
        rows.append(
            (
                KATEGORIA_PL[kat],
                d["n"],
                f"{pl(min(d['ceny']))}--{pl(max(d['ceny']))}",
                pl(sum(d["ceny"]) / len(d["ceny"])),
                f"{int(min(d['kcal']))}--{int(max(d['kcal']))}",
            )
        )
    body = "\n".join(
        f"{esc(r[0])} & {r[1]} & {r[2]} & {r[3]} & {r[4]} \\\\" for r in rows
    )
    tex = (
        r"\begin{table}[H]\centering"
        r"\caption{Podsumowanie menu Pasibus wg kategorii (ceny Uber Eats, maj 2026).}"
        r"\label{tab:menu_summary}"
        r"\begin{tabular}{lrccc}\toprule "
        r"Kategoria & Liczba pozycji & Ceny [zł] & Średnia [zł] & Kcal/porcja \\\midrule "
        + body
        + r"\bottomrule\end{tabular}"
        + SOURCE_NOTE
        + r"\end{table}"
    )
    (TAB / "tab_01_menu_summary.tex").write_text(tex)


def tab_norms():
    skl_pl = {
        "kcal": "Kalorie [kcal]",
        "bialko": "Białko [g]",
        "tluszcz": "Tłuszcz [g]",
        "nasycone": "Nasycone [g]",
        "wegle": "Węglowodany [g]",
        "blonnik": "Błonnik [g]",
        "cukier": "Cukry wolne [g]",
        "sol": "Sól [g]",
        "kofeina": "Kofeina [mg]",
    }
    rows = [
        (
            label,
            f"{NORMS[k]['M_min']}--{NORMS[k]['M_max']}",
            f"{NORMS[k]['K_min']}--{NORMS[k]['K_max']}",
        )
        for k, label in skl_pl.items()
    ]
    body = "\n".join(f"{esc(r[0])} & {r[1]} & {r[2]} \\\\" for r in rows)
    tex = (
        r"\begin{table}[H]\centering"
        r"\caption{Widełki dziennego zapotrzebowania (IŻŻ, EFSA, WHO).}\label{tab:norms}"
        r"\begin{tabular}{lcc}\toprule "
        r"Składnik & Mężczyzna (M) & Kobieta (K) \\\midrule "
        + body
        + r"\bottomrule\end{tabular}"
        + SOURCE_NOTE
        + r"\end{table}"
    )
    (TAB / "tab_02_norms.tex").write_text(tex)


def tab_solution(label, fname, tex_label, caption):
    d = RES[label]
    if not d.get("picks"):
        tex = (
            r"\begin{table}[H]\centering"
            rf"\caption{{{caption}}}\label{{tab:{tex_label}}}"
            r"\begin{tabular}{l}\toprule \textit{Problem niewykonalny -- patrz Tabela~\ref{tab:diagnostic}.} \\\bottomrule\end{tabular}\end{table}"
        )
        (TAB / fname).write_text(tex)
        return
    picks_sorted = sorted(d["picks"], key=lambda x: -x["x"] * x["cena"])
    rows = []
    for p in picks_sorted:
        m = MENU[p["id"]]
        rows.append(
            (
                m["nazwa"],
                KATEGORIA_PL.get(m["kategoria"], m["kategoria"]),
                int(p["x"]),
                pl(p["cena"]),
                pl(p["x"] * p["cena"]),
            )
        )
    body = "\n".join(
        f"{esc(r[0])} & {esc(r[1])} & {r[2]} & {r[3]} & {r[4]} \\\\" for r in rows
    )
    body += f"\n\\midrule \\multicolumn{{4}}{{r}}{{Razem}} & {pl(d['obj'])} \\\\"
    tex = (
        r"\begin{table}[H]\centering"
        rf"\caption{{{caption}}}\label{{tab:{tex_label}}}"
        r"\begin{tabular}{lllrr}\toprule "
        r"Pozycja & Kategoria & Sztuk & Cena [zł] & Wartość [zł] \\\midrule "
        + body
        + r"\bottomrule\end{tabular}"
        + SOURCE_NOTE
        + r"\end{table}"
    )
    (TAB / fname).write_text(tex)


SCEN_LABELS = [
    ("Wariant M, normy EFSA strict", "M_BASE"),
    ("Wariant K, normy EFSA strict", "K_BASE"),
    (
        "Wariant M, normy złagodzone (tłuszcz $\\leq$140 g, błonnik $\\geq$15 g)",
        "M_RELAXED",
    ),
    (
        "Wariant K, normy złagodzone (tłuszcz $\\leq$115 g, błonnik $\\geq$15 g)",
        "K_RELAXED",
    ),
]

DIAGNOSTIC_LABELS = [
    ("M\\_BASE strict EFSA", "M_BASE"),
    ("M bez ograniczenia tłuszczu", "M_NO_FAT"),
    ("M bez ograniczenia cukru", "M_NO_SUGAR"),
    ("M bez ograniczenia błonnika", "M_NO_FIBER"),
    ("M bez ograniczeń tłuszczu i błonnika", "M_NO_FAT_FIBER"),
]


def tab_scenarios():
    body_lines = []
    for name, label in SCEN_LABELS:
        d = RES[label]
        if d.get("obj") is not None:
            body_lines.append(f"{name} & {pl(d['obj'])} \\\\")
        else:
            body_lines.append(f"{name} & \\textit{{problem niewykonalny}} \\\\")
    body = "\n".join(body_lines)
    tex = (
        r"\begin{table}[H]\centering"
        r"\caption{Koszt dziennej diety w głównych scenariuszach "
        r"(zamówienie przez Uber Eats, maj 2026).}"
        r"\label{tab:scenarios}"
        r"\small\begin{tabular}{p{0.64\textwidth}r}\toprule "
        r"Scenariusz & Koszt [zł] \\\midrule "
        + body
        + r"\bottomrule\end{tabular}"
        + SOURCE_NOTE
        + r"\end{table}"
    )
    (TAB / "tab_05_scenarios.tex").write_text(tex)


def tab_diagnostic():
    body_lines = []
    for name, label in DIAGNOSTIC_LABELS:
        d = RES[label]
        if d.get("obj") is not None:
            body_lines.append(f"{name} & {d['obj']:.2f} & TAK \\\\")
        else:
            body_lines.append(f"{name} & -- & NIE \\\\")
    body = "\n".join(body_lines)
    tex = (
        r"\begin{table}[H]\centering"
        r"\caption{Diagnoza niewykonalności: pojedyncze relaksacje ograniczeń M\_BASE. "
        r"Zarówno tłuszcz jak i błonnik muszą zostać zluzowane jednocześnie.}"
        r"\label{tab:diagnostic}"
        r"\small\begin{tabular}{p{0.64\textwidth}rc}\toprule "
        r"Scenariusz & Koszt [zł] & Wykonalny \\\midrule "
        + body
        + r"\bottomrule\end{tabular}\end{table}"
    )
    (TAB / "tab_06_diagnostic.tex").write_text(tex)


# ============== WYKRESY ==============

NUTR_KEYS = [
    ("KCAL", "kcal", "kcal"),
    ("BIAL", "bialko", "g"),
    ("TLUSZCZ", "tluszcz", "g"),
    ("NASYCONE", "nasycone", "g"),
    ("WGL", "wegle", "g"),
    ("BLONNIK", "blonnik", "g"),
    ("CUKIER", "cukier", "g"),
    ("SOL", "sol", "g"),
    ("KOFEINA", "kofeina", "mg"),
]


NUTR_LABELS_PL = {
    "kcal": "Kalorie",
    "bialko": "Białko",
    "tluszcz": "Tłuszcz",
    "nasycone": "Tłuszcze nas.",
    "wegle": "Węglowodany",
    "blonnik": "Błonnik",
    "cukier": "Cukry wolne",
    "sol": "Sól",
    "kofeina": "Kofeina",
}


def _norm_bounds(who, override=None):
    """Zwraca dla każdego składnika (nmin, nmax) z ewentualnymi nadpisaniami."""
    out = {}
    for totkey, normkey, _ in NUTR_KEYS:
        n = NORMS[normkey]
        nmin = float(n[f"{who}_min"])
        nmax = float(n[f"{who}_max"])
        if override and normkey in override:
            om, oM = override[normkey]
            if om is not None:
                nmin = om
            if oM is not None:
                nmax = oM
        out[normkey] = (nmin, nmax, totkey)
    return out


GREEN_FILL = "#4f9d5e"
GREEN_EDGE = "#2f5f37"
RED_FILL = "#c73e3a"
NORM_LINE = "#1b6b29"
MIN_TICK = "#222222"
GREY_BG = "#f4f1ea"


def fig_macro(label, who, fname, title, override=None):
    d = RES[label]
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    if not d.get("picks"):
        ax.text(
            0.5,
            0.5,
            f"{title}\n\nProblem niewykonalny",
            ha="center",
            va="center",
            fontsize=12,
            color=RED_FILL,
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        plt.savefig(FIG / fname)
        plt.close()
        return

    bounds = _norm_bounds(who, override)
    rows = []
    for totkey, normkey, unit in NUTR_KEYS:
        actual = d["totals"].get(totkey, 0)
        nmin, nmax, _ = bounds[normkey]
        ref = nmax if np.isfinite(nmax) and nmax > 0 else nmin
        if ref <= 0:
            ref = 1
        rows.append(
            (NUTR_LABELS_PL[normkey], actual, nmin, nmax, ref, 100 * actual / ref, unit)
        )

    ys = np.arange(len(rows))
    fig.patch.set_facecolor("white")
    for j, (_lab, actual, nmin, nmax, _ref, pct, unit) in enumerate(rows):
        within = min(pct, 100)
        excess = max(pct - 100, 0)
        ax.barh(
            j,
            within,
            color=GREEN_FILL,
            height=0.62,
            edgecolor=GREEN_EDGE,
            linewidth=0.6,
            zorder=2,
        )
        if excess > 0:
            ax.barh(
                j,
                excess,
                left=100,
                color=RED_FILL,
                height=0.62,
                edgecolor="#7a1f1c",
                linewidth=0.6,
                zorder=2,
            )
        if nmin > 0 and np.isfinite(nmax) and nmax > 0:
            lo_pct = 100 * nmin / nmax
            ax.plot(
                [lo_pct, lo_pct], [j - 0.30, j + 0.30], color=MIN_TICK, lw=1.4, zorder=3
            )
        if np.isfinite(nmax) and nmax > 0:
            txt = f"{pl(actual, 0)}/{pl(nmax, 0)} {unit}"
        else:
            txt = f"{pl(actual, 0)} {unit} (min {pl(nmin, 0)})"
        ax.text(max(pct, 100) + 3, j, txt, va="center", fontsize=9.5)

    ax.set_yticks(ys, [r[0] for r in rows], fontsize=10)
    ax.invert_yaxis()
    ax.axvline(100, color=NORM_LINE, lw=1.4, zorder=4)
    ax.set_xlim(0, 175)
    ax.set_xticks([0, 25, 50, 75, 100, 125, 150])
    ax.set_xlabel(r"\% górnego progu normy", fontsize=10)
    ax.set_title(title, fontsize=12, pad=12)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#444")
    ax.spines["bottom"].set_color("#444")
    ax.grid(axis="x", color="white", lw=1.0, zorder=1)
    ax.tick_params(axis="x", colors="#444")
    ax.tick_params(axis="y", length=0)
    ax.text(
        100,
        len(rows) - 0.3,
        r"  norma 100\%",
        color=NORM_LINE,
        fontsize=9,
        va="bottom",
        ha="left",
        style="italic",
    )
    plt.tight_layout()
    plt.savefig(FIG / fname)
    plt.close()


def fig_M_K_comparison():
    """Grouped bar chart: realizacja norm w M i K obok siebie (% górnego progu)."""
    overrideM = {"tluszcz": (None, 140), "blonnik": (15, None), "sol": (None, 8)}
    overrideK = {"tluszcz": (None, 115), "blonnik": (15, None), "sol": (None, 8)}
    bM = _norm_bounds("M", overrideM)
    bK = _norm_bounds("K", overrideK)
    dM, dK = RES["M_RELAXED"]["totals"], RES["K_RELAXED"]["totals"]

    labels, pctM, pctK = [], [], []
    for totkey, normkey, _ in NUTR_KEYS:
        nminM, nmaxM, _ = bM[normkey]
        nminK, nmaxK, _ = bK[normkey]
        refM = nmaxM if np.isfinite(nmaxM) and nmaxM > 0 else nminM
        refK = nmaxK if np.isfinite(nmaxK) and nmaxK > 0 else nminK
        pctM.append(100 * dM[totkey] / refM if refM else 0)
        pctK.append(100 * dK[totkey] / refK if refK else 0)
        labels.append(NUTR_LABELS_PL[normkey])

    x = np.arange(len(labels))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8.8, 4.4))
    barsM = ax.bar(
        x - w / 2,
        pctM,
        w,
        color="#1f77b4",
        edgecolor="black",
        linewidth=0.4,
        label="Mężczyzna",
    )
    barsK = ax.bar(
        x + w / 2,
        pctK,
        w,
        color="#e377c2",
        edgecolor="black",
        linewidth=0.4,
        label="Kobieta",
    )
    ax.axhline(100, color="#2ca02c", lw=1.2)
    for b, v in list(zip(barsM, pctM)) + list(zip(barsK, pctK)):
        ax.text(
            b.get_x() + b.get_width() / 2, v + 3, f"{v:.0f}", ha="center", fontsize=8
        )
    ax.set_xticks(x, labels, rotation=20, ha="right")
    ax.set_ylabel(r"\% górnego progu normy")
    ax.set_title("Realizacja norm w optimum M i K (wariant złagodzony)")
    ax.set_ylim(0, max(max(pctM), max(pctK)) * 1.18)
    ax.legend(loc="upper right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG / "fig_02_M_K_comparison.pdf", bbox_inches="tight")
    plt.close()


def fig_price_kcal():
    """Scatter: cena vs kcal dla wszystkich 45 pozycji, pozycje w optimum wyróżnione."""
    cat_colors = {
        "burger": "#d62728",
        "burger_kura": "#ff7f0e",
        "wypasik": "#bcbd22",
        "wlap": "#17becf",
        "side": "#9467bd",
        "napoj": "#1f77b4",
        "deser": "#e377c2",
        "zestaw": "#2ca02c",
        "bundle": "#8c564b",
    }
    opt_ids = {p["id"] for p in RES["M_RELAXED"]["picks"]} | {
        p["id"] for p in RES["K_RELAXED"]["picks"]
    }
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    seen = set()
    for r in MENU_ROWS:
        kcal = float(r["kcal"])
        cena = float(r["cena_pln"])
        if kcal < 20:  # napoje zero / woda
            continue
        kat = r["kategoria"]
        label = KATEGORIA_PL.get(kat, kat) if kat not in seen else None
        seen.add(kat)
        in_opt = r["id"] in opt_ids
        ax.scatter(
            cena,
            kcal,
            c=cat_colors.get(kat, "#888"),
            s=180 if in_opt else 55,
            marker="*" if in_opt else "o",
            alpha=0.95 if in_opt else 0.7,
            edgecolor="black",
            linewidth=1.2 if in_opt else 0.4,
            label=label,
            zorder=3 if in_opt else 2,
        )
        if in_opt:
            ax.annotate(
                r["nazwa"].split("(")[0].strip()[:20],
                (cena, kcal),
                xytext=(7, 6),
                textcoords="offset points",
                fontsize=8,
                fontweight="bold",
            )
    # linia stałej gęstości 100 kcal/zł (orientacyjnie)
    xs = np.linspace(8, 80, 50)
    for ratio, alpha in [(20, 0.18), (50, 0.18)]:
        ax.plot(xs, xs * ratio, ls=":", color="gray", alpha=alpha)
        ax.text(
            xs[-1],
            xs[-1] * ratio,
            f"  {ratio} kcal/zł",
            fontsize=7.5,
            color="gray",
            va="center",
        )
    ax.set_xlabel("Cena [zł]")
    ax.set_ylabel("Wartość energetyczna [kcal]")
    ax.set_title("Pozycje menu Pasibus: cena vs kalorie (gwiazdy = pozycje w optimum)")
    ax.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG / "fig_06_price_kcal.pdf", bbox_inches="tight")
    plt.close()


def fig_binding():
    """Pokazuje które pojedyncze ograniczenie odblokowuje feasibility."""
    labels = ["Tłuszcz", "Cukier", "Błonnik", "Tłuszcz\n+ Błonnik"]
    keys = ["M_NO_FAT", "M_NO_SUGAR", "M_NO_FIBER", "M_NO_FAT_FIBER"]
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    vals = [(RES[k]["obj"] if RES[k].get("picks") else None) for k in keys]
    colors = ["#d62728" if v is None else "#2ca02c" for v in vals]
    plot_vals = [v if v is not None else 0 for v in vals]
    bars = ax.bar(labels, plot_vals, color=colors, edgecolor="black", linewidth=0.5)
    ymax = max(v for v in plot_vals if v) * 1.4 if any(plot_vals) else 100
    for b, v in zip(bars, vals):
        if v is None:
            ax.add_patch(
                plt.Rectangle(
                    (b.get_x(), 0),
                    b.get_width(),
                    ymax * 0.55,
                    fill=True,
                    color="#d62728",
                    alpha=0.18,
                    hatch="///",
                    edgecolor="#d62728",
                )
            )
            ax.text(
                b.get_x() + b.get_width() / 2,
                ymax * 0.28,
                "wciąż\nniewykonalny",
                ha="center",
                fontsize=10,
                color="#d62728",
                fontweight="bold",
            )
        else:
            ax.text(
                b.get_x() + b.get_width() / 2,
                v + ymax * 0.03,
                f"{v:.2f} zł",
                ha="center",
                fontsize=11,
                fontweight="bold",
            )
    ax.set_ylabel("Koszt optimum [zł]")
    ax.set_xlabel("Pojedyncze ograniczenie usunięte z M_BASE")
    ax.set_title("Które ograniczenie blokuje feasibility?")
    ax.set_ylim(0, ymax)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG / "fig_04_binding_constraints.pdf", bbox_inches="tight")
    plt.close()


def _solve_local(tlmax, blmin):
    """Mini-solver dla pareto: liczy tylko optymalny koszt M dla zadanych granic."""
    items = MENU_ROWS
    n = len(items)
    cena = np.array([float(r["cena_pln"]) for r in items])
    c = np.concatenate([cena, np.zeros(n)])
    integrality = np.ones(2 * n)
    lb = np.zeros(2 * n)
    ub = np.concatenate([np.full(n, 5.0), np.ones(n)])
    keys = [
        ("kcal", 2300, 2700),
        ("bialko_g", 56, 135),
        ("tluszcz_g", 51, tlmax),
        ("nasycone_g", -np.inf, 28),
        ("wegle_g", 259, 438),
        ("blonnik_g", blmin, np.inf),
        ("cukier_g", -np.inf, 60),
        ("sol_g", -np.inf, 8),
        ("kofeina_mg", -np.inf, 400),
    ]
    Arows, lo, hi = [], [], []
    for col, mn, mx in keys:
        a = np.array([float(r[col]) for r in items])
        Arows.append(np.concatenate([a, np.zeros(n)]))
        lo.append(mn)
        hi.append(mx)
    for i in range(n):
        row = np.zeros(2 * n)
        row[i] = 1
        row[n + i] = -5
        Arows.append(row)
        lo.append(-np.inf)
        hi.append(0)
    res = milp(
        c,
        constraints=LinearConstraint(np.vstack(Arows), lo, hi),
        integrality=integrality,
        bounds=Bounds(lb, ub),
    )
    return float(res.fun) if res.success else None


def fig_pareto_fat():
    """Krzywa Pareto: koszt optimum jako funkcja relaksacji limitu tłuszczu (M)."""
    fat_caps = list(range(100, 201, 5))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    # 3 krzywe: różne wartości blmin
    for blmin, color, marker in [
        (0, "#1f77b4", "o"),
        (10, "#ff7f0e", "s"),
        (15, "#2ca02c", "^"),
        (25, "#d62728", "D"),
    ]:
        costs = []
        for fc in fat_caps:
            c = _solve_local(fc, blmin)
            costs.append(c)
        feasible_x = [x for x, c in zip(fat_caps, costs) if c is not None]
        feasible_y = [c for c in costs if c is not None]
        if feasible_y:
            ax.plot(
                feasible_x,
                feasible_y,
                marker=marker,
                color=color,
                label=f"błonnik ≥{blmin} g",
                linewidth=1.6,
                markersize=5,
            )
    ax.axvline(105, color="#d62728", ls="--", lw=1, alpha=0.6, label="EFSA fat ≤105 g")
    ax.axvline(140, color="#2ca02c", ls="--", lw=1, alpha=0.6, label="M_RELAXED 140 g")
    ax.set_xlabel("Limit tłuszczu [g]")
    ax.set_ylabel("Koszt optymalnej diety M [zł]")
    ax.set_title("Krzywa Pareto: koszt vs relaksacja limitu tłuszczu i błonnika")
    ax.legend(loc="upper right", fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG / "fig_05_pareto_fat.pdf", bbox_inches="tight")
    plt.close()


def fig_menu_scatter():
    """Scatter: cena/zł per kcal vs tłuszcz/kcal, kolor=kategoria."""
    cat_colors = {
        "burger": "#d62728",
        "burger_kura": "#ff7f0e",
        "wypasik": "#bcbd22",
        "wlap": "#17becf",
        "side": "#9467bd",
        "napoj": "#1f77b4",
        "deser": "#e377c2",
        "zestaw": "#2ca02c",
        "bundle": "#8c564b",
    }
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    seen = set()
    for r in MENU_ROWS:
        kcal = float(r["kcal"])
        if kcal < 20:  # filtruj napoje zero-kalorii i wodę (śmiecioweidla wykresu)
            continue
        x = float(r["cena_pln"]) / kcal * 100  # zł per 100 kcal
        y = float(r["tluszcz_g"]) / kcal * 100  # g fat per 100 kcal
        kat = r["kategoria"]
        label = KATEGORIA_PL.get(kat, kat) if kat not in seen else None
        seen.add(kat)
        ax.scatter(
            x,
            y,
            c=cat_colors.get(kat, "#888"),
            s=50,
            alpha=0.78,
            edgecolor="black",
            linewidth=0.4,
            label=label,
        )
    # linia: EFSA 35%E z tłuszczu => g_fat/kcal = 0.35/9 *100 ≈ 3.89 g per 100 kcal
    ax.axhline(
        3.89,
        color="#d62728",
        ls="--",
        lw=1,
        alpha=0.7,
        label="EFSA 35%E (3.89 g fat/100 kcal)",
    )
    ax.set_xlabel("Cena [zł / 100 kcal]")
    ax.set_ylabel("Tłuszcz [g / 100 kcal]")
    ax.set_title("Pozycje menu Pasibus: gęstość kosztowa vs gęstość tłuszczu")
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG / "fig_06_menu_scatter.pdf", bbox_inches="tight")
    plt.close()


def fig_heatmap():
    """Heatmap pozycji × składników, znormalizowane do dziennej normy M."""
    items_for_heat = [r for r in MENU_ROWS if r["kategoria"] not in ("napoj", "deser")][
        :20
    ]
    # 20 najciekawszych w sensie kcal
    items_for_heat = sorted(MENU_ROWS, key=lambda r: -float(r["kcal"]))[:24]
    nuts = [
        ("kcal", "kcal", "M_max"),
        ("bialko_g", "bialko", "M_max"),
        ("tluszcz_g", "tluszcz", "M_max"),
        ("nasycone_g", "nasycone", "M_max"),
        ("wegle_g", "wegle", "M_max"),
        ("cukier_g", "cukier", "M_max"),
        ("sol_g", "sol", "M_max"),
        ("blonnik_g", "blonnik", "M_min"),
    ]
    nut_labels = [
        "kcal",
        "białko",
        "tłuszcz",
        "nasyc.",
        "węgl.",
        "cukier",
        "sól",
        "błonnik",
    ]
    data = np.zeros((len(items_for_heat), len(nuts)))
    for i, r in enumerate(items_for_heat):
        for j, (col, norm_key, denom_key) in enumerate(nuts):
            denom = float(NORMS[norm_key][denom_key])
            data[i, j] = float(r[col]) / denom * 100  # % normy
    fig, ax = plt.subplots(figsize=(8.5, 8))
    # clamp dla kolorystyki, ale wartości pokazane jak są (boxy potrafią mieć 200-500%)
    data_clipped = np.clip(data, 0, 100)
    im = ax.imshow(data_clipped, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=100)
    ax.set_xticks(range(len(nut_labels)), nut_labels, rotation=30, ha="right")
    ax.set_yticks(
        range(len(items_for_heat)),
        [r["nazwa"][:35] for r in items_for_heat],
        fontsize=8,
    )
    for i in range(len(items_for_heat)):
        for j in range(len(nuts)):
            v = data[i, j]
            # przekroczenie 100% normy: oznacz markerem !!
            if v > 100:
                txt_color = "white"
                marker = "!"
            else:
                txt_color = "white" if v > 55 else "black"
                marker = ""
            ax.text(
                j,
                i,
                f"{v:.0f}{marker}",
                ha="center",
                va="center",
                fontsize=7,
                color=txt_color,
                fontweight="bold" if v > 100 else "normal",
            )
    cbar = plt.colorbar(im, ax=ax, shrink=0.7)
    cbar.set_label(
        "% dziennej normy M (skala 0–100; ,,!'' = przekroczenie)", fontsize=9
    )
    ax.set_title(
        "Top-24 pozycje Pasibus wg kcal: udział pojedynczej porcji w dziennej normie M"
    )
    plt.tight_layout()
    plt.savefig(FIG / "fig_07_heatmap.pdf", bbox_inches="tight")
    plt.close()


def main():
    tab_menu_summary()
    tab_norms()
    tab_solution(
        "M_RELAXED",
        "tab_03_M_menu.tex",
        "M_menu",
        "Optymalne menu wariant M (M\\_RELAXED: tłuszcz $\\leq$140 g, błonnik $\\geq$15 g).",
    )
    tab_solution(
        "K_RELAXED",
        "tab_04_K_menu.tex",
        "K_menu",
        "Optymalne menu wariant K (K\\_RELAXED: tłuszcz $\\leq$115 g, błonnik $\\geq$15 g).",
    )
    tab_scenarios()
    tab_diagnostic()

    # override: normkey -> (min_override, max_override). Solver używa solmax=8
    # (zamiast WHO 5) i M_RELAXED obniża fiber floor z 25 do 15 oraz fat cap
    # z 105/86 do 140/115.
    fig_macro(
        "M_RELAXED",
        "M",
        "fig_01_M_macro.pdf",
        "Realizacja norm w optimum M (wariant złagodzony)",
        override={"tluszcz": (None, 140), "blonnik": (15, None), "sol": (None, 8)},
    )
    fig_M_K_comparison()
    fig_price_kcal()
    print("OK")


if __name__ == "__main__":
    main()
