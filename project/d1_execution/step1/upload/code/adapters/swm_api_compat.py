"""Step2 unified AP only: map legacy constructor spelling onto pinned native CEM.
No algorithm replacement or source edits. Original-mode environments keep pip0.0.6.
"""
def install():
 import sys,types
 from stable_worldmodel.planning.solver.cem import CEMSolver as NewCEM
 class LegacySpelling(NewCEM):
  def __init__(self,model,**kwargs):super().__init__(cost=model,**kwargs)
 package=types.ModuleType('stable_worldmodel.solver');package.__path__=[]
 cem=types.ModuleType('stable_worldmodel.solver.cem');cem.CEMSolver=LegacySpelling
 package.CEMSolver=LegacySpelling;package.cem=cem
 sys.modules['stable_worldmodel.solver']=package;sys.modules['stable_worldmodel.solver.cem']=cem
