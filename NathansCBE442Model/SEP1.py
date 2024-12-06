import pyomo.environ as pyo

from PyomoTools import LoadIndexedSet

from .Block import Block, BlockParams
from .ThermoParameters import ThermoParameters

class SEP1Params(BlockParams):
    def NathansFit(self,feed,rec,A,B,C,D,E):
        #TODO: REPORT NEW FORM
        return A + B * feed + C * rec + D * feed * rec + E * feed / (1-rec)
    
    def EquipmentCostFit(self,feed,rec,A,B,C,D,E):
        #TODO: REPORT NEW FORM
        return A * feed**B + C * feed * (1-rec)**D + E

    def _DefineParams(self):
        #TODO: REPORT NEW VALUES
        self.utilityCoefs = {
            "COOL": [2.08574e-04, 2.30288e-01, -2.14784e-04, 9.42690e-02, 3.12708e-03],
            "HP": [-1.53187e-05, 7.27182e-02, 1.57717e-05, 1.51983e-01, 3.16489e-03],
            "ELEC": 5.33
        }

        self.equipmentCostCoefs = [3.87143e+02, 4.89396e-01, 9.06817e-03, -1.02898e+00, 4.10637e+04]

        self.fixedPhi = {
            "H2O": {
                "H2_OUT": 0.0528,
                "H2O_OUT": 0.9472
            }
        }

        self.sizeFactor = 1.9862 #m^3 / (kg / hr)
        self.minS = None

        self.maxFlow = 1e5

        self.P = 1 #atm

    def __init__(self,thermoParams:ThermoParameters):
        super().__init__(
            inletStreams = [
                "IN"
            ],
            outletStreams = [
                "H2_OUT",
                "H2O_OUT",
                "SOLV_OUT"
            ],
            streamCompositions = {
                "IN": ["GVL","DECALIN","H2O","H2"],
                "H2_OUT": ["H2","H2O"],
                "H2O_OUT": ["H2O","DECALIN"],
                "SOLV_OUT": ["GVL","DECALIN"]
            },
            utilities = ["COOL","ELEC","HP"]
        )
        
        

class SEP1(Block):
    def _AddSets(self,addBaseSets=False):
        if addBaseSets:
            super()._AddBaseSets()
        pass

    def _AddVars(self,addBaseVars=False):
        if addBaseVars:
            super()._AddBaseVars()

        self.R = pyo.Var(domain=pyo.Reals,bounds=(0.94703,0.98965)) #TODO: FORCE CONSTRAIN THIS.

    def OutletSpecification_Func(self, _, i, s):
        if i == "DECALIN":
            if s == "H2O_OUT":
                return self.F[i,s] == self.F_OUT[i] * (1 - self.R)
            elif s == "SOLV_OUT":
                return self.F[i,s] == self.F_OUT[i] * self.R
        elif i == "GVL":
            if s == "SOLV_OUT":
                return self.F[i,s] == self.F_OUT[i]
        elif i == "H2O":
            return self.F[i,s] == self.params.fixedPhi[i][s] * self.F_OUT[i]
        elif i == "H2":
            if s == "H2_OUT":
                return self.F[i,s] == self.F_OUT[i]
            
    def UtilityDemand_Func(self, _, u):
        if u != "ELEC":
            params = self.params.utilityCoefs[u]
            return self.U[u] == self.params.NathansFit(self.F_TOT,self.R,*params)
        else:
            coef = self.params.utilityCoefs[u] / 1000
            return self.U[u] == coef * self.F_TOT
        
    def EquipmentCost_Func(self):
        return self.params.EquipmentCostFit(self.F_TOT,self.R,*self.params.equipmentCostCoefs) / 1000

    def _AddConstrs(self,addBaseConstrs=False):
        if addBaseConstrs:
            super()._AddBaseConstrs()


    def __init__(self,params:SEP1Params):
        super().__init__(params,addBaseElements=False)

        self._AddSets(addBaseSets=True)
        self._AddVars(addBaseVars=True)
        self._AddConstrs(addBaseConstrs=True)

def Test1():
    from PyomoTools.IO import ModelToExcel
    thermoParams = ThermoParameters()
    params= SEP1Params(thermoParams)
    model = SEP1(params)

    Fins = {
        "H2O": 0.990373412129611,
        "GVL": 1.853036969629321,
        "DECALIN": 4.797109287094703,
        "H2": 0.001411172793055
    }
    model.InConstr = pyo.Constraint(model.species,rule=lambda model,i: model.F_IN[i] == Fins[i])

    model.RConstr = pyo.Constraint(expr=model.R == 0.45)

    solver = pyo.SolverFactory("scip")

    solver.solve(model,tee=True)

    ModelToExcel(model,"sep1.xlsx")


if __name__ == "__main__":
    Test1()
