from pulp import *
import os.path
import os
import errno
import sys
import time
import json

from asp_form import load_file
from asp_form import parse_inst_predicates
from asp_form import parse_aux_predicates
from rcpsp import RCPSP

if __name__ == "__main__":
    # load gencfg file
    gencfg_file = f"../gencfg.json"
    if os.path.exists(gencfg_file):
        with open(gencfg_file) as f:
            gencfg = json.load(f)
    else:
        print(f"{gencfg_file} doesn't exist!")
        sys.exit()

    inst_dir = f"../instances"
    inst_id_dir = f"{inst_dir}/{gencfg['inst_id']}"

    sol_file = f"{inst_id_dir}_milp_sol.json"
    sol = {}
    sol["inst_id"] = f"{gencfg['inst_id']}"
    sol["task_max_count"] = f"{gencfg['task_max_count']}"
    sol["num_of_insts"] = f"{gencfg['num_of_insts']}"
    sol["inst_count_max"] = f"{gencfg['inst_count_max']}"
    sol["resource_quarter"] = f"{gencfg['resource_quarter']}"
    sol["resource_type_count"] = f"{gencfg['resource_type_count']}"
    sol["igs"] = {}

    print(f"inst_id_dir:{inst_id_dir}")
    idth = 0
    for id in gencfg["igs"].keys():
        for ig_id_key, ig_id in gencfg["igs"][id].items():
            if ig_id_key != "ig_id":
                continue

            base = f"{inst_id_dir}/{id}_{ig_id}"
            inst_file = f"{base}_inst.lp"
            aux_file = f"{base}_aux.lp"

            _inst = load_file(inst_file)
            _aux = load_file(aux_file)

            rcpsp = RCPSP(timeout=gencfg["timeout"])
            rcpsp.predicates = parse_inst_predicates(_inst)
            rcpsp.predicates = parse_aux_predicates(_aux, rcpsp.predicates)
            rcpsp.setup_instance()
            rcpsp.set_objective()
            rcpsp.set_constraints()
            rcpsp.solve()

            objective = value(rcpsp.prob.objective)
            if rcpsp.prob.sol_status == 1:
                sol["igs"][f"{id}_{ig_id}"] = {}
                sol["igs"][f"{id}_{ig_id}"]["total_dur"] = objective
                sol["igs"][f"{id}_{ig_id}"]["time"] = rcpsp.prob.solutionTime

                print(f"{id}_{ig_id}: " + \
                      f"total_dur:{objective}, " + \
                      f"took:{rcpsp.prob.solutionTime:06.3f} sec.")
            else:
                sol["igs"][f"{id}_{ig_id}"] = {}
                sol["igs"][f"{id}_{ig_id}"]["total_dur"] = -1
                sol["igs"][f"{id}_{ig_id}"]["time"] = -1

                print(f"{id}_{ig_id}: " + \
                      f"total_dur:-1, " + \
                      f"took:-1 sec.")
            idth += 1
            if idth % 10 == 0:
                print(f"==== {idth:03d} / " + \
                      f"{len(gencfg['igs'].keys()):03d} ====")
    with open(sol_file, 'w') as f:
        json.dump(sol, f, indent=4, sort_keys=True)
