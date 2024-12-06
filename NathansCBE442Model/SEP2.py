import pyomo.environ as pyo

from FixedOutletRatioBlock import FixedOutletRatioBlock, FixedOutletRatioBlockParams

class SEP2Params(FixedOutletRatioBlockParams):
    def _DefineParams(self):
        self.HP_coef = 0.058 
        self.COOL_coef = 0.1186 

        self.ELEC_coef = 4.9163e-4 #kW / (hg / hr)

    def __init__(self):
        super().__init__(
            inletStreams = [
                "IN"
            ],
            outletStreams = [
                "TOP",
                "BOT"
            ],
            streamCompositions = {
                "IN": ["DECALIN","PE"],
                "TOP": ["DECALIN"],
                "BOT": ["PE"]
            },
            utilities = ["ELEC","COOL","HP"],
            outletRatios={
                "PE": {
                    "BOT": 1.0
                },
                "DECALIN": {
                    "TOP": 1.0
                }
            },
            sizeFactor=2.2569E-03, #m^3 / (kg/hr)
            EquipCostParams=(
                47.8814, # k$
                3.1500, # m^3
                0.6660 
            )
        )
        self.maxFlow = 1e5

class SEP2(FixedOutletRatioBlock):
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


    def __init__(self,params:SEP2Params):
        super().__init__(params,addBaseElements=False)

        self._AddSets(addBaseSets=True)
        self._AddVars(addBaseVars=True)
        self._AddConstrs(addBaseConstrs=True)

    def UtilityDemand_Func(self, _, u):
        if u == "ELEC":
            return self.U[u] == self.params.ELEC_coef * self.F_TOT
        elif u == "COOL":
            return self.U[u] == self.params.COOL_coef * self.F["PE","IN"]
        elif u == "HP":
            return self.U[u] == self.params.HP_coef * self.F["PE","IN"]
        

def Test1():
    from PyomoTools.IO import ModelToExcel
    params= SEP2Params()
    model = SEP2(params)

    Fins = {
        "PE": 9.446389723402051,
        "DECALIN": 75.15471216448367
    }
    model.InConstr = pyo.Constraint(model.species,rule=lambda model,i: model.F_IN[i] == Fins[i])

    solver = pyo.SolverFactory("scip")

    solver.solve(model,tee=True)

    ModelToExcel(model,"sep2.xlsx")


if __name__ == "__main__":
    Test1()
  