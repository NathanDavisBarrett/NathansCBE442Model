import pyomo.environ as pyo
import numpy as np

from FixedOutletRatioBlock import FixedOutletRatioBlock, FixedOutletRatioBlockParams
from ThermoParameters import ThermoParameters

class ReactorParams(FixedOutletRatioBlockParams):
    def __init__(self,thermoParams):
        super().__init__(
            inletStreams = [
                "FEED",
                "DEC_REC",
                "SEP1_REC",
                "SEP2_REC",
                "S1_REC",
                "H2O_TREAT_REC"
            ],
            outletStreams = [
                "VAP",
                "LIQ"
            ],
            streamCompositions = {
                "FEED": ["PE","EVOH","H2","GVL","DECALIN","CAT","H2O"],
                "DEC_REC": ["GVL","H2O","CAT"],
                "SEP1_REC": ["GVL","DECALIN"],
                "SEP2_REC": ["DECALIN"],
                "S1_REC": ["H2","H2O"],
                "H2O_TREAT_REC": ["H2O","DECALIN"],
                "LIQ": ["GVL","DECALIN","H2O","PE","CAT"],
                "VAP": ["GVL","DECALIN","H2O","H2"]
            },
            utilities = ["ELEC","HP"],
            outletRatios={
                "PE": {"LIQ": 1.0},
                "EVOH": {},
                "DECALIN": {"VAP": 0.06, "LIQ": 0.94},
                "GVL": {"VAP": 0.04, "LIQ": 0.96},
                "CAT": {"LIQ":1.0},
                "H2": {"VAP":1.0},
                "H2O": {"VAP":0.49,"LIQ":0.51}
            },
            sizeFactor = 2.4577e-3, #m^3 / (kg / hr)
            EquipCostParams=(
                93.927, # k$
                11, # m^3
                0.6
            )
        )

        AW = {
            "C": 12,
            "O": 16,
            "H": 1
        }

        n = 500

        self.MW = {
            "EVOH": AW["C"]*2*n + AW["H"]*3.5*n + AW["O"]*n/2,
            "PE": AW["C"]*2*n + AW["H"]*4*n,
            "H2O": AW["H"]*2 + AW["O"],
            "H2": AW["H"]*2
        }

        nu = np.linalg.solve(
            np.array([
                #EVOH ,H2,PE ,H2O
                [0    ,0 ,1  ,0  ], #nu_PE should be 1
                [2*n  ,0 ,2*n,0  ], #Carbon balance
                [3.5*n,2 ,4*n,2  ], #Hydrogen balance
                [n/2  ,0 ,0  ,1  ]  #Oxygen balance
            ]),
            np.array([1,0,0,0])
        )
        
        self.nu = { #Mass basis stoichiometric coef.
            "PE": nu[2] * self.MW["PE"],
            "EVOH": nu[0] * self.MW["EVOH"],
            "DECALIN": 0,
            "GVL": 0,
            "CAT": 0,
            "H2": nu[1] * self.MW["H2"],
            "H2O": nu[3] * self.MW["H2O"]
        }

        self.x_in = {#Fixed inlet mass fractions
            "PE": 0.032,
            "EVOH": 0.008,
            "DECALIN": 0.603,
            "GVL": 0.349,
            "CAT": 0.004,
            "H2": 0.001,
            "H2O": 0.003
        }

        self.residenceTime = 1.5 #hr

        self.zeta_eff = 1.2288e-3 #kW / (kg/hr)

        self.maxFlow = 1e5

        self.theta = 195 #deg C

        self.phases = {
            "FEED": "LIQ",
            "DEC_REC": "LIQ",
            "SEP1_REC": "LIQ",
            "SEP2_REC": "VAP",
            "S1_REC": "VAP",
            "H2O_TREAT_REC": "LIQ"
        }

        self.Cp = thermoParams.Cp
        self.dH_Melt = thermoParams.dH_Melt

        self.thetas = { #Fixed steam temperatures (degC)
            "FEED": 25,
            "DEC_REC": 40,
            "SEP1_REC": 200,
            "SEP2_REC": 40,
            "S1_REC": 40,
            "H2O_TREAT_REC": 170
        }

class Reactor(FixedOutletRatioBlock):
    def _AddSets(self,addBaseSets=False):
        if addBaseSets:
            super()._AddBaseSets()
        pass

    def _AddVars(self,addBaseVars=False):
        if addBaseVars:
            super()._AddBaseVars()

        #Extent of reaction
        self.E = pyo.Var(domain=pyo.NonNegativeReals)

        #Temperature of each inlet stream
        self.T = pyo.Var(self.inletStreams,domain=pyo.NonNegativeReals)

    def _AddConstrs(self,addBaseConstrs=False):
        if addBaseConstrs:
            super()._AddBaseConstrs()

        #Assuming complete conversion of EVOH
        self.CompleteConversionEVOH = pyo.Constraint(expr=self.F_OUT["EVOH"] == 0)

        def FixedInletComposition(self,i):
            return self.F_IN[i] == self.params.x_in[i] * self.F_TOT
        self.FixedInletComposition = pyo.Constraint(self.species,rule=FixedInletComposition)

        self.SetTemperatures = pyo.Constraint(list(self.params.thetas.keys()),rule=lambda _,i: self.T[i] == self.params.thetas[i])

    def MaterialBalance_Func(self,_,i):
        return self.F_OUT[i] == self.F_IN[i] + self.params.nu[i] * self.E
    
    def ELEC_Demand(self):
        return self.U["ELEC"] == self.params.zeta_eff * self.F_TOT
    
    def HP_Demand(self):
        heat = sum(self.F[i,s] * self.params.Cp[i][self.params.phases[s]] * (self.params.theta - self.T[s]) for s in self.inletStreams for i in self.streamCompositions[s]) / 3600
        melt = self.F["PE","FEED"] * self.params.dH_Melt["PE"] / 3600
        return self.U["HP"] == heat + melt
    
    def UtilityDemand_Func(self,_, u):
        if u == "ELEC":
            return self.ELEC_Demand()
        elif u == "HP":
            return self.HP_Demand()
        else:
            raise Exception(f"\"{u}\" is not a recognized utility")

    def __init__(self,params:ReactorParams):
        super().__init__(params,addBaseElements=False)

        self._AddSets(addBaseSets=True)
        self._AddVars(addBaseVars=True)
        self._AddConstrs(addBaseConstrs=True)

def Test():
    from PyomoTools.Solvers import DefaultSolver
    from PyomoTools.IO import ModelToExcel

    thermoParams = ThermoParameters()

    params = ReactorParams(thermoParams)
    model = Reactor(params)

    model.F["PE","FEED"].fix(10)

    solver = DefaultSolver("NLP")
    solver.solve(model,tee=True)

    ModelToExcel(model,"LinearReactorTest.xlsx")

if __name__ == "__main__":
    Test()