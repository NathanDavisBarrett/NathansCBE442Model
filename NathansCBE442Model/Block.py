from abc import ABC, abstractmethod

import pyomo.environ as pyo
import numpy as np

from PyomoTools import LoadIndexedSet

class BlockParams(ABC):
    def _DefineBaseSets(self,inletStreams:list,outletStreams:list,streamCompositions:dict,utilities:list):
        self.inletStreams = inletStreams
        self.outletStreams = outletStreams
        self.streamCompositions = streamCompositions
        self.utilities = utilities

    def _DefineSets(self):
        pass

    def _DefineBaseParams(self):
        self.Udomain = pyo.NonNegativeReals
        self.minS = None

    def _DefineParams(self):
        pass

    def __init__(self,inletStreams:list,outletStreams:list,streamCompositions:dict,utilities:list):
        self._DefineBaseSets(inletStreams,outletStreams,streamCompositions,utilities)
        self._DefineBaseParams()

        self._DefineSets()
        self._DefineParams()


class Block(pyo.ConcreteModel,ABC):
    def _AddBaseSets(self):
        sets = ["inletStreams","outletStreams","utilities"]
        for setName in sets:
            st = getattr(self.params,setName)
            if st in ["inletStreams","outletStreams"]:
                for s in st:
                    assert s in self.params.streamCompositions, f"Stream \"{s}\" is missing it's compositions"
            setattr(self,setName,st)

        LoadIndexedSet(self,"streamCompositions",self.params.streamCompositions)

        species = set([])
        for s in self.params.streamCompositions:
            species.update(set(self.params.streamCompositions[s]))
        self.species = pyo.Set(initialize=list(species))

    def _AddBaseVars(self):
        self.F = pyo.Var([(i,s) for s in self.streamCompositions for i in self.streamCompositions[s]],domain=pyo.NonNegativeReals)

        self.F_IN = pyo.Var(self.species,domain=pyo.NonNegativeReals)

        self.F_OUT = pyo.Var(self.species,domain=pyo.NonNegativeReals)

        self.F_TOT = pyo.Var(domain=pyo.NonNegativeReals)

        self.U = pyo.Var(self.utilities,domain=self.params.Udomain)

        self.S = pyo.Var(domain=pyo.NonNegativeReals)

        self.C = pyo.Var(domain=pyo.NonNegativeReals)

        self.X = pyo.Var(domain=pyo.Binary)

    def MaterialBalance_Func(self,_,i):
        return self.F_OUT[i] == self.F_IN[i]

    def OutletSpecification_Func(self,_,i,s):
        if len(self.params.outletStreams) == 1:
            return self.F[i,s] == self.F_OUT[i]
        else:
            raise Exception("No default function is available here. Please override this function in your child class.")
    
    def SizeDefinition_Func(self):
        return self.params.sizeFactor * self.F_TOT

    @abstractmethod
    def UtilityDemand_Func(self,_,u):
        pass

    def EquipmentCost_Func(self):
        return self.params.EquipCost_A * (self.S / self.params.EquipCost_B)**self.params.EquipCost_C
    
    def _AddBaseConstrs(self):
        def F_IN_Definition(self,i):
            return self.F_IN[i] == sum(self.F[i,s] for s in self.inletStreams if i in self.streamCompositions[s])
        self.F_IN_Definition = pyo.Constraint(self.F_IN.index_set(),rule=F_IN_Definition)

        def F_TOT_Definition(self):
            return self.F_TOT == sum(self.F_IN[i] for i in self.species)
        self.F_TOT_Definition = pyo.Constraint(rule=F_TOT_Definition)

        self.Material_Balance = pyo.Constraint(self.species,rule=self.MaterialBalance_Func)

        self.OutletSpecification = pyo.Constraint([(i,s) for s in self.outletStreams for i in self.streamCompositions[s]],rule=self.OutletSpecification_Func)

        self.UtilityDemand_Definition = pyo.Constraint(self.utilities,rule=self.UtilityDemand_Func)

        #TODO: Make sure to indicate that the size must be AT LEAST this amount.
        self.SizeDefinition = pyo.Constraint(expr= self.S >= self.SizeDefinition_Func())

        self.SizeLimit = pyo.Constraint(expr = self.S >= (self.params.minS if self.params.minS else 0))

        self.EquipmentCost_Definition = pyo.Constraint(expr=self.C == self.EquipmentCost_Func() * self.X)

        self.PurchaseEnforcement = pyo.Constraint(expr=self.F_TOT <= self.params.maxFlow * self.X)

    def __init__(self,params:BlockParams,addBaseElements=True):
        super().__init__()
        self.params = params
        if addBaseElements:
            self._AddBaseSets()
            self._AddBaseVars()
            self._AddBaseConstrs()