import pyomo.environ as pyo

from Block import Block,BlockParams

class ExtruderParams(BlockParams):
    def _DefineParams(self):
        self.ELEC_coef = 0.26

    def __init__(self):
        super().__init__(
            inletStreams = [
                "IN"
            ],
            outletStreams = [
                "OUT"
            ],
            streamCompositions = {
                "IN": ["PE"],
                "OUT": ["PE"]
            },
            utilities = ["ELEC",]
        )
        self.sizeFactor = 1 # 1 / (kg / hr)
        self.EquipCost_A = 127.438#326.274 # k$
        self.EquipCost_B = 360
        self.EquipCost_C = 0.9
        self.maxFlow = 1e5


class Extruder(Block):
    def UtilityDemand_Func(self,_, u):
        if u == "ELEC":
            return self.U[u] == self.params.ELEC_coef * self.F_TOT
        
def Test1():
    from PyomoTools.IO import ModelToExcel
    from PyomoTools import InfeasibilityReport

    params= ExtruderParams()
    model = Extruder(params)

    Fins = {
        "PE": 9.446389723402051
    }
    model.InConstr = pyo.Constraint(model.species,rule=lambda model,i: model.F_IN[i] == Fins[i])

    solver = pyo.SolverFactory("scip")

    solver.solve(model,tee=True)

    ModelToExcel(model,"extruder.xlsx")
    report = InfeasibilityReport(model,onlyInfeasibilities=False)
    report.WriteFile("Extruder_Constraints.txt")


if __name__ == "__main__":
    Test1()