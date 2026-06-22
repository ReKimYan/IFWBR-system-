# main.py
import os
import time
import random
import numpy as np
import pandas as pd
import pyomo.environ as pyo
from pyomo.environ import *
from pyomo.opt import SolverStatus, TerminationCondition
from pyomo.environ import value

# === Import custom model components ===
from SetParameterVariable import SetParameterVariableModel
from Grinding import GrindingModel
from VariableSelection import VariableSelectionModel
from InequalityConstraints import InequalityConstraintsModel
from Biorefinery import BiorefineryModel
from FWManagement import FWManagementModel
from CarbonCapture import CarbonCaptureModel
from UtilityChemical import UtilityChemicalConsumptionModel
from Cost import CostModel
from MOO import MOOModel


# ===================================================
# Build Pyomo Abstract Model
# ===================================================
def build_model():
    model = AbstractModel()
    SetParameterVariableModel(model)
    GrindingModel(model)
    VariableSelectionModel(model)
    InequalityConstraintsModel(model)
    BiorefineryModel(model)
    FWManagementModel(model)
    CarbonCaptureModel(model)
    UtilityChemicalConsumptionModel(model)
    CostModel(model)
    MOOModel(model)

    # Declare epsilon constraint parameters
    model.epsilon_param_GWP = Param(within=Reals, mutable=True, initialize=100000)
    model.epsilon_param_SIA = Param(within=Reals, mutable=True, initialize=10000)

    # Epsilon constraints
    def GWP_epsilon_rule(model):
        return model.GWPSavings <= model.epsilon_param_GWP
    model.GWPsavings_epsilon_constraint = Constraint(rule=GWP_epsilon_rule)

    def SIA_epsilon_rule(model):
        return model.SIA <= model.epsilon_param_SIA
    model.SIA_epsilon_constraint = Constraint(rule=SIA_epsilon_rule)

    # Objective: maximize NPV
    def NPV_objective_rule(model):
        return model.npv
    model.maximize_npv = Objective(rule=NPV_objective_rule, sense=maximize)

    return model


# ===================================================
# Monte Carlo Simulation
# ===================================================
def run_montecarlo(model,
                   n_simulations=100,
                   n_epsilon_samples=30,
                   solver_name='scip',
                   random_seed=42,
                   output_dir="/parallel_scratch/rh01280/MOO2"):

    print("\n=== Starting Monte Carlo simulations ===")

    # === Output paths ===
    directory = "/parallel_scratch/rh01280/MOO2"
    os.makedirs(directory, exist_ok=True)
    checkpoint_path = os.path.join(directory, "checkpoint_results.csv")
    full_path = os.path.join(directory, "MonteCarlo_Results_MOO_withEpsilons.xlsx")

    # === Epsilon Ranges ===
    epsilon_values_GWP = np.linspace(5000, 2000000, 30)
    epsilon_values_SIA = np.linspace(5000, 100000, 30)
    all_epsilon_combinations = [(GWP, SIA) for GWP in epsilon_values_GWP for SIA in epsilon_values_SIA]

    # === ONE random generator for the whole run (reproducible, no mid-run reseed) ===
    # CHANGED: previously np.random.seed(42) was called twice, which restarted the
    # stream and reused the SAME 100 feedstock draws for every epsilon-pair.
    # A single generator gives independent draws across the whole run.
    rng = np.random.default_rng(random_seed)

    # === Sample epsilon combinations ===
    idx = rng.choice(len(all_epsilon_combinations), size=n_epsilon_samples, replace=False)
    sampled_epsilons = [all_epsilon_combinations[i] for i in idx]

    # --- Initialize result containers ---
    data_dicts = []

    opt = SolverFactory(solver_name)
    opt.options['limits/time'] = 500

    # === Run all simulations ===
    for eps_GWP, eps_SIA in sampled_epsilons:
        for sim_id in range(n_simulations):
            print(f"\n--- Simulation {sim_id + 1}/{n_simulations} for e_GWP={eps_GWP:.0f}, e_SIA={eps_SIA:.0f} ---")
            start_time = time.time()

            # --- Reload data for each simulation ---
            data = DataPortal()
            data.load(filename="Data_blending.dat", model=model)
            instance = model.create_instance(data)

            # Set epsilon values
            instance.epsilon_param_GWP.set_value(eps_GWP)
            instance.epsilon_param_SIA.set_value(eps_SIA)

            # --- Generate random FW supply ---
            mean = 18225
            std_dev = 3324
            sigma = np.sqrt(np.log(1 + (std_dev / mean) ** 2))
            mu = np.log(mean) - 0.5 * sigma ** 2
            FW_supply = rng.lognormal(mean=mu, sigma=sigma)
            instance.FWsupply_availability.set_value(FW_supply)

            # --- Generate random macronutrients ---
            vals = {
                'Carbohydrate': np.clip(rng.normal(0.58, 0.12), 0.37, 0.75),
                'Protein': np.clip(rng.normal(0.16, 0.05), 0.05, 0.24),
                'Lipid': np.clip(rng.normal(0.16, 0.07), 0.056, 0.28)
            }
            total = sum(vals.values())
            uncertain_macronutrients = {k: v / total for k, v in vals.items()}

            for n in instance.Macronutrients:
                instance.FWMacronutrient[n].set_value(uncertain_macronutrients[n])

            # --- Solve the model ---
            try:
                results = opt.solve(instance, tee=False)
            except Exception as e:
                print(f"  ! Solver crashed in simulation {sim_id+1}: {e}")
                continue

            # --- Skip runs that did not reach a usable optimal solution ---
            # CHANGED: previously infeasible/failed solves were still recorded,
            # which polluted the results. Now they are skipped.
            tc = results.solver.termination_condition
            if tc not in (TerminationCondition.optimal,
                          TerminationCondition.locallyOptimal,
                          TerminationCondition.feasible):
                print(f"  ! Skipped sim {sim_id+1}: termination_condition = {tc}")
                continue

            elapsed_time = time.time() - start_time

            # --- Extract results ---
            data_dict = {
                'GWP Epsilon': eps_GWP,
                'SIA Epsilon': eps_SIA,
                'Simulation': sim_id + 1,
                'Runtime (s)': round(elapsed_time, 2),
                'NPV': value(instance.npv),
                'GWP Savings': value(instance.GWPSavings),
                'Job generation': value(instance.SIA),
                'GWPcredit': value(instance.GWPcredit),
                'GWPelectricity': value(instance.GWPelectricity),
                'GWPcoolingwater': value(instance.GWPcoolingwater),
                'GWPheat': value(instance.GWPheat),
                'GWPchilling': value(instance.GWPchilling),
                'GWPchemicalLCA': value(instance.GWPchemicalLCA),
                'GWPEmissionDirect': value(instance.GWPEmissionDirect),
                'FW Supply (MT/day)': value(instance.FWsupply),
                'FW Supply availability (MT/day)': FW_supply,
                'Carbohydrate': uncertain_macronutrients['Carbohydrate'],
                'Protein': uncertain_macronutrients['Protein'],
                'Lipid': uncertain_macronutrients['Lipid'],
                'Bioethanol (MT/day)': value(instance.TotalBioethanol),
                'LA (MT/day)': value(instance.TotalLA),
                'Butanol (MT/day)': value(instance.TotalButanol),
                'BDO (MT/day)': value(instance.TotalBDO),
                'SA (MT/day)': value(instance.TotalSA),
                'Biodiesel (MT/day)': value(instance.TotalBiodiesel),
                'Protein (MT/day)': value(instance.TotalProtein),
                'Glycerol (MT/day)': value(instance.TotalGlycerol),
                'BioCNG (MT/day)': value(instance.TotalBioCNG),
                'Fertilizer (MT/day)': value(instance.TotalFertilizer),
                'Compost (MT/day)': value(instance.Compost_product),
                'CO2 (MT/day)': value(instance.TotalCO2),
                'Electricity (kWh)': value(instance.ElectricityGenerated),
                'Ethanol (MT/day)': value(instance.EthanolCoproduct),
                'Acetone (MT/day)': value(instance.TotalAcetoneCoproduct),
                'H2 (MT/day)': value(instance.TotalH2Coproduct),
                'Capex ($)': value(instance.total_capital_investment),
                'Opex ($/year)': value(instance.total_operating_cost),
                'Revenue ($/year)': value(instance.total_product_revenue),
                'OrganicWaste': value(instance.Organicwaste),
                'SolidWaste':  value(instance.SolidWaste),
                'FlueGas':     value(instance.FlueGasStream),
                'OffGas':      value(instance.OffgasStream),
                'TotalOffGas': value(instance.Total_OffgasStream),
            }

            # Flatten Pyomo sets
            data_dict.update({f'StageSelected_{k}': value(instance.StageSelected[k]) for k in instance.StageSelected})
            data_dict.update({f'TechnicalWeight_{k}': value(instance.TechnicalWeight[k]) for k in instance.TechnicalWeight})
            data_dict.update({f'Tavg_{k}': value(instance.Tavg[k]) for k in instance.Tavg})
            data_dict.update({f'GlucoseSelected_{k}': value(instance.GlucoseSelected[k]) for k in instance.GlucoseSelected})
            data_dict.update({f'DCF_list_{year}': value(instance.discounted_cash_flow[year]) for year in instance.discounted_cash_flow})
            data_dict.update({f'Depreciation_list_{year}': value(instance.depreciation[year]) for year in instance.depreciation})
            data_dict.update({f'GrossProfit_list_{year}': value(instance.gross_profit[year]) for year in instance.gross_profit})
            data_dict.update({f'ProfitBeforeTax_list_{year}': value(instance.profit_before_tax[year]) for year in instance.profit_before_tax})
            data_dict.update({f'IncomeTax_list_{year}': value(instance.income_tax[year]) for year in instance.income_tax})
            data_dict.update({f'NetProfit_list_{year}': value(instance.net_profit[year]) for year in instance.net_profit})
            data_dict.update({f'NetCashFlow_list_{year}': value(instance.net_cash_flow[year]) for year in instance.net_cash_flow})

            # Append to overall results
            data_dicts.append(data_dict)

            # === Checkpoint save (every run) ===
            write_header = not os.path.exists(checkpoint_path)
            pd.DataFrame([data_dict]).to_csv(checkpoint_path, mode='a', header=write_header, index=False)
            print(f"  saved: sim {sim_id+1}, eps_GWP={eps_GWP:.0f}, eps_SIA={eps_SIA:.0f}")

    # === Save final results to Excel ===
    df_final = pd.DataFrame(data_dicts)
    with pd.ExcelWriter(full_path, engine='openpyxl', mode='w') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Montecarlo Results')

    print(f"\nAll Monte Carlo results saved to Excel: {full_path}")
    print(f"Checkpoint CSV (incremental saves): {checkpoint_path}")

    return df_final


# ===================================================
# Main
# ===================================================
def main():
    model = build_model()
    df = run_montecarlo(
        model,
        n_simulations=100,
        n_epsilon_samples=30,
        solver_name='scip',
        random_seed=42
    )


if __name__ == "__main__":
    main()