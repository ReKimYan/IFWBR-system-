# models/inequality_constraints.py
from pyomo.environ import *

class InequalityConstraintsModel:
    """Add global inequality constraints to the model."""

    def __init__(self, model):
        self.model = model
        self._add_constraints()

    def _add_constraints(self):
        m = self.model

        ## -------------------------------
        # FW supply constraint
        # --------------------------------
        def supply_upper_bound_rule(m):
            return   m.FWsupply <= m.FWsupply_availability   # Ensure that FW supply is below the availability
        m.supplyUpperBoundConstraints = Constraint(rule=supply_upper_bound_rule)
        
        ## -------------------------------
        # Enzymatic hydrolysis capacity
        # --------------------------------
        def EH_capacity_bound_rule(m):
            FWsupply_EH = m.Finfeedstock['enzymatic-hydrolysis'] 
            return FWsupply_EH <= m.CapacityFWManagement['enzymatic-hydrolysis']
        m.EH_capacity_Constraint = Constraint(rule=EH_capacity_bound_rule)
        
        ## -------------------------------
        # Bioethanol
        # --------------------------------
        def Bioethanol_demand_upper_bound_rule(m):
            bioethanol_upper_product = sum(m.BioethanolProduct[ n, 'BioethanolProcess', 'Cooler'] for n in m.Components)
            return bioethanol_upper_product  <= m.ProductDemand ['bioethanol'] 
        m.BioethanoldemandUpperBoundConstraint = Constraint(rule=Bioethanol_demand_upper_bound_rule)
        
        ## -------------------------------
        # Lactic Acid 
        # --------------------------------
        def LacticAcid_demand_upper_bound_rule(m):
            lacticacid_upper_product = sum(m.LacticAcidProduct[ n, 'LacticAcidProcess','DT'] for n in m.Components)
            return lacticacid_upper_product  <= m.ProductDemand ['LacticAcid'] 
        m.LacticAciddemandUpperBoundConstraint = Constraint(rule=LacticAcid_demand_upper_bound_rule)
        
        ## -------------------------------
        # BDO product
        # --------------------------------
        def BDO_demand_upper_bound_rule(m):
            BDO_upper_product = sum(m.BDO_product [ n, 'BDOProcess','DT'] for n in m.Components )
            return BDO_upper_product  <=  m.ProductDemand['BDO'] 
        m.BDOdemandUpperBoundConstraint = Constraint(rule=BDO_demand_upper_bound_rule)
        
        # -------------------------------
        # Succinic Acid product
        # --------------------------------
        def SuccinicAcid_demand_upper_bound_rule(m):
            succinicacid_upper_product = sum(m.SuccinicAcidProduct [ n, 'SuccinicAcidProcess','Centrifugal'] for n in m.Components )
            return succinicacid_upper_product  <= m.ProductDemand['SuccinicAcid'] 
        m.SuccinicAciddemandUpperBoundConstraint = Constraint(rule=SuccinicAcid_demand_upper_bound_rule)
        
        ## -------------------------------
        # Butanol
        # --------------------------------
        def Butanol_demand_upper_bound_rule(m):
            butanol_upper_product = sum(m.Butanol_product [ n, 'ButanolProcess', 'DT'] for n in m.Components)
            return butanol_upper_product  <= m.ProductDemand ['Butanol'] 
        m.ButanoldemandUpperBoundConstraint = Constraint(rule=Butanol_demand_upper_bound_rule)
        
        
        ## -------------------------------
        # Composting demand
        # --------------------------------
        def Composting_demand_bound_rule(m):
            Compost_product = m.Compost_product
            return Compost_product <= m.ProductDemand ['compost']
        m.Composting_demand_Constraint = Constraint(rule=Composting_demand_bound_rule)
        
        #-------------------------------
        # Electricity capacity
        # -------------------------------        
        def Electricity_capacity_bound_rule(m):
            Electricity_product = m.ElectricityGenerated
            return Electricity_product <= m.ProductDemand ['electricity']
        m.Electricity_capacity_Constraint = Constraint(rule=Electricity_capacity_bound_rule)
        
        #-------------------------------
        # BioCNG demand
        # -------------------------------
        def BioCNG_capacity_bound_rule(m):
            BioCNG_product = sum(m.BioCNG_product[ n,'AnaerobicDigestion']for n in m.Components)
            return BioCNG_product <= m.ProductDemand ['CH4']
        m.BioCNG_capacity_Constraint = Constraint(rule=BioCNG_capacity_bound_rule)
        