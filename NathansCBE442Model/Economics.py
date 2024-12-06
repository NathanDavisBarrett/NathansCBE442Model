import pyomo.environ as pyo

from PyomoTools import LoadIndexedSet

class EconomicParams:
    def __init__(self,blockNames,utilities):
        self.installFactor = 0.05

        #Assume no materials or pressure factor (since everything is at or near ATM and no excessively corrosive materials are bing used.)

        self.manufacturingContingency = 0.25 # $ CONT / ($ IC)
        self.nonManufacturingCostFactor = 0.40 # $ NONMANU / ($ MANU)
        self.maintenanceFactor = 0.03 # $ MAINT / yr / ($ CAPEX)
        self.insuranceFactor = 0.007 # $ INS / yr / ($ CAPEX)
        self.rentFactor = 0.01 # $ RENT / yr / ($ CAPEX)
        self.laborFactor = 0.02 # $ LABOR / yr / $ MANU
        self.overheadFactor = 0.9 # $ OVERHEAD / $ LABOR
        self.adminFactor = 0.25 # $ ADMIN / $ OVERHEAD
        self.distrFactor = 0.1 # $ DIST / yr / ($ TOTAL / yr)
        self.RDFactor = 0.07 # $ RD / yr / ($ TOTAL / yr)

        self.operatingHoursInAYear = 7890#8760

        self.salvageFraction = 0.2

        self.depreciationTimespan = 6 #years
        self.investmentLifetime = 20 #years

        self.setT = list(range(self.investmentLifetime+2))

        self.taxRate = 0.35

        self.interestRate = 0.11


        self.materialPrices = { # $ / kg
            "FILM": 0.325,
            "DECALIN": 0.62,
            "GVL": 2.33,
            "CAT": 540.75,
            "H2": 5,
            "PE": 0.87, #Final Product
            "CH4": 0.02
        }

        #Currently Range from ($0.015 / kg to $0.035 / kg)
        self.carbonTax = 0.025 #USD / kg

        self.utilityPrices = { #k$ / kWh
            "HP": 0.0100,
            "ELEC": 0.0775,
            "COOL": 0.00076
        }

        self.blockNames = blockNames

        assert set(self.utilityPrices.keys()) == set(utilities)

class Economics(pyo.ConcreteModel):
    def __init__(self,params:EconomicParams):
        super().__init__()
        self.params = params
        self._AddSets()
        self._AddVars()
        self._AddConstrs()

    def _AddSets(self):
        self.setB = pyo.Set(initialize=self.params.blockNames)
        self.setU = pyo.Set(initialize=list(self.params.utilityPrices.keys()))
        self.purchaseMaterials = pyo.Set(initialize=["FILM","DECALIN","CH4"])
        self.sellMaterials = pyo.Set(initialize=["PE"])
        self.loadMaterials = pyo.Set(initialize=["CAT","GVL"])
        self.setT = pyo.Set(initialize=self.params.setT)

    def _AddVars(self):
        # THESE VARIABLES NEED TO BE EQUATED TO THEIR COUNTERPARTS IN OTHER SUB-MODELS!
        self.BlockEquipmentCost = pyo.Var(self.setB,domain=pyo.Reals)
        self.NetUtilityDemand = pyo.Var(self.setU,domain=pyo.Reals)

        self.PurchaseRate = pyo.Var(self.purchaseMaterials,domain=pyo.Reals)
        self.SellRate = pyo.Var(self.sellMaterials,domain=pyo.Reals)
        self.LoadQuantity = pyo.Var(self.loadMaterials,domain=pyo.Reals)

        self.CarbonRate = pyo.Var(domain=pyo.Reals)

        # THESE VARIABLES ARE UNIQUE TO THIS SUB-MODEL.
        self.SellPrice = pyo.Var(self.sellMaterials,domain=pyo.NonNegativeReals)

        # Total Equipment Cost
        self.C_EC = pyo.Var(domain=pyo.Reals)

        # Installed Capital Cost
        self.C_IC = pyo.Var(domain=pyo.Reals)

        # Manufacturing Cost
        self.C_MANU = pyo.Var(domain=pyo.Reals)

        # Non-Manufacturing Cost
        self.C_NONMANU = pyo.Var(domain=pyo.Reals)

        # CAPEX
        self.C_CAPEX = pyo.Var(domain=pyo.Reals)

        # Maintenance Cost
        self.C_MAINT = pyo.Var(domain=pyo.Reals)

        # Insurance Cost
        self.C_INS = pyo.Var(domain=pyo.Reals)

        #Rent Cost
        self.C_RENT = pyo.Var(domain=pyo.Reals)

        # Labor Cost
        self.C_LABOR = pyo.Var(domain=pyo.Reals)

        # Overhead Cost
        self.C_OVERHEAD = pyo.Var(domain=pyo.Reals)

        # Admin Cost
        self.C_ADMIN = pyo.Var(domain=pyo.Reals)

        # Distr Cost
        self.C_DIST = pyo.Var(domain=pyo.Reals)

        # R&D Cost
        self.C_RD = pyo.Var(domain=pyo.Reals)

        # Total Yearly Expenses
        self.C_YR = pyo.Var(domain=pyo.Reals)

        # Total Yearly Revenue
        self.R = pyo.Var(domain=pyo.Reals)

        # Depreciation / year
        self.D = pyo.Var(domain=pyo.Reals)

        # Taxes to be paid in each year
        self.C_TAX = pyo.Var(self.setT,domain=pyo.Reals)

        # Cash Flow
        self.CF = pyo.Var(self.setT,domain=pyo.Reals)

        # NPV
        self.NPV = pyo.Var(domain=pyo.Reals)

        # Internal Rate of Return
        # self.IRR = pyo.Var(domain=pyo.Reals)

        #ROI
        self.ROI = pyo.Var(domain=pyo.Reals)

        

    def _AddConstrs(self):
        def SellPriceEnforcement(_,i):
            if self.params.materialPrices[i] is not None:
                return self.SellPrice[i] == self.params.materialPrices[i]
            else:
                return pyo.Constraint.Feasible
        self.SellPriceEnforcement = pyo.Constraint(self.sellMaterials,rule=SellPriceEnforcement)
            
        self.C_EC_Definition = pyo.Constraint(expr=self.C_EC == sum(self.BlockEquipmentCost[b] for b in self.setB) + sum(self.LoadQuantity[i] * self.params.materialPrices[i] for i in self.loadMaterials)/1000)

        self.C_IC_Definition = pyo.Constraint(expr=self.C_IC == (1+self.params.installFactor) * self.C_EC)

        self.C_MANU_Definition = pyo.Constraint(expr=self.C_MANU == (1+self.params.manufacturingContingency) * self.C_IC)

        self.C_NONMANU_Definition = pyo.Constraint(expr=self.C_NONMANU == self.params.nonManufacturingCostFactor * self.C_MANU)

        self.C_CAPEX_Definition = pyo.Constraint(expr=self.C_CAPEX == self.C_MANU + self.C_NONMANU)

        self.C_MAINT_Definition = pyo.Constraint(expr=self.C_MAINT == self.params.maintenanceFactor * self.C_CAPEX)

        self.C_INS_Definition = pyo.Constraint(expr=self.C_INS == self.params.insuranceFactor * self.C_CAPEX)

        self.C_RENT_Definition = pyo.Constraint(expr=self.C_RENT == self.params.rentFactor * self.C_CAPEX)

        self.C_LABOR_Definition = pyo.Constraint(expr=self.C_LABOR == self.params.laborFactor * self.C_MANU)

        self.C_OVERHEAD_Definition = pyo.Constraint(expr=self.C_OVERHEAD == self.params.overheadFactor * self.C_LABOR)

        self.C_ADMIN_Definition = pyo.Constraint(expr=self.C_ADMIN == self.params.adminFactor * self.C_OVERHEAD)

        self.C_DIST_Definition = pyo.Constraint(expr=self.C_DIST == self.params.distrFactor * self.C_YR)

        self.C_RD_Definition = pyo.Constraint(expr=self.C_RD == self.params.RDFactor * self.C_YR)

        self.yearlyCostOfMaterials = pyo.Expression(expr=sum(self.params.materialPrices[i] * self.PurchaseRate[i] for i in self.purchaseMaterials) * self.params.operatingHoursInAYear / 1000) #Divide by 1000 to go $ -> k$

        self.yearlyUtilityCosts = pyo.Expression(expr=sum(self.params.utilityPrices[u] * self.NetUtilityDemand[u] for u in self.setU) * self.params.operatingHoursInAYear / 1000) #Divide by 1000 to go $ -> k$

        self.C_YR_Definition = pyo.Constraint(expr=self.C_YR == self.C_LABOR + self.C_OVERHEAD + self.C_ADMIN + self.C_DIST + self.C_RD + self.C_RENT + self.C_INS + self.C_MAINT + self.yearlyCostOfMaterials + self.yearlyUtilityCosts)

        self.R_Definition = pyo.Constraint(expr=self.R == sum(self.SellRate[i] * self.SellPrice[i] for i in self.sellMaterials) * self.params.operatingHoursInAYear / 1000) #Divide by 1000 to go $ -> k$

        self.D_Definition = pyo.Constraint(expr=self.D == (1-self.params.salvageFraction) * self.C_CAPEX / self.params.depreciationTimespan)

        def Taxes_Definition(_,t):
            taxableIncome = 0
            if t >= 1:
                if t <= self.params.investmentLifetime:
                    taxableIncome += self.R
                if t <= self.params.depreciationTimespan:
                    taxableIncome -= self.D

                carbonTax = self.params.carbonTax * self.CarbonRate * self.params.operatingHoursInAYear / 1000
            else:
                carbonTax = 0

            return self.C_TAX[t] == self.params.taxRate * taxableIncome + carbonTax
        self.Taxes_Definition = pyo.Constraint(self.setT,rule=Taxes_Definition)

        def CashFlow_Definition(_,t):
            cf = -self.C_TAX[t]
            if t == 0:
                cf -= self.C_CAPEX
            elif t <= self.params.investmentLifetime:
                cf += self.R - self.C_YR
            elif t == self.params.investmentLifetime + 1:
                cf += self.params.salvageFraction * self.C_CAPEX
            return self.CF[t] == cf
        self.CashFlow_Definition = pyo.Constraint(self.setT,rule=CashFlow_Definition)

        def f(t):
            return 1 / (1 + self.params.interestRate)**(t)
        self.NPV_Definition = pyo.Constraint(expr= self.NPV == sum(f(t) * self.CF[t] for t in self.setT))
        
        # def IRR_Definition(_):
        #     return 0 == sum(self.CF[t] / (1 + self.IRR)**t for t in self.setT)
        # self.IRR_Definition = pyo.Constraint(rule=IRR_Definition)

        self.ROI_Definition = pyo.Constraint(expr = self.ROI * self.C_CAPEX == sum(self.CF[t] for t in self.setT))