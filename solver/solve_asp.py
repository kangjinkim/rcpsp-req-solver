import re
from clingo import Control
import os.path
import os
import errno
import sys
import time
import json

from asp_form import load_file
from asp_form import parse_initial_solution
from asp_form import parse_solution_in_asp

if __name__ == "__main__":
    # load gencfg file
    gencfg_file = f"../gencfg.json"
    if os.path.exists(gencfg_file):
        with open(gencfg_file) as f:
            gencfg = json.load(f)
    else:
        print(f"{gencfg_file} doesn't exist!")
        sys.exit()

    _basic = load_file(f"_asp_trim.lp")

    inst_dir = f"../instances"
    inst_id_dir = f"{inst_dir}/{gencfg['inst_id']}"

    sol_file = f"{inst_id_dir}_asp_sol.json"
    sol = {}
    sol["inst_id"] = f"{gencfg['inst_id']}"
    sol["task_max_count"] = f"{gencfg['task_max_count']}"
    sol["num_of_insts"] = f"{gencfg['num_of_insts']}"
    sol["inst_count_max"] = f"{gencfg['inst_count_max']}"
    sol["resource_quarter"] = f"{gencfg['resource_quarter']}"
    sol["resource_type_count"] = f"{gencfg['resource_type_count']}"
    sol["timeout"] = f"{gencfg['timeout']}"
    sol["igs"] = {}

    print(f"inst_id_dir:{inst_id_dir}")
    idth = 0
    for id in gencfg["igs"].keys():
        for ig_id_key, ig_id in gencfg["igs"][id].items():
            if ig_id_key != "ig_id":
                continue

            base_id = f"{id}_{ig_id}"
            #base = f"{inst_id_dir}/{id}_{ig_id}"
            base = f"{inst_id_dir}/{base_id}"
            inst_file = f"{base}_inst.lp"
            aux_file = f"{base}_aux.lp"

            _inst = load_file(inst_file)
            _aux = load_file(aux_file)

            ctl = Control()
            ctl.add("base", [], _inst + _aux + _basic)
            parts = []
            parts.append(("base", []))
            ctl.ground(parts)

            # parse the solution
            timeout_remained = gencfg["timeout"]
            tick = time.time()
            with ctl.solve(yield_=True, async_=True) as ret:
                while True:
                    tick2 = time.time()
                    ret.resume()
                    result = ret.wait(timeout_remained)
                    _time = time.time()
                    tock = _time - tick2
                    if result:
                        m = ret.model()
                        if m is None:
                            solve_result = str(ret.get())
                            if str(ret.get()) == "SAT":
                                tock2 = _time - tick
                                optimal = model['estart'][-1]
                                sol["igs"][base_id] = {}
                                sol["igs"][base_id]["total_dur"] = optimal
                                sol["igs"][base_id]["time"] = tock2

                                print(f"{base_id}: " + \
                                      f"total_dur:{optimal}, " + \
                                      f"tock:{tock2:06.3f} sec.")
                                break
                        else:
                            model = parse_solution_in_asp(f"{m}")
                        if timeout_remained - tock > 0:
                            timeout_remained -= tock
                        else:
                            sol["igs"][base_id] = {}
                            sol["igs"][base_id]["total_dur"] = -1
                            sol["igs"][base_id]["total_time"] = -1

                            print(f"{base_id}: " + \
                                  f"total_dur:-1, " + \
                                  f"tock:-1 sec.")
                            ret.cancel()
                            break
                    else:
                        sol["igs"][base_id] = {}
                        sol["igs"][base_id]["total_dur"] = -1
                        sol["igs"][base_id]["total_time"] = -1

                        print(f"{base_id}: " + \
                              f"total_dur:-1, " + \
                              f"tock:-1 sec.")
                        ret.cancel()
                        break
            idth += 1
            if idth % 10 == 0:
                print(f"==== {idth:03d} / " + \
                      f"{len(gencfg['igs'].keys()):03d} ====")
    with open(sol_file, 'w') as f:
        json.dump(sol, f, indent=4, sort_keys=True)
