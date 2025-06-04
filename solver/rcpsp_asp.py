import re
from clingo import Control
from clingo import Number
import time
from asp_form import load_file
from asp_form import parse_initial_solution
from asp_form import parse_solution_in_asp

cfg = {}
if __name__ == "__main__":
    id = 'sample'
    ig_id = ''
    cfg["inst"] = f"{id}_{ig_id}_inst.lp"
    cfg["aux"] = f"{id}_{ig_id}_aux.lp"
    cfg["sol"] = f"{id}_{ig_id}_sol.lp"   # initial solution for verification
    cfg["basic"] = "_asp_trim.lp"
    _inst = load_file(cfg["inst"])
    _aux = load_file(cfg["aux"])
    _sol = load_file(cfg["sol"])
    _basic = load_file(cfg["basic"])

    ## parse total_dur/1 and start/2 from the initial solution 
    i_preds = parse_initial_solution(_sol)

    # compute the solution through Clingo
    ctl = Control()
    ctl.add("base", [], _inst + _aux + _basic)
    parts = []
    parts.append(("base", [Number(cfg["rstar"])]))
    ctl.ground(parts)

    # parse the solution
    tick = time.time()
    with ctl.solve(yield_ = True) as ret:
        models = []
        for m in ret:
            model = parse_solution_in_asp(f"{m}")
            models.append(model)
    tock = time.time() - tick

    opt_model = models[-1]

    print(f"total_dur:{opt_model['estart'][-1]}, " + \
          f"initial total_dur:{i_preds['total_dur']}, " + \
          f"result:{opt_model['estart'][-1] == i_preds['total_dur']}")
