# Repository overview

The repository separates calculation logic (`src/`) from the five project-facing notebooks (`notebooks/`).

Data flow:

`raw freight + ENTSO-E -> preprocessing -> Step 1 baseline -> Step 2 depot base-load network -> Step 3 charger design/uncontrolled + network limits -> Step 4 cost optimization -> Step 5 loss optimization -> final comparison`

The same Pandapower physical model validates Steps 2–5. From Step 2 onward it always uses half the original CIGRE load and S1/S2/S3 closed.
