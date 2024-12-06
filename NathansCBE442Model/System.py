import pyomo.environ as pyo

from PyomoTools.MergeableModel import MergableModel

from LinearReactor import Reactor, ReactorParams
from SEP1 import SEP1, SEP1Params
from Decanter import Decanter, DecanterParams
from SEP2 import SEP2, SEP2Params
from Extruder import Extruder, ExtruderParams
from WaterTreatment_Linear import WaterTreatmentBlockParams, WaterTreatmentBlock
from Splitter import SplitterParams,ContinuousSplitter,SelectionSplitter
from Combustor_Simple import Combustor, CombustorParams
from ThermoParameters import ThermoParameters
from Economics import EconomicParams,Economics

class SystemParams:
    def __init__(self):
        thermoParams = ThermoParameters()
        self.componentParams = {
            "RXR": ReactorParams(thermoParams),
            "SEP1": SEP1Params(thermoParams),
            "DECANT": DecanterParams(),
            "SEP2": SEP2Params(),
            "EXTRUDE": ExtruderParams(),
            "WATER_TREATMENT": WaterTreatmentBlockParams(thermoParams),
            "S1": SplitterParams(3,["H2","H2O"]),
            "S2": SplitterParams(3,["H2O","DECALIN"]),
            "COMB": CombustorParams(thermoParams)
        }

        self.streamEqualities = [
            ("RXR","VAP","SEP1","IN"),
            ("RXR","LIQ","DECANT","IN"),
            ("SEP1","SOLV_OUT","RXR","SEP1_REC"),
            ("DECANT","BOT","RXR","DEC_REC"),
            ("DECANT","TOP","SEP2","IN"),
            ("SEP2","TOP","RXR","SEP2_REC"),
            ("SEP2","BOT","EXTRUDE","IN"),
            ("SEP1","H2_OUT","S1","IN"),
            ("S1","OUT_1","RXR","S1_REC"), 
            ("S1","OUT_3","COMB","H2_IN"),
            ("SEP1","H2O_OUT","S2","IN"),
            ("S2","OUT_1","COMB","DEC_IN"),
            ("S2","OUT_3","WATER_TREATMENT","IN"),
            ("WATER_TREATMENT","LIQ","RXR","H2O_TREAT_REC")
        ]

        self.utilities = [] #These will be collected from block utilities.

        self.feedComposition = {
            "PE": 0.8,
            "EVOH": 0.2
        }

        self.decalinVentLimit = 500 #kg / year

        self._finalize()

    def _finalize(self):
        #Assemble a list of all species in all equated streams.
        fullStreamEqualities = [None for _ in self.streamEqualities]
        for i,(src,srcStrmName,snk,snkStrmName) in enumerate(self.streamEqualities):
            srcStrmElements = set(self.componentParams[src].streamCompositions[srcStrmName])
            snkStrmElements = set(self.componentParams[snk].streamCompositions[snkStrmName])

            assert srcStrmElements == snkStrmElements, f"The steam equality {src}.{srcStrmName} = {snk}.{snkStrmName} does not have matching species.\n\t{srcStrmElements}\n\t\tVERSUS\n\t{snkStrmElements}"

            fullStreamEqualities[i] = [(src,srcStrmName,snk,snkStrmName,s) for s in srcStrmElements]
        self.streamEqualities = [eq for strSpec in fullStreamEqualities for eq in strSpec]

        self.utilities = set([])
        for p in self.componentParams.values():
            self.utilities.update(p.utilities)
        self.utilities = list(self.utilities)

        self.economicParams = EconomicParams(
            blockNames=list(self.componentParams.keys()),
            utilities=self.utilities
        )


class System(MergableModel):
    def _AddSubModels(self):
        self.AddSubModel("RXR",Reactor(self.params.componentParams["RXR"]))
        self.AddSubModel("SEP1",SEP1(self.params.componentParams["SEP1"]))
        self.AddSubModel("DECANT",Decanter(self.params.componentParams["DECANT"]))
        self.AddSubModel("SEP2",SEP2(self.params.componentParams["SEP2"]))
        self.AddSubModel("EXTRUDE",Extruder(self.params.componentParams["EXTRUDE"]))
        self.AddSubModel("WATER_TREATMENT",WaterTreatmentBlock(self.params.componentParams["WATER_TREATMENT"]))
        self.AddSubModel("S1",ContinuousSplitter(self.params.componentParams["S1"]))
        self.AddSubModel("S2",ContinuousSplitter(self.params.componentParams["S2"]))
        self.AddSubModel("COMB",Combustor(self.params.componentParams["COMB"]))
        self.AddSubModel("ECON",Economics(self.params.economicParams))

    def _AddSets(self):
        pass

    def _AddVars(self):
        self.U_TOT = pyo.Var(self.params.utilities,domain=pyo.NonNegativeReals)

        self.F_FILM = pyo.Var(domain=pyo.NonNegativeReals)


    def _AddConstrs(self):
        def StreamEqualities(self,srcBlockName,srcStrName,snkBlockName,snkStrName,spec):
            srcBlock = getattr(self,srcBlockName)
            snkBlock = getattr(self,snkBlockName)
            return srcBlock.F[spec,srcStrName] == snkBlock.F[spec,snkStrName]
        self.StreamEqualities = pyo.Constraint(self.params.streamEqualities,rule=StreamEqualities)

        def U_TOT_Definition(self,u):
            sm = 0
            for blockName in self.params.componentParams:
                blockUtilities = self.params.componentParams[blockName].utilities
                if u in blockUtilities:
                    subModel = getattr(self,blockName)
                    sm += subModel.U[u]
            return self.U_TOT[u] >= sm
        self.U_TOT_Definition = pyo.Constraint(self.params.utilities,rule=U_TOT_Definition)

        def F_FILM_Definition(model):
            return model.F_FILM == model.RXR.F["PE","FEED"] + model.RXR.F["EVOH","FEED"]
        self.F_FILM_Definition = pyo.Constraint(rule=F_FILM_Definition)

        def FilmComposition_Constr(model,i):
            return model.RXR.F[i,"FEED"] == self.params.feedComposition[i] * model.F_FILM
        self.FilmComposition_Constr = pyo.Constraint(list(self.params.feedComposition.keys()),rule=FilmComposition_Constr)

        def EquipmentCostEqualities(model,i):
            return model.ECON.BlockEquipmentCost[i] == getattr(model,i).C
        self.EquipmentCostEqualities = pyo.Constraint(self.params.economicParams.blockNames,rule=EquipmentCostEqualities)

        self.NetUtilityDemandEqualities = pyo.Constraint(self.params.utilities,rule=lambda _,u: self.ECON.NetUtilityDemand[u] == self.U_TOT[u])

        #Purchase Rate Equalities
        self.FilmPurchaseRateEquality = pyo.Constraint(expr=self.ECON.PurchaseRate["FILM"] == self.F_FILM)
        self.DecalinPurchaseRateEquality = pyo.Constraint(expr=self.ECON.PurchaseRate["DECALIN"] == self.RXR.F["DECALIN","FEED"])
        self.CH4PurchaseRateEquality = pyo.Constraint(expr=self.ECON.PurchaseRate["CH4"] == self.COMB.F["CH4","CH4_IN"])

        #Sell Rate Equalities
        self.PelletSellRateEquality = pyo.Constraint(expr=self.ECON.SellRate["PE"] == self.EXTRUDE.F["PE","OUT"])

        #Load Quantity Equalities
        self.LoadQuantityEquality = pyo.Constraint(self.ECON.loadMaterials,rule=lambda _,i: self.ECON.LoadQuantity[i] == self.RXR.F_IN[i] * self.params.componentParams["RXR"].residenceTime)

        #Carbon Equality
        self.CarbonEquality = pyo.Constraint(expr=self.ECON.CarbonRate == self.COMB.F["CO2","OUT"])

        #Decalin Limit
        self.DecalinVentLimit = pyo.Constraint(expr= (self.S2.F["DECALIN","OUT_2"] + self.WATER_TREATMENT.F["DECALIN","VAP"]) * self.params.economicParams.operatingHoursInAYear <= self.params.decalinVentLimit)



    def __init__(self,params:SystemParams):
        super().__init__()
        self.params = params

        self._AddSubModels()
        self._AddSets()
        self._AddVars()
        self._AddConstrs()

def Test1():
    from PyomoTools.IO import ModelToExcel, LoadModelSolutionFromExcel
    from PyomoTools import InfeasibilityReport
    from PyomoTools import FindLeastInfeasibleSolution
    from Graphs import YearlyExpenses, CashFlowDiagram, EquipmentCosts, UtilityBreakdown
    import matplotlib.pyplot as plt
    params = SystemParams()
    model = System(params)

    model.C = pyo.Constraint(expr=model.EXTRUDE.F_OUT["PE"] == 1200)

    # model.C2 = pyo.Constraint(expr=model.WATER_TREATMENT.X == 1)
    
    # model.COMB.Purchase.fix(0)

    # model.MaxProductObj = pyo.Objective(expr=model.F_FILM,sense=pyo.minimize)
    # model.MinUtilityObj = pyo.Objective(expr=sum(model.U_TOT[u] for u in params.utilities),sense=pyo.minimize)
    model.NPVObj = pyo.Objective(expr=model.ECON.NPV, sense=pyo.maximize)

    # LoadModelSolutionFromExcel(model,"oopModel.xlsx")

    solver = pyo.SolverFactory("scip")
    solver.solve(model,tee=True,options={'limits/gap': 1e-5})

    print("Yearly Cost of Utilities",pyo.value(sum(params.economicParams.utilityPrices[u] * model.ECON.NetUtilityDemand[u] for u in model.ECON.setU) * params.economicParams.operatingHoursInAYear / 1000))

    print("Yearly Cost of Materials",pyo.value(sum(params.economicParams.materialPrices[i] * model.ECON.PurchaseRate[i] for i in model.ECON.purchaseMaterials) * params.economicParams.operatingHoursInAYear / 1000))


    # solver = pyo.SolverFactory("ipopt",executable=r"C:\Users\nb5786-A\Documents\ipopt.exe")
    # solver.solve(model,tee=True)#,options={'max_iter': 700})

    # solver = pyo.SolverFactory("gams")
    # solver.solve(model,solver="baron",tee=True)

    ModelToExcel(model,"memo3_baseSolution.xlsx")

    # LoadModelSolutionFromExcel(model,"oopModel_debug.xlsx")
    report = InfeasibilityReport(model,onlyInfeasibilities=False)
    report.WriteFile("allConstraints_Memo3.txt")
    # assert len(report) == 0


    fig,((ax1,ax2),(ax3,ax4)) = plt.subplots(2,2)
    
    YearlyExpenses(params,model,ax1)
    CashFlowDiagram(params,model,ax2)
    EquipmentCosts(params,model,ax3)
    UtilityBreakdown(params,model,ax4)

    plt.show()



if __name__ == "__main__":
    Test1()