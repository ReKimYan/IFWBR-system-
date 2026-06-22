#Foodwaste selection
from pyomo.environ import *

# ======================================================
# FW allocation model
# ======================================================
class FWAllocationModel:
    """Foodwaste allocation constraints (no sets, params, or vars)."""

    def __init__(self, model):
        """Attach FW allocation constraints to an existing model."""
        self.model = model
        self._add_constraints()

    def _add_constraints(self):
        m = self.model
        
        ## -------------------------------
        # Feedstock portion for valorisation stages
        # --------------------------------  
        def Finfeedstock_composition_inflow_rule(m, j):
            return m.Finfeedstock[j] == m.Tavg[j] * sum(m.Fmill_component[n, 'grinding', 'Crusher'] for n in m.Macronutrients)
        m.total_feedstock_composition_inflow = Constraint(m.FWManagementOption, rule=Finfeedstock_composition_inflow_rule)

        ## -------------------------------
        # Define technical weight as expression (recommended fix)
        # --------------------------------  
        def technical_weight_expr(m, j):
            return m.TechnicalScore[j] / m.MaxTechnicalScore
        m.TechnicalWeight = Expression(m.FWManagementOption, rule=technical_weight_expr)

        ## -------------------------------
        # Tavg = StageSelected[j] * TechnicalWeight[j]
        # --------------------------------          
        def Tavg_rule(m, j):
            return m.Tavg[j] == m.StageSelected[j] * m.TechnicalWeight[j]
        m.Tavg_constraint = Constraint(m.FWManagementOption, rule=Tavg_rule)

        ## -------------------------------
        # stage can be selected
        # --------------------------------
        def one_feedstock_rule(m):
            return sum(m.Tavg[j] for j in m.FWManagementOption) == 1
        m.onefeedstock = Constraint(rule=one_feedstock_rule)

# ======================================================
# Glucose-based process selection model
# ======================================================
class GlucoseSelectionModel:
    """Glucose selection constraints (no sets, params, or vars)."""

    def __init__(self, model):
        """Attach Glucose selection constraints to an existing model."""
        self.model = model
        self._add_constraints()

    def _add_constraints(self):
        m = self.model
        
        ## -------------------------------
        # Constraint: Allocate component flows proportionally to selection weight
        # --------------------------------  
        def glucose_flow_allocation_rule(m, n, p):
            return m.Finglucose_component[n, p] == m.FCentrifugal1_liquid[n, 'enzymatic-hydrolysis', 'Centrifugal'] * m.GlucoseSelected[p]
        m.allocate_glucose = Constraint(m.Components, m.GlucoseUpgrading, rule=glucose_flow_allocation_rule)

        ## -------------------------------
        # Constraint: Total sum of process shares should be 1 (if full distribution)
        # --------------------------------  
        def process_share_sum_rule(m):
            return sum(m.GlucoseSelected[p] for p in m.GlucoseUpgrading) == 1
        m.total_process_share = Constraint(rule=process_share_sum_rule)

# ======================================================
# Variable selection model
# ======================================================
class VariableSelectionModel:
    """Unified class that groups AnaerobicDigestion, Composting, and Incineration models."""

    def __init__(self, model):
        """Attach all process constraints to one existing AbstractModel."""
        self.model = model
        self.FWAllocation = FWAllocationModel(model)
        self.GlucoseSelection = GlucoseSelectionModel(model)

    def get_models(self):
        """Return all sub-models (for inspection or solving separately)."""
        return {
            'FWAllocation': self.FWAllocation.model,
            'GlucoseSelection': self.GlucoseSelection.model,
        }
