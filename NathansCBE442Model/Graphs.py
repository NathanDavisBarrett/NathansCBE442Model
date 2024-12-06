import matplotlib.pyplot as plt
import pyomo.environ as pyo
import numpy as np
from scipy.optimize import fsolve

from System import System, SystemParams

def YearlyExpenses(params:SystemParams,model:System,ax:plt.Axes):
    costNames = "Labor,Overhead,Admin,Dist,R&D,Rent,Insurance,Maint,Materials,Utilities".split(',')
    yearlyCostOfMaterials = sum(params.economicParams.materialPrices[i] * model.ECON.PurchaseRate[i] for i in model.ECON.purchaseMaterials) * params.economicParams.operatingHoursInAYear / 1000
    yearlyUtilityCosts = sum(params.economicParams.utilityPrices[u] * model.ECON.NetUtilityDemand[u] for u in model.ECON.setU) * params.economicParams.operatingHoursInAYear / 1000
    costs = [model.ECON.C_LABOR,model.ECON.C_OVERHEAD,model.ECON.C_ADMIN,model.ECON.C_DIST,model.ECON.C_RD,model.ECON.C_RENT,model.ECON.C_INS,model.ECON.C_MAINT,yearlyCostOfMaterials,yearlyUtilityCosts]
    for i in range(len(costs)):
        costs[i] = pyo.value(costs[i])

    for i in range(len(costNames)):
        print(f"{costNames[i]}: {costs[i]}")
    ax.pie(costs,labels=costNames)
    ax.set_title("Yearly Expenses")

def EquipmentCosts(params:SystemParams,model:System,ax:plt.Axes,includeLoadCosts=True):
    blocks = list(model.ECON.setB)
    ECs = [pyo.value(model.ECON.BlockEquipmentCost[b]) for b in blocks]

    if includeLoadCosts:
        for i in model.ECON.loadMaterials:
            blocks.append(f"LOAD {i}")
            ECs.append(pyo.value(model.ECON.LoadQuantity[i]) * params.economicParams.materialPrices[i]/1000)

    ECs = np.array(ECs)
    ECs[np.abs(ECs)<1e-5] = 0.0


    ax.pie(ECs,labels=blocks)
    ax.set_title("Block Equipment Costs")


def CashFlowDiagram(params:SystemParams,model:System,ax:plt.Axes):
    CFs = np.array([pyo.value(model.ECON.CF[t]) for t in model.ECON.setT])
    color = "tab:blue"
    ax.bar(model.ECON.setT,CFs/1000,color=color)
    ax.set_ylabel("Un-DiscountedCashFlow (M$)",color=color)
    ax.set_xlabel("time (yr)")
    ax.tick_params(axis='y', labelcolor=color)


    def f(t):
        return 1 / (1 + params.economicParams.interestRate)**(t)
    discountedCFs = [f(model.ECON.setT[i+1]) * CFs[i] for i in range(len(CFs))]
    NPVs = [discountedCFs[0]]
    for i in range(1,len(CFs)):
        NPVs.append(NPVs[-1] + discountedCFs[i])
    NPVs = np.array(NPVs)

    color = "black"
    twinAx = ax#.twinx()
    twinAx.plot(model.ECON.setT,NPVs/1000,color=color)
    twinAx.set_ylabel("NPV (M$)",color=color)
    twinAx.tick_params(axis='y', labelcolor=color)

    if not hasattr(model.ECON,"IRR"):
        def solveIRR(irr):
            return sum(CFs[t] / (1 + irr)**t for t in range(len(CFs)))
        irr,_,err,msg = fsolve(solveIRR,0.11,full_output=True)
        if err != 1:
            print(f"IRR Calculation did not converge: {msg}")
            model.ECON.IRR = np.infty
        else:
            model.ECON.IRR = irr[0]

        
    ax.set_title(f"Cash Flow Diagram (IRR = {pyo.value(model.ECON.IRR)*100:.3f}%) (ROI = {pyo.value(model.ECON.ROI)*100:.3f}%)")

def UtilityBreakdown(params:SystemParams,model:System,ax:plt.Axes):
    utilities = [u for u in model.ECON.setU]
    utilityColors = ["tab:blue","tab:orange","tab:green"]

    blocks = list(params.componentParams.keys())
    blockNames = [(b if b != "WATER_TREATMENT" else "WT") for b in blocks]

    bottoms = np.zeros(len(blocks))
    tops = np.zeros(len(blocks))
    for j,u in enumerate(utilities):
        ax.fill_between([0,],[0,],[0,],color=utilityColors[j],label=u)
        addition = np.zeros(len(blocks))
        for i,b in enumerate(blocks):
            blockUtils = params.componentParams[b].utilities
            if u in blockUtils:
                subModel = getattr(model,b)
                addition[i] += pyo.value(subModel.U[u])
        
        positive = np.copy(addition)
        positive[positive<0] = 0.0

        negative = np.copy(addition)
        negative[negative>0] = 0.0

        ax.bar(blockNames, positive,bottom=bottoms,color=utilityColors[j])
        bottoms += positive
        tops += negative
        ax.bar(blockNames, -negative ,bottom=tops,color=utilityColors[j])

    maxY = np.max(bottoms + positive)
    minY = np.min(tops)

    ax.set_ylim(minY,maxY)
    ax.set_title("Utility Breakdown")
    ax.set_ylabel("Demand (kW)")
    ax.legend()
    plt.xticks(rotation=90)

