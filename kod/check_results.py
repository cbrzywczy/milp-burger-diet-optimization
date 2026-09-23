"""
Porownuje wyniki ponownie policzone przez solve_local.py z wynikami zapisanymi w repozytorium.
Uzycie: python kod/check_results.py <zapisane_results.json> <nowe_results.json>
"""

from __future__ import annotations
import json, sys

TOL = 0.01  # zl

saved = json.load(open(sys.argv[1]))
fresh = json.load(open(sys.argv[2]))

errors = []
for name, ref in saved.items():
    new = fresh.get(name)
    if new is None:
        errors.append(f"{name}: brak scenariusza w nowych wynikach")
        continue
    a, b = ref["obj"], new["obj"]
    if (a is None) != (b is None):
        errors.append(f"{name}: wykonalnosc sie zmienila ({a} -> {b})")
    elif a is not None and abs(a - b) > TOL:
        errors.append(f"{name}: koszt {a:.2f} -> {b:.2f}")
    else:
        status = "niewykonalny" if a is None else f"{a:.2f} zl"
        print(f"OK  {name}: {status}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"Wszystkie {len(saved)} scenariusze zgodne.")
