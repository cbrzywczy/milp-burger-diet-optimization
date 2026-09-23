# Programowanie całkowitoliczbowe: optymalna dieta w Pasibusie

Czy da się zjeść cały dzień w sieci burgerowej i zmieścić się w normach żywieniowych? Ile to kosztuje? Projekt rozwiązuje klasyczny problem diety Stiglera w wersji całkowitoliczbowej, bo burgery kupuje się w całych sztukach.

**Dane:** 45 pozycji menu Pasibusa z Uber Eats (maj 2026): cena, kalorie, białko, tłuszcze, węglowodany, błonnik, cukry, sól, kofeina

**Normy:** IŻŻ, EFSA, WHO; osobno dla mężczyzny (M) i kobiety (K) w wieku 20–25 lat

**Metody:** MILP · branch-and-bound · analiza scenariuszowa · diagnoza niewykonalności

<img src="https://img.shields.io/badge/SAS-PROC%20LP-0766D1" alt="SAS PROC LP" height="18"><br>
<img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="16" alt="Python"> &nbsp;`scipy.optimize.milp` (HiGHS) · `numpy` · `matplotlib`

<sub>Projekt z Probabilistycznych i Deterministycznych Modeli Optymalizacji Decyzji, WNE UW, 2026</sub>

## Model

$$\min Z = \sum_{i=1}^{45} c_i x_i, \qquad x_i \in \{0, 1, \dots, 5\}$$

$c_i$ to cena pozycji $i$, a $x_i$ to liczba zamówionych sztuk. Ograniczenia to dolne i górne progi dla każdego składnika odżywczego: 45 zmiennych, 13 ograniczeń.

## Najważniejsze wyniki

- **Przy pełnych normach problem jest niewykonalny** dla M i K. Żadna kombinacja pozycji nie spełnia jednocześnie widełek kalorii, limitu tłuszczu i progu błonnika.
- Zdjęcie jednego ograniczenia (tłuszcz, błonnik albo cukier) nie wystarcza. Rozwiązanie istnieje dopiero po **zluzowaniu tłuszczu i błonnika jednocześnie**. Przyczyną jest profil całego menu, a nie jedno ograniczenie.
- Po złagodzeniu norm optymalne menu kosztuje **60,97 zł (M)** i **75,96 zł (K)**.
- Mega Deal „3x Cziks + frytki” ma najlepszy w menu stosunek kalorii do ceny i stanowi 57% kosztu menu M. W wariancie K niższy limit kalorii wyklucza boxy.
- Tłuszcz w optimum: 135 g (M) przy zalecanym maksimum 105 g oraz 112 g (K) przy limicie 86 g.

## Wykresy

| Pozycje menu: cena a kalorie | Realizacja norm w optimum M i K |
|---|---|
| ![Pozycje menu w przestrzeni cena–kalorie](charts/cena_vs_kalorie.png) | ![Realizacja norm w optimum M i K](charts/realizacja_norm_M_K.png) |

## Kod

| Plik | Zawartość |
|---|---|
| <img src="https://img.shields.io/badge/SAS-0766D1" height="14"> [`kod/model.sas`](kod/model.sas) | model `PROC LP` dla wszystkich scenariuszy |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="14"> [`kod/run_sas.py`](kod/run_sas.py) | generator `model.sas` z plików CSV |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="14"> [`kod/solve_local.py`](kod/solve_local.py) | weryfikacja modelu w Pythonie (HiGHS) |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="14"> [`kod/make_outputs.py`](kod/make_outputs.py) | tabele i wykresy |
| [`menu.csv`](menu.csv) · [`normy.csv`](normy.csv) | menu z profilem odżywczym, widełki norm M i K |
| [`wyniki/results.json`](wyniki/results.json) | wyniki wszystkich scenariuszy |

```bash
pip install numpy scipy
python kod/solve_local.py   # odtwarza wyniki/results.json
```

## Dane

- [Uber Eats, Pasibus Nowy Świat](https://www.ubereats.com/pl/store/pasibus-nowy-swiat/gXk0BheTVMuFCk1dFTaHNg), maj 2026: ceny
- [Wykaz producenta (PDF)](https://pasibus.pl/wp-content/uploads/2026/04/pbsbsb_merged.pdf) i [FatSecret](https://www.fatsecret.pl/kalorie-warto%C5%9Bci%C2%A0od%C5%BCywcze/pasibus): wartości odżywcze
- Zestawy i boxy: suma wartości składników

## Licencja

Kod: [MIT](LICENSE).
