import pyomo.environ as pyo

from Block import BlockParams, Block

class FixedOutletRatioBlockParams(BlockParams):
    def __init__(self,inletStreams:list,outletStreams:list,streamCompositions:dict,utilities:list,outletRatios:dict,sizeFactor,EquipCostParams):
        super().__init__(inletStreams,outletStreams,streamCompositions,utilities)

        self.outletRatios = outletRatios

        self.sizeFactor = sizeFactor
        self.EquipCost_A,self.EquipCost_B,self.EquipCost_C = EquipCostParams

class FixedOutletRatioBlock(Block):
    def OutletSpecification_Func(self, _, i, s):
        return self.F[i,s] == self.params.outletRatios[i][s] * self.F_OUT[i]

    def __init__(self,params:FixedOutletRatioBlockParams,addBaseElements=True):
        super().__init__(params,addBaseElements)