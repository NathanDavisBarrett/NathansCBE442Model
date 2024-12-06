from NathansCBE442Model import System, SystemParams
import pyomo.environ as pyo

params = SystemParams()

###############################################
#Examples of how to change the values you need:
#   Unless the default "params" are changed, the original parameters will be used.
###############################################
params.economicParams.materialPrices["FILM"] = 0.2 # $ / kg

params.economicParams.carbonTax = 0.026 #USD / kg

params.decalinVentLimit = 420 #kg / year



#The following line deactivates the constraint that the selling price is fixed.
# params.economicParams.materialPrices["PE"] = None 

###############################################
#The following line creates a model of the entire plastic recycling system using the parameters you provide.
#   Note that the constraint that the total outlet flow rate of PE should be 1200 kg/hr is NOT part of the baseline model.
#   As you'll see in a few lines, we have to add that constraint manually.
model = System(params)
###############################################


#Here's how to constrain the outlet PE flow rate.
model.OutletConstraint = pyo.Constraint(expr=model.EXTRUDE.F_OUT["PE"] == 1200) 

#This is the variable you'd use to include the selling price of PE in another constraint that you would define.
pePrice = model.ECON.SellPrice["PE"] 

#This is the variable you'd use to tell whether or not the water treatment block is purchased.
waterTreatmentDecision = model.WATER_TREATMENT.X 

model.NPVObj = pyo.Objective(expr=model.ECON.NPV, sense=pyo.maximize)

#As usual, you can solve the model like this:
solver = pyo.SolverFactory('scip')
solver.solve(model)#,tee=True)

print(f"Optimal NPV: {pyo.value(model.ECON.NPV)/1000} Million Dollars")

wwtPicked = pyo.value(waterTreatmentDecision) >= 0.5 #This is a binary variable. So if it's bigger than 0.5 then it must be 1
wwtMessage = "was" if wwtPicked else "was NOT"
print(f"The Water Treatment Block {wwtMessage} picked!")