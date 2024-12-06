import pyomo.environ as pyo

from .Block import BlockParams, Block

class SplitterParams(BlockParams):
    def __init__(self,numOutlets,materials:list,maxFlow:float=1e5):
        outletStreamNames = [f"OUT_{i+1}" for i in range(numOutlets)]
        super().__init__(
            inletStreams=["IN",],
            outletStreams=outletStreamNames,
            streamCompositions={s: materials for s in (outletStreamNames+["IN",])},
            utilities=[]
        )
        self.maxFlow = maxFlow
        self.sizeFactor = 1

class ContinuousSplitter(Block):
    def _AddSets(self,addBaseSets=False):
        if addBaseSets:
            super()._AddBaseSets()
        pass

    def _AddVars(self,addBaseVars=False):
        if addBaseVars:
            super()._AddBaseVars()

        self.S_frac = pyo.Var(self.outletStreams,domain=pyo.NonNegativeReals)

    def UtilityDemand_Func(self,_,u):
        pass

    def SizeDefinition_Func(self):
        return self.F_TOT
    
    def EquipmentCost_Func(self):
        return 0.0

    def OutletSpecification_Func(self, _, i, s):
        return self.F[i,s] == self.F_OUT[i] * self.S_frac[s]

    def _AddConstrs(self,addBaseConstrs=False):
        if addBaseConstrs:
            super()._AddBaseConstrs()

        def SplitFraction_Summation(self):
            return sum(self.S_frac[o] for o in self.outletStreams) == 1
        self.SplitFraction_Summation = pyo.Constraint(rule=SplitFraction_Summation)

    def __init__(self,params:SplitterParams):
        super().__init__(params,addBaseElements=False)

        self._AddSets(addBaseSets=True)
        self._AddVars(addBaseVars=True)
        self._AddConstrs(addBaseConstrs=True)

class SelectionSplitter(Block):
    def _AddSets(self,addBaseSets=False):
        if addBaseSets:
            super()._AddBaseSets()
        pass

    def _AddVars(self,addBaseVars=False):
        if addBaseVars:
            super()._AddBaseVars()

        self.S_frac = pyo.Var(self.outletStreams,domain=pyo.Binary)

    def UtilityDemand_Func(self,_,u):
        pass

    def OutletSpecification_Func(self, _, i, s):
        return self.F[i,s] <= self.params.maxFlow * self.S_frac[s]

    def _AddConstrs(self,addBaseConstrs=False):
        if addBaseConstrs:
            super()._AddBaseConstrs()

        def SplitFraction_Summation(self):
            return sum(self.S_frac[o] for o in self.outletStreams) == 1
        self.SplitFraction_Summation = pyo.Constraint(rule=SplitFraction_Summation)

        def OutletEnforcement(self,i):
            return sum(self.F[i,s] for s in self.outletStreams) == self.F_OUT[i]
        self.OutletEnforcement = pyo.Constraint(self.species,rule=OutletEnforcement)

    def __init__(self,params:SplitterParams):
        super().__init__(params,addBaseElements=False)

        self._AddSets(addBaseSets=True)
        self._AddVars(addBaseVars=True)
        self._AddConstrs(addBaseConstrs=True)