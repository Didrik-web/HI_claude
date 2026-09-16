# MJ2505 Project 1 — Freight Electrification and Network Optimization

This repository implements the five project steps as one reproducible workflow.

```text
raw data
  -> preprocessing
  -> 01 baseline CIGRE network
  -> 02 two-week depot base-load analysis + shared connection-point screening
  -> 03 charging-infrastructure design + uncontrolled charging
  -> 04 market-driven cost optimization
  -> 05 network-loss optimization
  -> final comparison
```

## Important project conventions

- Step 1 uses the original CIGRE MV topology and the Step-1 switching procedure.
- Before Step 2 the original CIGRE loads are halved, as required by the project.
- **From Step 2 onwards S1, S2 and S3 are CLOSED for every analysis**, including N-1.
- The four companies are modelled as separate fleets/loads inside one logistics area with one shared electrical connection point. The current selected connection is **Bus 1**.
- N-1 tests the 12 ordinary lines; corrected switch/tie references `Line 6-7`, `Line 11-4`, `Line 14-8` are not treated as ordinary outage lines.
- Each contingency is temporary and restored before the next test.

## Repository structure

```text
data/
  raw/                untouched course/external data
  processed/fleet/    fleet assumptions, charger design and base-load interfaces
  processed/market/   processed SE1 prices
  processed/network/  shared bus + generated Step-2/3/5 network interfaces
notebooks/             five notebooks, one per project step
src/                   reusable calculation code
docs/                  assumptions and methodology notes
results/               generated outputs by step
scripts/               preprocessing, checks and submission packaging
```

## Setup

```bash
git clone https://github.com/Eliasylund/MJ2505-Project1.git
cd MJ2505-Project1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/preprocess_all.py
python scripts/check_project.py
```

Run notebooks **01 -> 05 in order**. Restart the kernel before `Run All` if source files have been changed.

## Data ownership

The 336-hour depot base-load profiles are course inputs. The EV fleet size/mix, daily vehicle energy requirements and charger sizing are **engineering assumptions introduced by the group**, which is required by Step 3. They are centralized in `src/preprocess/fleet.py` and exported to `fleet_assumptions.csv` and `charger_design.csv` for transparent reporting.

## Generated interfaces

- Notebook 02: `connection_point_screening.csv`
- Notebook 03: `network_limits.csv`
- Notebook 05: `marginal_loss_factors.csv`

Step 4 and Step 5 deliberately fail if Step 3 found that full installed charging is not network-feasible.

## Git workflow

Before working:

```bash
git pull --rebase origin main
```

After a tested change:

```bash
git status
git add .
git commit -m "Describe change"
git pull --rebase origin main
git push origin main
```

Do not force-push conflicts. Resolve them, `git add` the resolved files and continue with `git rebase --continue`.

For a clean ZIP of committed files:

```bash
git archive --format=zip --output=MJ2505_project1.zip HEAD
```

## Submission folder

The project asks for `01_notebooks/`, `02_inputs/`, `03_outputs/`. After running all notebooks:

```bash
python scripts/build_submission.py
```

This creates `submission/` in that format.
