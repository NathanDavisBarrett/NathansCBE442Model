import pyomo.environ as pyo

from FixedOutletRatioBlock import FixedOutletRatioBlock, FixedOutletRatioBlockParams

class DecanterParams(FixedOutletRatioBlockParams):
    def _DefineParams(self):
        self.ELEC_coef = 0.01

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
                "IN": ["GVL","DECALIN","H2O","CAT","PE"],
                "TOP": ["DECALIN","PE"],
                "BOT": ["GVL","H2O","CAT"]
            },
            utilities = ["ELEC",],
            outletRatios={
                "GVL": {
                    "BOT": 1.0
                },
                "DECALIN": {
                    "TOP": 1.0
                },
                "H2O": {
                    "BOT": 1.0
                },
                "CAT": {
                    "BOT": 1.0
                },
                "PE": {
                    "TOP": 1.0
                },
                "EVOH": {
                    "BOT": 1.0
                }
            },
            sizeFactor = 8.4410E-04, #m / (kg / hr)
            EquipCostParams=(
                31.309, # k$
                7, # m
                0.7
            )
        )

        self.maxFlow = 1e5

class Decanter(FixedOutletRatioBlock):
    def UtilityDemand_Func(self, _, u):
        if u == "ELEC":
            return self.U[u] == self.params.ELEC_coef * self.F_TOT
        

def Test1():
    from PyomoTools.IO import ModelToExcel
    params= DecanterParams()
    model = Decanter(params)

    Fins = {
        "PE": 9.446389723402051,
        "H2O": 1.03079681670633,
        "GVL": 44.47288727110372,
        "DECALIN": 75.15471216448367,
        "EVOH": 0.00101763396064,
        "CAT": 0.014193871889826
    }
    model.InConstr = pyo.Constraint(model.species,rule=lambda model,i: model.F_IN[i] == Fins[i])

    solver = pyo.SolverFactory("scip")

    solver.solve(model,tee=True)

    ModelToExcel(model,"decanter.xlsx")


if __name__ == "__main__":
    Test1()
  