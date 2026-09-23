"""
Generuje SAS PROC LP z menu.csv + normy.csv (wszystkie scenariusze) do model.sas.
Kod do uruchomienia w SAS Studio / Viya.

Format zgodny ze slajdami wykładu PIDMOD: tabela z kolumnami x1..x45 oraz
wierszami f_celu, ograniczenia (le/ge), upperbd, integer.
"""

from __future__ import annotations
import csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MENU = ROOT / "menu.csv"
NORM = ROOT / "normy.csv"

NUTS = [
    ("kcal", "kcal", "ge", "le"),
    ("bialko_g", "bialko", "ge", "le"),
    ("tluszcz_g", "tluszcz", "ge", "le"),
    ("nasycone_g", "nasycone", None, "le"),
    ("wegle_g", "wegle", "ge", "le"),
    ("blonnik_g", "blonnik", "ge", None),
    ("cukier_g", "cukier", None, "le"),
    ("sol_g", "sol", None, "le"),
    ("kofeina_mg", "kofeina", None, "le"),
]


def fmt(v) -> str:
    f = float(v)
    return f"{f:g}"


def build_proclp_dataset(label: str, items: list, params: dict) -> str:
    """Buduje data step + proc lp w formacie wierszowym ze slajdów wykładu.

    Wiersze:
      f_celu  c1 c2 ... c45  min .
      kcalMin a1 a2 ... a45  ge  2300
      kcalMax a1 a2 ... a45  le  2700
      ... (analogicznie dla pozostałych norm)
      upper   5 5 ... 5     upperbd .
      int     1 1 ... 1     integer .
    """
    n = len(items)
    xcols = " ".join(f"x{i + 1}" for i in range(n))

    # Wiersz funkcji celu
    obj_cells = " ".join(fmt(r["cena_pln"]) for r in items)
    rows = [f"f_celu   {obj_cells}  min .  ."]

    # Wiersze ograniczeń żywieniowych
    rhs_keys = {
        "kcal": ("kcalmin", "kcalmax"),
        "bialko": ("bialmin", "bialmax"),
        "tluszcz": ("tlmin", "tlmax"),
        "nasycone": (None, "nasmax"),
        "wegle": ("wgmin", "wgmax"),
        "blonnik": ("blmin", None),
        "cukier": (None, "cukmax"),
        "sol": (None, "solmax"),
        "kofeina": (None, "kofmax"),
    }
    for col, normkey, low_op, high_op in NUTS:
        cells = " ".join(fmt(r[col]) for r in items)
        lo_key, hi_key = rhs_keys[normkey]
        if low_op == "ge" and lo_key:
            rhs = params[lo_key]
            rows.append(f"{normkey[:8]}Min {cells}  ge  {rhs}  .")
        if high_op == "le" and hi_key:
            rhs = params[hi_key]
            rows.append(f"{normkey[:8]}Max {cells}  le  {rhs}  .")

    # Górna granica zmiennych (0..5)
    upper_cells = " ".join("5" for _ in items)
    rows.append(f"upper    {upper_cells}  upperbd .  .")

    # Wymaganie całkowitoliczbowości
    int_cells = " ".join("1" for _ in items)
    rows.append(f"int      {int_cells}  integer .  .")

    data_block = (
        f"data {label.lower()};\n"
        f"  format _row_ $10. _type_ $10.;\n"
        f"  input _row_ $ {xcols} _type_ $ _rhs_ _rhssen_;\n"
        f"  datalines;\n" + "\n".join(rows) + "\n;\nrun;\n"
        f"\nproc lp data={label.lower()};\n"
        f'  title "{label}";\n'
        f"run;\n"
    )
    return data_block


def build_full() -> str:
    items = list(csv.DictReader(open(MENU)))
    norms = {r["skladnik"]: r for r in csv.DictReader(open(NORM))}

    def base(who: str) -> dict:
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
            # WHO 5g jest niewykonalne dla diety w lokalu burgerowym
            # (sam Standard wnosi ok. 2.4 g soli). Podniesiono do 8 g.
            "solmax": "8",
            "kofmax": norms["kofeina"][f"{who}_max"],
        }

    out = (
        "/* ===================================================================\n"
        "   Optymalna dieta studenta w Pasibusie\n"
        "   Model PLC -- PROC LP (zgodnie z formatem ze slajdow wykladu PIDMOD)\n"
        "   =================================================================== */\n\n"
    )

    out += build_proclp_dataset("M_BASE", items, base("M"))
    out += build_proclp_dataset("K_BASE", items, base("K"))

    p = base("M")
    p["tlmax"] = "140"
    p["blmin"] = "15"
    out += build_proclp_dataset("M_RELAXED", items, p)

    p = base("K")
    p["tlmax"] = "115"
    p["blmin"] = "15"
    out += build_proclp_dataset("K_RELAXED", items, p)

    return out


def main():
    sas_code = build_full()
    (ROOT / "kod" / "model.sas").write_text(sas_code)
    print(f"Zapisano model.sas ({len(sas_code)} znaków)")


if __name__ == "__main__":
    main()
