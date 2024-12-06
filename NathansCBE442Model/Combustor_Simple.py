import pyomo.environ as pyo

from Block import BlockParams,Block
from ThermoParameters import ThermoParameters

class CombustorParams(BlockParams):
    def __init__(self,thermoParams:ThermoParameters):
        super().__init__(
            inletStreams=["H2_IN","DEC_IN","ATM_IN","CH4_IN"],
            outletStreams=["OUT",],
            streamCompositions={
                "H2_IN": ["H2","H2O"],
                "DEC_IN": ["H2O","DECALIN"],
                "ATM_IN": ["N2","O2"],
                "CH4_IN": ["CH4"],
                "OUT": ["H2O","CO2","O2","N2"]
            },
            utilities=["HP"]
        )
        self.Udomain = pyo.Reals
        self.Hcomb = thermoParams.Hcomb
        self.Cp = thermoParams.Cp

        self.T = 400 #degC

        self.T_in = {
            "H2_IN": 200,
            # "DEC_IN": #VARIABLE
            "ATM_IN": 25,
            "CH4_IN": 25
        }

        #Mass fractions of standard air
        self.x_air = {
            "N2": 0.75,
            "O2": 0.25
        }

        #Mass basis stoichiometric coefficient for the complete combustion of each species
        self.nu = {
            "H2": {
                "O2": -8,
                "H2O": 9,
                "CO2": 0
            },
            "H2O": {
                "O2": 0,
                "H2O": 1,
                "CO2": 0
            },
            "DECALIN": {
                "O2": -3.362318841,
                "H2O": 1.173913043,
                "CO2": 3.188405797
            },
            "CH4": {
                 "O2": -4,
                "H2O": 2.25,
                "CO2": 2.75
            }
        }

        self.O2_Excess = 0.1 #The fraction of incoming oxygen that must remain un-combusted.

        self.maxFlow = 1e5

        self.EquipCost_A = 6.3876e-2 # k$
        self.EquipCost_B = 4.8073e-2 # kW
        self.EquipCost_C = 0.780


class Combustor(Block):
    def __init__(self, params: CombustorParams):
        super().__init__(params,addBaseElements=False)

        self._AddSets(addBaseSets=True)
        self._AddVars(addBaseVars=True)
        self._AddConstrs(addBaseConstrs=True)

    def _AddSets(self,addBaseSets=False):
        if addBaseSets:
            super()._AddBaseSets()
        pass

    def _AddVars(self,addBaseVars=False):
        if addBaseVars:
            super()._AddBaseVars()

        self.T_IN = pyo.Var(self.inletStreams,domain=pyo.NonNegativeReals)


    def _AddConstrs(self,addBaseConstrs=False):
        if addBaseConstrs:
            super()._AddBaseConstrs()

        self.AtmosphericAirCompositionConstraint = pyo.Constraint(expr=self.F["N2","ATM_IN"] == self.params.x_air["N2"] / self.params.x_air["O2"] * self.F["O2","ATM_IN"])

        self.inletCO2Constraint = pyo.Constraint(expr=self.F_IN["CO2"] == 0)

        self.T_IN_Specification = pyo.Constraint(list(self.params.T_in.keys()),rule=lambda _,s: self.T_IN[s] == self.params.T_in[s])

        self.O2_Excess_Enforcement = pyo.Constraint(expr=self.F_OUT["O2"] >= self.F_IN["O2"] * self.params.O2_Excess)

    def MaterialBalance_Func(self,_,i):
        if i in ["H2","DECALIN","CH4"]:
            return self.F_OUT[i] == 0
        elif i in ["O2","CO2","H2O"]:
            return self.F_OUT[i] == self.F_IN[i] + sum(self.F_IN[ip] * self.params.nu[ip][i] for ip in self.params.nu)
        elif i == "N2":
            return self.F_OUT[i] == self.F_IN[i]
        else:
            raise Exception(f"\"{i}\" is not a recognized species.")
        
    def UtilityDemand_Func(self,_, u):
        if u != "HP":
            raise Exception(f"\"{u}\" is not a recognized utility for the combustor.")
        
        dHrxn = sum(self.params.Hcomb[s] * self.F_IN[s] for s in self.params.nu) / 3600

        return self.U[u] == (-dHrxn)*0.5
    
    def SizeDefinition_Func(self):
        return -self.U["HP"]

def Test():
    from PyomoTools.IO import ModelToExcel
    from PyomoTools.Solvers import DefaultSolver

    thermoParams = ThermoParameters()
    params = CombustorParams(thermoParams)
    model = Combustor(params)

    model.F_IN["CH4"].fix(100)

    model.obj = pyo.Objective(expr=sum(model.F_IN[s] for s in model.species),sense=pyo.minimize)

    solver = DefaultSolver("NLP")
    solver.solve(model,tee=True)

    ModelToExcel(model,"Combustor.xlsx")

if __name__ == "__main__":
    Test()


