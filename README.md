# Programowanie całkowitoliczbowe: optymalna dieta w Pasibusie

[![Weryfikacja modelu](https://github.com/cbrzywczy/milp-burger-diet-optimization/actions/workflows/verify.yml/badge.svg)](https://github.com/cbrzywczy/milp-burger-diet-optimization/actions/workflows/verify.yml)

Czy da się zjeść cały dzień w sieci burgerowej, zmieścić się w normach żywieniowych i ile to kosztuje?

Projekt z Probabilistycznych i Deterministycznych Modeli Optymalizacji Decyzji (WNE UW, 2026) rozwiązuje klasyczny problem diety Stiglera w wersji całkowitoliczbowej, bo burgery kupuje się w całych sztukach.

**Dane:** 45 pozycji menu Pasibusa z Uber Eats (maj 2026) z ceną, kaloriami, białkiem, tłuszczami, węglowodanami, błonnikiem, cukrami, solą i kofeiną

**Normy:** IŻŻ, EFSA i WHO, osobno dla mężczyzny (M) i kobiety (K) w wieku 20–25 lat

**Metody:** programowanie całkowitoliczbowe (MILP), metoda podziału i ograniczeń, analiza scenariuszowa, diagnoza niewykonalności

<img src=".github/sas.svg" width="16" alt="SAS">&nbsp; `PROC LP`<br>
<img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="16" alt="Python">&nbsp; `scipy.optimize.milp` `numpy` `matplotlib`

## Model

```math
\min Z = \sum_{i=1}^{45} c_i x_i, \qquad x_i \in \{0, 1, \dots, 5\}
```

$c_i$ to cena pozycji $i$, a $x_i$ to liczba zamówionych sztuk. Ograniczenia to dolne i górne progi dla każdego składnika odżywczego. Model ma 45 zmiennych i 13 ograniczeń.

## Najważniejsze wyniki

- **Przy pełnych normach problem jest niewykonalny** dla M i K. Żadna kombinacja pozycji nie spełnia jednocześnie widełek kalorii, limitu tłuszczu i progu błonnika.
- Zdjęcie jednego ograniczenia (tłuszcz, błonnik albo cukier) nie wystarcza. Rozwiązanie istnieje dopiero po **zluzowaniu tłuszczu i błonnika jednocześnie**. Przyczyną jest profil całego menu, a nie jedno ograniczenie.
- Po złagodzeniu norm optymalne menu kosztuje **60,97 zł (M)** i **75,96 zł (K)**.
- Mega Deal 3x Cziks z frytkami ma najlepszy w menu stosunek kalorii do ceny i stanowi 57% kosztu menu M. W wariancie K niższy limit kalorii wyklucza boxy.
- Tłuszcz w optimum: 135 g (M) przy zalecanym maksimum 105 g oraz 112 g (K) przy limicie 86 g.

## Ocena modelu

- **Niezależna implementacja.** Model jest zapisany w SAS `PROC LP` i osobno w Pythonie (solver HiGHS). Skrypt `solve_local.py` odtwarza wszystkie wyniki z `results.json`.
- **Zależność od założeń.** Koszt optimum zależy od tego, jak mocno zluzujemy normy tłuszczu i błonnika. To wybór scenariuszowy, a nie wynik modelu.
- **Jakość danych.** Część wartości odżywczych pochodzi z FatSecret, a pojedyncze braki uzupełniłam średnią z kategorii. Przykład ryzyka: FatSecret podaje dwie wersje burgera Bebek, różniące się o 270 kcal i 27 g tłuszczu.
- **Ceny** z Uber Eats zawierają 10–15% marży za dostawę. W lokalu optimum byłoby tańsze.
- **Zakres modelu.** Model dotyczy jednego dnia i nie uwzględnia smaku ani powtarzalności posiłków. Górny limit 5 sztuk pozycji to arbitralne założenie.

## Wykresy

| Cena a kalorie |
|:-:|
| ![Pozycje menu w przestrzeni cena–kalorie](charts/cena_vs_kalorie.png) |
| Każdy punkt to pozycja menu. Gwiazdki to pozycje wybrane do optymalnego menu. Leżą tam, gdzie kalorie są najtańsze. |

| Realizacja norm w optymalnym menu |
|:-:|
| ![Realizacja norm w optimum M i K](charts/realizacja_norm_M_K.png) |
| Jaką część górnego limitu każdej normy pokrywa optymalne menu. Kalorie i tłuszcz są blisko limitu, białko i błonnik daleko. |

## Kod

| | Plik | Zawartość |
|:-:|---|---|
| <img src=".github/sas.svg" width="18"> | [`model.sas`](kod/model.sas) | model `PROC LP` dla wszystkich scenariuszy |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="18"> | [`run_sas.py`](kod/run_sas.py) | generator `model.sas` z plików CSV |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="18"> | [`solve_local.py`](kod/solve_local.py) | weryfikacja modelu w Pythonie (solver HiGHS) |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="18"> | [`make_outputs.py`](kod/make_outputs.py) | tabele i wykresy |
|  | [`menu.csv`](menu.csv), [`normy.csv`](normy.csv) | menu z profilem odżywczym, widełki norm M i K |
|  | [`results.json`](wyniki/results.json) | wyniki wszystkich scenariuszy |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/python/python-original.svg" width="18"> | [`check_results.py`](kod/check_results.py) | porównanie nowych wyników z zapisanymi (CI) |

```bash
uv run python kod/solve_local.py   # odtwarza wyniki/results.json
```

Przy każdej zmianie w repozytorium GitHub Actions rozwiązuje wszystkie scenariusze od nowa i porównuje wyniki z `results.json` ([`verify.yml`](.github/workflows/verify.yml)).

## Dane

- [Uber Eats, Pasibus Nowy Świat](https://www.ubereats.com/pl/store/pasibus-nowy-swiat/gXk0BheTVMuFCk1dFTaHNg), maj 2026: ceny
- [Wykaz producenta (PDF)](https://pasibus.pl/wp-content/uploads/2026/04/pbsbsb_merged.pdf) i [FatSecret](https://www.fatsecret.pl/kalorie-warto%C5%9Bci%C2%A0od%C5%BCywcze/pasibus): wartości odżywcze
- Zestawy i boxy: suma wartości składników

## Licencja

Kod: [MIT](LICENSE).
