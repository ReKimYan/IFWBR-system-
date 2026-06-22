# Integrated Food Waste BioRefinery (IFWBR) System

A mixed-integer nonlinear programming (MINLP) framework for the optimal design of an **Integrated Food Waste BioRefinery (IFWBR) system** — a system that integrates conventional **food waste management** options (composting, anaerobic digestion, incineration) with **biorefinery pathways** (biofuels and biochemicals) into a single optimisation framework, with **uncertainty quantified through Monte Carlo simulation**.

The model is built in Python with [Pyomo](http://www.pyomo.org/) and solved with [SCIP](https://www.scipopt.org/).

The framework supports a triple-bottom-line analysis through three objectives:

- **Economic** — Net Present Value (NPV)
- **Environmental** — Global Warming Potential savings (GWP)
- **Social** — Job creation potential (Social Impact, SIA)

The Pareto front of optimal trade-offs is generated using the **ε-constraint method**, and robustness of the solutions is assessed under uncertainty using **Monte Carlo simulation**.

---

## Object-Oriented Design

The model follows an **object-oriented programming (OOP)** approach. Each major part of the IFWBR is encapsulated in its own class, all operating on a single shared Pyomo `AbstractModel` instance. This makes the code modular, easy to extend, and easy to debug.

```
            ┌─────────────────────────────────┐
            │    SetParameterVariableModel    │  ← Sets, Params, Vars
            └─────────────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
   GrindingModel    InequalityConstraints   VariableSelectionModel
                            │
                            ▼
              UtilityChemicalConsumptionModel
                            │
                            ▼
                    BiorefineryModel
                            │
                            ▼
                    FWManagementModel
                            │
                            ▼
                   CarbonCaptureModel
                            │
                            ▼
                       CostModel
                            │
                            ▼
                       MOOModel
                            │
                            ▼
       ε-constraint sweep + Monte Carlo loop in main.py
```

Each class takes the shared model as input, attaches its own constraints, and returns control to `main.py`. There is one source of truth (the model) and clean separation of concerns.

---

## Repository Structure

```
.
├── main.py                       # Entry point: ε-constraint sweep under Monte Carlo uncertainty
│
├── SetParameterVariable.py       # Sets, parameters, decision variables
├── Grinding.py                   # Pre-treatment (milling) constraints
├── InequalityConstraints.py      # Global feasibility constraints
├── VariableSelection.py          # Process selection (FW allocation, glucose-upgrading routes)
├── UtilityChemical.py            # Utility & chemical consumption tracking
├── Biorefinery.py                # Core biorefinery process equations
├── FWManagement.py               # Composting / anaerobic digestion / incineration
├── CarbonCapture.py              # CO2 capture and compression process
├── Cost.py                       # Capex / Opex calculations
├── MOO.py                        # Economic, Environmental, and Social Impact objectives
│
└── Data_blending.dat             # Sets, parameters, compositions, specific mass & energy, cost, prices, etc.
```

---

## Methodology

### 1. The MINLP Model

The IFWBR is described as a mixed-integer nonlinear program with:

- **Continuous variables (0–1)** — allocation of food waste to each management/biorefinery pathway, biofuel pathway shares, biochemical pathway shares, flow rates, capacities, costs, and environmental burdens.
- **Binary variables** — used **only** for:
  - Tax indicator constraints (whether positive profit is realised in a given year, triggering taxation)
  - Regulatory compatibility constraints
- **Constraints** — mass and energy balances, conversion stoichiometry, demand limits, capacity bounds, product demand, the management-option-selection rule, economic, environmental, and social constraints.

### 2. Multi-Objective Formulation

The ε-constraint method is used:

```
maximize     NPV
subject to   GWP_saving  ≤  ε_GWP
             SIA         ≤  ε_SIA
             [all biorefinery constraints]
```

### 3. Uncertainty Quantification (Monte Carlo)

For each sampled ε-pair, `main.py` runs a Monte Carlo loop in which uncertain inputs are
re-sampled and the MINLP is re-solved for every draw:

- **Food-waste availability** — sampled from a lognormal distribution (mean ≈ 18,225 MT/day).
- **Macronutrient composition** — carbohydrate, protein, and lipid fractions sampled from
  truncated normal distributions and renormalised to sum to 1.

A single reproducible random generator (fixed seed) is used across the whole run so that
draws are independent. Solves that do not reach a usable optimal/feasible solution are skipped,
and results are checkpointed incrementally to CSV and saved to Excel at the end.

### 4. Pareto Front Construction

`main.py` solves the MINLP at each ε-point under each Monte Carlo draw and stores the resulting
non-dominated solutions in a CSV / Excel file for post-processing.

---

## Model Coverage

### Management options & products

| Management option         | Products                                                   |
|---------------------------|------------------------------------------------------------|
| **Composting**            | Compost                                                    |
| **Anaerobic digestion**   | Biomethane (BioCNG) + fertilizer                           |
| **Incineration**          | Heat & power recovery (electricity)                        |
| **Biorefinery**           | Biofuels and biochemicals (with co-products and captured CO₂) |

### Biorefinery products
- **Biofuels:** bioethanol, biodiesel, biobutanol
- **Biochemicals:** lactic acid, succinic acid, 2,3-butanediol (BDO)
- **Co-products:** glycerol, acetone, hydrogen, protein, fertilizer
- **Captured CO₂** from anaerobic digestion off-gas, fermentation, and incineration flue gas

### Carbon Capture
Amine-based absorption with PZ/MDEA solvent, distillation regeneration, and compression for sale or sequestration.

---

## Outputs

For every point in the ε-constraint grid and each Monte Carlo draw, the model reports:

- **Economic:** NPV, total revenue, capex, opex
- **Environmental:** GWP savings, direct emissions, utility-related GWP, chemical-LCA GWP
- **Social:** total jobs (SIA)
- **Material balances:** product yields (BDO, LA, SA, ethanol, butanol, biodiesel, etc.)
- **Process selections:** food-waste allocation across management options, glucose-upgrading route shares
- **Waste streams:** organic waste, solid waste, flue gas, off-gas
- **Uncertainty inputs logged per run:** FW availability draw and macronutrient composition

---

## How to Run

```bash
# install dependencies
pip install pyomo pandas numpy openpyxl
# SCIP must be installed separately and available to Pyomo

# run the full ε-constraint sweep under Monte Carlo uncertainty
python main.py
```

> Note: update the output directory paths in `main.py` (currently set to a cluster
> scratch path) to a location on your own machine before running.

---

## References

To be updated upon publication.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `pyomo` | Optimization modelling framework |
| `scip` | MINLP solver (external — install separately) |
| `pandas`, `numpy` | Data handling & Monte Carlo sampling |
| `openpyxl` | Excel file writing |

---

## License

This project is released for academic and research purposes.
