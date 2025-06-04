from itertools import product
from pulp import *

from asp_form import load_file
from asp_form import parse_inst_predicates
from asp_form import parse_aux_predicates
from asp_form import parse_initial_solution
from rcpsp import RCPSP

cfg = {}

if __name__ == "__main__":
    id = 'sample'
    ig_id = ''
    cfg["inst"] = f"{id}_{ig_id}_inst.lp"
    cfg["aux"] = f"{id}_{ig_id}_aux.lp"
    cfg["sol"] = f"{id}_{ig_id}_sol.lp"   # initial solution for verification
    _inst = load_file(cfg["inst"])
    _aux = load_file(cfg["aux"])
    _sol = load_file(cfg["sol"])

    ## parse total_dur/1 and start/2 from the initial solution 
    i_preds = parse_initial_solution(_sol)

    # compute the solution through MILP
    rcpsp = RCPSP()
    rcpsp.predicates = parse_inst_predicates(_inst)
    rcpsp.predicates = parse_aux_predicates(_aux, rcpsp.predicates)
    rcpsp.setup_instance()
    rcpsp.set_objective()
    rcpsp.set_constraints()
    rcpsp.solve()

    buff = rcpsp.convert_sol_to_asp_form()
    print(f"{buff}")

    objective = value(rcpsp.prob.objective)

    print(f"total_dur:{objective}, " + \
          f"initial total_dur:{i_preds['total_dur']}, " + \
          f"result:{objective == i_preds['total_dur']}, " + \
          f"status:{rcpsp.status}," + \
          f"status2:{rcpsp.prob.status}, " + \
          f"solution time:{rcpsp.prob.solutionTime}, " + \
          f"cpu time:{rcpsp.prob.solutionCpuTime}, " + \
          f"sol. status:{rcpsp.prob.sol_status}" # 1:optimal, 2:unoptimal sol.
    )
