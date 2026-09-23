"""
Lokalny solver MILP (scipy) -- generuje results.json w tym samym formacie
co run_sas.py, kiedy SAS Viya jest niedostepne. Sluzy jako sanity check.
"""

from __future__ import annotations
import csv, json, pathlib
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

ROOT = pathlib.Path(__file__).resolve().parent.parent
MENU = ROOT / "menu.csv"
NORM = ROOT / "normy.csv"
OUT = ROOT / "wyniki"
OUT.mkdir(exist_ok=True)


def load():
    items = list(csv.DictReader(open(MENU)))
    norms = {r["skladnik"]: r for r in csv.DictReader(open(NORM))}
    return items, norms


def solve(items, params, price_mult=None):
    n = len(items)
    if price_mult is None:
        price_mult = [1.0] * n
    cena = np.array([float(r["cena_pln"]) * m for r, m in zip(items, price_mult)])
    # zmienne: x_i (0..5 calkowite)
    c = cena
    integrality = np.ones(n)
    lb = np.zeros(n)
    ub = np.full(n, 5.0)

    keys = [
        ("kcal", "kcalmin", "kcalmax"),
        ("bialko_g", "bialmin", "bialmax"),
        ("tluszcz_g", "tlmin", "tlmax"),
        ("nasycone_g", None, "nasmax"),
        ("wegle_g", "wgmin", "wgmax"),
        ("blonnik_g", "blmin", None),
        ("cukier_g", None, "cukmax"),
        ("sol_g", None, "solmax"),
        ("kofeina_mg", None, "kofmax"),
    ]

    Arows, lo, hi = [], [], []
    for col, kmin, kmax in keys:
        Arows.append(np.array([float(r[col]) for r in items]))
        lo.append(float(params[kmin]) if kmin else -np.inf)
        hi.append(float(params[kmax]) if kmax else np.inf)

    A = np.vstack(Arows)
    res = milp(
        c,
        constraints=LinearConstraint(A, lo, hi),
        integrality=integrality,
        bounds=Bounds(lb, ub),
    )
    if not res.success:
        return {"obj": None, "picks": [], "totals": {}, "msg": res.message}
    x = res.x
    picks = []
    totals = {
        "KCAL": 0,
        "BIAL": 0,
        "TLUSZCZ": 0,
        "NASYCONE": 0,
        "WGL": 0,
        "BLONNIK": 0,
        "CUKIER": 0,
        "SOL": 0,
        "KOFEINA": 0,
    }
    tot_keys = [
        ("KCAL", "kcal"),
        ("BIAL", "bialko_g"),
        ("TLUSZCZ", "tluszcz_g"),
        ("NASYCONE", "nasycone_g"),
        ("WGL", "wegle_g"),
        ("BLONNIK", "blonnik_g"),
        ("CUKIER", "cukier_g"),
        ("SOL", "sol_g"),
        ("KOFEINA", "kofeina_mg"),
    ]
    for i, r in enumerate(items):
        if x[i] > 0.5:
            picks.append(
                {
                    "id": r["id"],
                    "x": float(round(x[i])),
                    "cena": float(r["cena_pln"]) * price_mult[i],
                }
            )
        for tk, ck in tot_keys:
            totals[tk] += float(r[ck]) * x[i]
    return {
        "obj": float(res.fun),
        "picks": picks,
        "totals": {k: round(v, 2) for k, v in totals.items()},
    }


def base(norms, who):
    return {
        "kcalmin": norms["kcal"][f"{who}_min"],
        "kcalmax": norms["kcal"][f"{who}_max"],
        "bialmin": norms["bialko"][f"{who}_min"],
        "bialmax": norms["bialko"][f"{who}_max"],
        "tlmin": norms["tluszcz"][f"{who}_min"],
        "tlmax": norms["tluszcz"][f"{who}_max"],
        "nasmax": norms["nasycone"][f"{who}_max"],
        "wgmin": norms["wegle"][f"{who}_min"],
        "wgmax": norms["wegle"][f"{who}_max"],
        "blmin": norms["blonnik"][f"{who}_min"],
        "cukmax": norms["cukier"][f"{who}_max"],
        "solmax": "8",
        "kofmax": norms["kofeina"][f"{who}_max"],
    }


def main():
    items, norms = load()
    out = {}

    # Bazowe (EFSA-strict). Oczekiwane niewykonalne.
    out["M_BASE"] = solve(items, base(norms, "M"))
    out["K_BASE"] = solve(items, base(norms, "K"))

    # Złagodzone: tłuszcz <= 40% energii (140 g dla M, 115 g dla K)
    # ORAZ błonnik >= 15 g (zamiast EFSA 25 g) -- inaczej Pasibus jest
    # strukturalnie niewykonalny (max osiągalny błonnik to 29 g przy bardzo
    # wąskim wyborze pozycji; przy realnych makro to za mało).
    p = base(norms, "M")
    p["tlmax"] = "140"
    p["blmin"] = "15"
    out["M_RELAXED"] = solve(items, p)
    p = base(norms, "K")
    p["tlmax"] = "115"
    p["blmin"] = "15"
    out["K_RELAXED"] = solve(items, p)

    # Diagnostyka: pojedyncze relaksacje pokazują, że ZADNA pojedyncza nie wystarcza --
    # potrzeba zluzowania jednocześnie tłuszczu i błonnika.
    p = base(norms, "M")
    p["tlmax"] = "999"
    out["M_NO_FAT"] = solve(items, p)
    p = base(norms, "M")
    p["cukmax"] = "999"
    out["M_NO_SUGAR"] = solve(items, p)
    p = base(norms, "M")
    p["blmin"] = "0"
    out["M_NO_FIBER"] = solve(items, p)
    p = base(norms, "M")
    p["tlmax"] = "999"
    p["blmin"] = "0"
    out["M_NO_FAT_FIBER"] = solve(items, p)

    (OUT / "results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    for label, d in out.items():
        if d.get("obj") is None:
            print(f"  {label}: NIEWYKONALNY -- {d.get('msg', '')}")
        else:
            print(f"  {label}: koszt={d['obj']:.2f} zł, {len(d['picks'])} pozycji")


if __name__ == "__main__":
    main()
