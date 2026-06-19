# compare_internet_packages

## General info
> Comparison of internet packages from different internet service provider in Iran

---

## Requirements
- [uv](https://docs.astral.sh/uv/) (manages Python and dependencies)

All three operators are now scraped over plain HTTP — no Chrome driver / Selenium.

---

## Usage
  Get the best package offered with **100000** toman budget from **mci** and **mtn** :
  ```bash
  uv run compare-internet-packages -b 100000 -p mci mtn
  ```
  for more options :
  ```bash
  uv run compare-internet-packages -h
  ```
  Installable too: `pip install .` then run `compare-internet-packages ...`.

---
## Task-Lists
- [x] support Hamrahe Aval (MCI)
- [x] support Irancell (MTN)
- [x] support RighTel 
