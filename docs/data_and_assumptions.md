# Data and assumptions

## Course-supplied inputs

- Four 336 h freight-depot base-load profiles: ICA, Mathem, Postnord and Airmee.
- Depot operating-pattern descriptions used to define weekday/weekend activity windows.
- CIGRE MV benchmark network and project operating limits.

## External input

- ENTSO-E SE1 day-ahead prices, 1–14 January 2024, used for the winter group case.

## Engineering assumptions introduced by the group

The project explicitly asks the group to define the EV fleet and charging infrastructure. The repository therefore assumes representative fleet size/mix, daily vehicle energy, charger ratings, 0.92 charging efficiency and 0.95 base-load power factor. These are model assumptions, not measured fleet telemetry.

The complete assumptions are regenerated into `data/processed/fleet/fleet_assumptions.csv` and `charger_design.csv` so they can be reported transparently.
