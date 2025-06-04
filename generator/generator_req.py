from instance import *
import instance as instance_core
from adding_reqs import parse_pert_chart
from adding_reqs import factor_decision_vectors
from adding_reqs import req_list
from adding_reqs import to_req_uid
from adding_reqs import to_req_idx
from adding_reqs import factor_write_vectors

from mass import *
from assign_req_trees import generate_proper_subprojects
from assign_req_trees import get_track_count
from assign_req_trees import get_req_tree_count
from assign_req_trees import calculate_rstar_bound
from assign_req_trees import generate_proper_req_instances
from clingo import Control
import re
import os.path
import os
import errno
import sys
import time
import json

sys.path.append('../solver')
from asp_form import load_file
from asp_form import write_file 
from asp_form import parse_inst_predicates
from asp_form import parse_solution_in_asp
from asp_form import create_extra_stuff
from asp_form import create_aux_predicates
from preprocess import calculate_eis, calculate_lis

def create_dir(dir_name):
    if os.path.exists(dir_name):
        pass
        #print(f"{dir_name} exists!")
    else:
        # then create the dir
        # we have to create inst_list.py file under the dir
        #print(f"{dir_name} doesn't exist!")
        try:
            os.mkdir(dir_name)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                print(f"Failed to create {dir_name}.")
            raise OSError
        #print(f"{dir_name} is just created!")

def get_default_gencfg():
    gencfg = instance_core.cfg
    gencfg['duration_max'] = 5
    gencfg['task_max_count'] = 20
    gencfg['resource_type_count'] = 4
    gencfg['resource_quarter'] = 2
    gencfg['amount_quarter'] = 5
    gencfg['low_bound'] = 2
    gencfg['high_bound'] = 5
    gencfg['rstar_low'], gencfg['rstar_high'] = calculate_rstar_bound(gencfg)
    gencfg['owners'] = ["req1", "req2", "req3"]
    gencfg['req1'] = []
    gencfg['req2'] = []
    gencfg['req3'] = []
    gencfg['rstar'] = 1
    gencfg['timeout'] = 600 # ten minutes

    gencfg['inst_count_max'] = 3
    gencfg['igs'] = {}
    gencfg['forests'] = {}
    gencfg['remained'] = []

    gencfg['cmargin'] = 0
    gencfg['camount'] = 0

    #gencfg['id'] = id_generator()
    gencfg['ids'] = []
    gencfg['num_of_insts'] = 5
    gencfg['inst_id'] = "000000"
    gencfg['inst_dir'] = "instances"

    return gencfg

def dump_file(buff, json_file):
    with open(json_file, 'w') as f:
        json.dump(buff, f, indent=4, sort_keys=True)

def convert_forest_to_asp_form2(forest, gencfg, id):
    buf = f"%%%%% ig_id: {forest.ig_id}, "
    buf += f"Total {len(forest.tdict)} tasks %%%%%\n\n"

    for task in forest.tdict.values():
        buf += f"task({task.tid}).\n"
    buf += f"\n"

    for task in forest.tdict.values():
        buf += f"dur({task.tid}, {task.dur}).\n"
    buf += f"\n"

    for task in forest.tdict.values():
        for pred in task.pred:
            buf += f"psrel({pred.tid}, {task.tid}).\n"
        #for succ in task.pred:
        #    buf += f"psrel({task.tid}, {succ.tid}).\n"
    buf += f"\n"

    resource_limits = {}
    for task in forest.tdict.values():
        for res, req in task.resources.items():
            buf += f"rsreq({task.tid}, {res}, {req}).\n"
            if res not in resource_limits:
                resource_limits[res] = req
            else:
                resource_limits[res] = max(resource_limits[res], req)
    buf += f"\n"

    for res, limit in resource_limits.items():
        buf += f"limit({res}, {limit}).\n"
    buf += f"\n"

    buf += f"ig_id(\"{id}_{forest.ig_id}\").\n"
    buf += f"\n"

    #ig_id = f"{id}_{forest.ig_id}"

    for tidx in forest.trees.keys():
        tree_idx = f"{id}_{forest.ig_id}_{tidx}"
        #tree_idx = f"{gencfg['id']}_{forest.ig_id}_{tidx}"
        #buf += f"tree_id({gencfg['id']}_{forest.ig_id}_{tidx}).\n"
        buf += f"tree_id(\"{tree_idx}\").\n"
    buf += f"\n"

    #req_trees = {1: 'user1', 2: 'user2', 3: 'user3'}
    ##print(f"req_trees:{req_trees}")
    #for user_id, user_cfg_key in req_trees.items():
    #    #print(f"user_id:{user_id}, user_cfg_key:{user_cfg_key}," + 
    #    #      f"gencfg['igs'][id][]:{gencfg['igs'][id][user_cfg_key]}")
    #    #for ig_id, tree in gencfg[user_cfg_key]:
    #    #for ig_id, tidx in gencfg[user_cfg_key]:
    #    for ig_id, tidx in gencfg['igs'][id][user_cfg_key]:
    #        if ig_id != forest.ig_id:
    #            continue
    #        tree_idx = f"{id}_{forest.ig_id}_{tidx}"
    #        #tree_idx = f"{gencfg['id']}_{forest.ig_id}_{tidx}"
    #        buf += f"owner({user_id}, \"{tree_idx}\").\n"
    #        #for tid in tree:
    #        #    tree_idx = f"{gencfg['id']}_{forest.ig_id}_{tidx}"
    #        #    #buf += f"owner({user_id}, {tid}).\n"
    #        #    #buf += f"owner({user_id}, {tidx}).\n"
    #        #    buf += f"owner({user_id}, {tree_idx}).\n"
    for user_cfg_key in gencfg["owners"]:
        for ig_id, tidx in gencfg['igs'][id][user_cfg_key]:
            if ig_id != forest.ig_id:
                continue
            tree_idx = f"{id}_{forest.ig_id}_{tidx}"
            buf += f"owner(\"{user_cfg_key}\", \"{tree_idx}\").\n"
    buf += f"\n"

    for tidx, tree in forest.trees.items():
        #tree_idx = f"{gencfg['id']}_{forest.ig_id}_{tidx}"
        tree_idx = f"{id}_{forest.ig_id}_{tidx}"
        for t in tree:
            buf += f"tree(\"{tree_idx}\", {t.tid}).\n"
    buf += f"\n"

    return buf

def convert_opt_model_to_asp_form(opt_model):
    buf = f"\n%%%%% initial solution %%%%%\n"
    for start_pred in opt_model['start']:
        buf += f"{start_pred}.\n"

    buf += f"\n%%%%% initial project duration %%%%%\n"
    buf += f"total_dur({opt_model['estart'][-1]}).\n"
    #buf += f"total_dur({opt_model['estart'][-1] - 1}).\n"

    return buf

def solve_initial_instance(forest, gencfg, inst_cfg, ig_id, id, _basic):
    inst_dir = "../" + gencfg["inst_dir"]
    new_inst_id = gencfg['inst_id']
    new_inst_id_dir = inst_dir + "/" + f"{new_inst_id}"
    inst_cfg_idx = int(ig_id[2:])
    icfg = {}
    _inst = convert_forest_to_asp_form2(forest, gencfg, id)
    parse_pert_chart(_inst, icfg)

    # the old ones are in the integer format (only having the tidx),
    # and the new ones are in the string format, including id, ig_id and tidx.
    old_tidx_list = list(forest.trees.keys())

    for old_tidx in old_tidx_list:  # the tidx keys in integer format
        new_tidx = f"{id}_{forest.ig_id}_{old_tidx}"
        assert new_tidx in icfg["trees"]    # through parse_pert_chart() above
        forest.trees[new_tidx] = forest.trees[old_tidx]
        del forest.trees[old_tidx]

    # create file names for base, inst, sol, aux and reqs
    base = f"{new_inst_id_dir}/{id}_{forest.ig_id}"
    inst_file = f"{base}_inst.lp"
    sol_file = f"{base}_sol.lp"
    aux_file = f"{base}_aux.lp"
    reqs_file = f"{base}_reqs.lp"
    icfg["base"] = f"{new_inst_id_dir}/{id}_{forest.ig_id}"
    icfg["inst_file"] = f"{base}_inst.lp"
    icfg["reqs_file"] = reqs_file

    # load the instance (we already loaded it from the above _inst)

    preds = {key: value for key, value in icfg.items()} # from pert_chart

    # create extra stuff and aux_predicates
    preds = create_extra_stuff(preds)
    preds["eis"] = calculate_eis(preds["psrels"], preds["durs"])
    preds["lis"] = calculate_lis(preds["psrels"], preds["durs"])
    _aux = create_aux_predicates(preds)

    # compute the solution (initial) for the forest
    ctl = Control()
    ctl.add("base", [], _inst + _aux + _basic)
    parts = []
    parts.append(("base", []))
    ctl.ground(parts)

    # parse solution (initial)
    with ctl.solve(yield_ = True) as ret:
        opt_model = parse_solution_in_asp(f"{list(ret)[-1]}")

    print(f"success!, base:{icfg['base']}, " + \
          f"total_dur:{opt_model['estart'][-1]}")
    # convert it in asp form
    _sol = convert_opt_model_to_asp_form(opt_model)

    # add predicates for the solution
    icfg["start"] = {t.tid: t.tstep for t in opt_model["start"]}
    icfg["total_dur"] = int(opt_model['estart'][-1])
    icfg["eis"] = preds["eis"]
    icfg["forest"] = forest

    # write instance files
    write_file(_inst, inst_file)
    write_file(_aux, aux_file)
    write_file(_sol, sol_file)

    # keep these predicates to inst_cfg dict
    inst_cfg[inst_cfg_idx] = icfg

if __name__ == "__main__":
    # dir exists?
    inst_dir = "../instances"
    create_dir(inst_dir)

    inst_list_file = f"{inst_dir}/inst_list.json"
    if os.path.exists(inst_list_file):
        with open(inst_list_file) as f:
            inst_list = json.load(f)
    else:
        inst_list = dict()  # key: inst_id, value: (# of instances, # of tasks)

    while True:
        new_inst_id = id_generator(
            size=8, chars=string.ascii_lowercase + string.digits
        )
        if new_inst_id not in inst_list:
            break

    new_inst_id_dir = inst_dir + "/" + f"{new_inst_id}"
    create_dir(new_inst_id_dir)
    inst_list[new_inst_id] = (0, 0)

    # generate a config file, gencfg.json, for generating instances of ASP.
    gencfg_file = "../gencfg.json"
    if os.path.exists(gencfg_file):
        with open(gencfg_file) as f:
            _gencfg = json.load(f)
        gencfg = instance_core.cfg
        for key, value in _gencfg.items():
            gencfg[key] = value
        gencfg['ids'] = []
    else:
        gencfg = get_default_gencfg()

    gencfg['inst_id'] = new_inst_id
    inst_list[new_inst_id] = (gencfg['num_of_insts'], gencfg['task_max_count'])

    # generate ids for num_of_insts
    for _ in range(gencfg['num_of_insts']):
        while True:
            new_id = id_generator()
            if new_id not in gencfg['ids']:
                gencfg['ids'].append(new_id)
                break

    generate_proper_req_instances(gencfg)

    #for id in gencfg['ids']:
    #    for ig_id, forest in gencfg['igs'][id]['forests'].items():
    #        print(f"=> id:{id}, ig_id:{ig_id}, forest.ig_id:{forest.ig_id}")
    #    print(f"==== ====\n")

    # generate each instance
    _basic_asp_form = "../solver/_asp_trim.lp"
    with open(_basic_asp_form, "r") as f:
        _basic = f.read()

    #print(f"gencfg['ids']:{gencfg['ids']}")
    #print(f"gencfg['igs']:{gencfg['igs']}")

    for idth, id in enumerate(gencfg['ids']):
        inst_cfg = {}
        for ig_id, forest in gencfg['igs'][id]['forests'].items():
            solve_initial_instance(forest, gencfg, inst_cfg, ig_id, id, _basic)

        # decide factors for req1, req2, and req3
        cfg = {req_idx: {} for req_idx in req_list}
        #print(f"inst_cfg.keys:{inst_cfg.keys()}, cfg.keys:{cfg.keys()}")
        #for req_uid, df_fc in enumerate(factor_decision_vectors, start=1):
        for req_uid, df_fc in enumerate(factor_decision_vectors):
            df_fc(cfg, inst_cfg, gencfg, req_uid, to_req_idx[req_uid])

        #for req_uid, wf_fc in enumerate(factor_write_vectors, start=1):
        for req_uid, wf_fc in enumerate(factor_write_vectors):
            wf_fc(cfg, inst_cfg, req_uid, to_req_idx[req_uid])

        for icfg in inst_cfg.values():
            write_file(icfg["buff"], icfg["reqs_file"])

    # write the gencfg to the sub-folder
    gencfg_file_new = new_inst_id_dir + "/" + f"{gencfg_file[2:]}"

    _gencfg = {}
    _gencfg = gencfg.copy()
    for id in _gencfg['igs'].keys():
        ig_ids = [ig_id for ig_id, ig in _gencfg['igs'][id]['igs']]
        _gencfg['igs'][id]['ig_id'] = ig_ids

        del _gencfg['igs'][id]['igs']
        del _gencfg['igs'][id]['forests']
        for user_cfg_key in gencfg['owners']:
            del _gencfg['igs'][id][user_cfg_key]
        #del _gencfg['igs'][id]['user1']
        #del _gencfg['igs'][id]['user2']
        #del _gencfg['igs'][id]['user3']
        del _gencfg['igs'][id]['remained']

    dump_file(_gencfg, gencfg_file_new)

    # add the gencfg to the current folder
    dump_file(_gencfg, gencfg_file)
    dump_file(inst_list, inst_list_file)
