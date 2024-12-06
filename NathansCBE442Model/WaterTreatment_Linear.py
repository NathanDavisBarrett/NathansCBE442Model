import pyomo.environ as pyo

from FixedOutletRatioBlock import FixedOutletRatioBlockParams, FixedOutletRatioBlock
from ThermoParameters import ThermoParameters

class WaterTreatmentBlockParams(FixedOutletRatioBlockParams):    
    def __init__(self,thermoParams:ThermoParameters):
        super().__init__(
            inletStreams = [
                "IN"
            ],
            outletStreams = [
                "VAP",
                "LIQ"
            ],
            streamCompositions = {
                "IN": ["H2O","DECALIN"],
                "LIQ": ["H2O","DECALIN"],
                "VAP": ["H2O","DECALIN"],
            },
            utilities = ["COOL"],
            outletRatios = {
                "H2O": {
                    "VAP": 0.3727,
                    "LIQ": 0.6273
                },
                "DECALIN": {
                    "VAP": 0.08287,
                    "LIQ": 0.91713
                }
            },
            sizeFactor=1.9862, #m^3 / (kg / hr)
            EquipCostParams=(
                22.300, # k$
                49.655, #m^3
                0.7
            )
        )

        self.maxFlow = 1e5
        self.minS = 5

        self.CoolingWaterRatio = 391.657 / 1000 #kW / (kg/ hr)

class WaterTreatmentBlock(FixedOutletRatioBlock):
    def __init__(self,params:WaterTreatmentBlockParams):
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
    
    def _AddConstrs(self,addBaseConstrs=False):
        if addBaseConstrs:
            super()._AddBaseConstrs()

    def UtilityDemand_Func(self, _, u):
        if u != "COOL":
            raise Exception()

        return self.U[u] == self.params.CoolingWaterRatio * self.F_TOT
    
def Test1():
    from PyomoTools.IO import ModelToExcel
    from PyomoTools import InfeasibilityReport
    thermoParams = ThermoParameters()
    params= WaterTreatmentBlockParams(thermoParams)
    model = WaterTreatmentBlock(params)

    Fins = {
        "H2O": 100,
        "DECALIN": 5
    }
    model.InConstr = pyo.Constraint(model.species,rule=lambda model,i: model.F_IN[i] == Fins[i])

    solver = pyo.SolverFactory("scip")

    solver.solve(model,tee=True)

    ModelToExcel(model,"waterTreatment.xlsx")

    report = InfeasibilityReport(model,onlyInfeasibilities=False)
    report.WriteFile("allConstrs.txt")

if __name__ == "__main__":
    Test1()