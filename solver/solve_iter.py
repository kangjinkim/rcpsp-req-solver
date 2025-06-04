import re
from clingo import Control
from clingo import Number
import os.path
import os
import errno
import sys
import time
import json

from predicate import Start
from asp_form import load_file
from asp_form import parse_initial_solution
from asp_form import parse_aux_predicates
from asp_form import parse_solution_in_asp
from asp_form import parse_inst_predicates
from asp_form import parse_inst_predicates2
from asp_form import parse_solution_for_req1_in_asp
from asp_form import parse_solution_for_req2_in_asp
from asp_form import parse_solution_for_req3_in_asp
from asp_form import parse_instance_for_req1
from asp_form import parse_instance_for_req2
from asp_form import parse_instance_for_req3

def load_instance_with_reqs(ccfg, id, ig_id):
    base_id = f"{id}_{ig_id}"
    base = f"{ccfg['inst_id_dir']}/{base_id}"
    _inst = load_file(f"{base}_inst.lp")
    _aux = load_file(f"{base}_aux.lp")
    _req = load_file(f"{base}_reqs.lp")
    return (_inst, _aux, _req)
    _base_code = _inst + _aux + _req + _basic2 + _reqxx

def compute_delay_range(ccfg):
    txid_to_tr = {txid: trid for trid, (txid, _) in ccfg["tree_exts"].items()}
    d_range = {
        txid_to_tr[txid]: (0, ccfg["max_time"] - tree_dur)
            for txid, tree_dur in ccfg["min_tree_dur"].items()
                if txid in txid_to_tr
    }
    return d_range

def parse_instance_and_reqs(ccfg, _inst, _req):
    preds = {}
    preds["inst_id"] = ccfg["inst_id"]
    preds["inst_tree_exts"] = ccfg["inst_tree_exts"]

    preds |= parse_inst_predicates(_inst)
    preds |= parse_inst_predicates2(_inst)

    parse_instance_for_req1(preds, _req)
    parse_instance_for_req2(preds, _req)
    parse_instance_for_req3(preds, _req)
    return preds

def pre_process_for_reqs(gencfg, ccfg, preds):
    # get track_id and tidx of each tree regarding req2
    preds['req2_tidx_cvalues'] = {}

    # compute cmargin and camount of that tidx
    for tr_id, tidx in preds['req2_tr_tx'].items():
        preds['req2_tidx_cvalues'][tidx] = {}
        tidx_camount = 0
        tidx_cmargin = 0
        for task in preds['tree'][tidx]:
            for rtype, ramount in preds['rsreqs'][task].items():
                if rtype == gencfg['rstar']:
                    tidx_camount += ramount
                    tidx_cmargin += preds['limits'][rtype] - ramount
        preds['req2_tidx_cvalues'][tidx]['camount'] = tidx_camount
        preds['req2_tidx_cvalues'][tidx]['cmargin'] = tidx_cmargin

    # prepare for req3
    inst_id = ccfg["inst_id"]
    ccfg["actual_delay"][inst_id] = {}

def get_additional_code(preds, _aux, delay_margin):
    # add predicates for req3
    parse_aux_predicates(_aux, preds)
    d_range = compute_delay_range(preds)

    _additional_code = ""
    for trid, (d_lb, d_hb) in d_range.items():
        _additional_code += f"delay_range({trid}, {d_lb}..{d_hb}).\n"

    if len(delay_margin.keys()) == 0:
        for trid in d_range.keys():
            delay_margin[trid] = 0

    for trid, d_margin in delay_margin.items():
        _additional_code += f"delay_margin({trid}, {d_margin}).\n"
    return _additional_code

def create_control(gencfg, _base_code, _additional_code):
    ctl = Control()
    ctl.add("base", ["rstar"], _base_code + _additional_code)
    parts = []
    parts.append(("base", [Number(gencfg["rstar"])]))
    ctl.ground(parts)
    return ctl

def parse_solution_for_reqs(m):
    model = parse_solution_for_req1_in_asp(f"{m}")
    model |= parse_solution_for_req2_in_asp(f"{m}")
    model |= parse_solution_for_req3_in_asp(f"{m}")
    return model

def update_solution(_sol, ccfg, tock2, opt_model):
    if opt_model == None:
        _sol["total_dur"] = -1
        _sol["time"] = -1
        _sol["excess"] = []
        _sol["opt_model"] = None
        ccfg["curr_duration_sum"] = float("Inf")
    else:
        _sol["total_dur"] = opt_model['estart'][-1]
        _sol["time"] = tock2
        _sol["excess"] = opt_model['excess_in_total']
        _sol["opt_model"] = opt_model
        ccfg["curr_duration_sum" ] += _sol["total_dur"]

def process_for_req3(idcfg, _ig_id, _sol, ccfg, preds, delay_margin):
    # merge this idcfg[_ig_id] with key-value pairs in _sol after
    idcfg[_ig_id] |= _sol

    # post-process of req3 for plain RCPSP solver
    actual_tree_duration = {}
    actual_delay = {}
    if _sol["opt_model"] != None:
        for tr_id, tidx in preds['req3_tr_tx'].items():
            tree_start = min(
                task.tstep
                    for task in _sol['opt_model']['start']
                        if task.tid in preds['tree'][tidx]
            )
            tree_end = max(
                task.tstep + preds['durs'][task.tid]
                    for task in _sol['opt_model']['start']
                        if task.tid in preds['tree'][tidx]
            )
            duration = tree_end - tree_start
            actual_tree_duration[tidx] = duration
            actual_delay[tidx] = duration - preds['min_tree_dur'][tidx] 

        # update predicates for next schedule for req3
        tr_ids = delay_margin.keys()
        for tr_id in tr_ids:
            curr_delay_m = _sol["opt_model"]["current_delay_margin"][tr_id]
            delay_margin[tr_id] = curr_delay_m

    idcfg[_ig_id]['actual_tree_duration0'] = actual_tree_duration
    idcfg[_ig_id]['actual_delay0'] = actual_delay

    #ccfg[_ig_id]['actual_tree_duration'] = actual_tree_duration
    ccfg['actual_delay'][_ig_id] = actual_delay

def initialize_results(ccfg):
    ccfg["min_duration_sum"] = float("Inf")
    ccfg["last_duration_sum"] = float("Inf")
    ccfg["curr_duration_sum"] = float("Inf")
    ccfg["same_duration_sum_count"] = 0
    ccfg["same_duration_sum_count_max"] = 2
    ccfg["same_delay_count"] = 0
    ccfg["same_delay_count_max"] = 1
    ccfg["dur_sums"] = {}
    ccfg["actual_delay"] = {}
    ccfg["id_tick"] = time.time()

def backup_results(ccfg):
    # update duration sum result
    ccfg["min_duration_sum"] = min(
        ccfg["min_duration_sum"],
        ccfg["curr_duration_sum"]
    )
    ccfg["last_duration_sum"] = ccfg["curr_duration_sum"]
    ccfg["curr_duration_sum"] = 0

    # backup delay sum result
    if len(ccfg["actual_delay"].keys()) > 0:
        ccfg["last_actual_delay"] = {}
        for inst_id, curr_actual_delay in ccfg["actual_delay"].items():
            ccfg["last_actual_delay"][inst_id] = {}
            for tr_id, curr_delay in curr_actual_delay.items():
                ccfg["last_actual_delay"][inst_id][tr_id] = curr_delay
    else:
        ccfg["last_actual_delay"] = {}

def update_duration_count(ccfg):
    curr_dur_sum = ccfg['curr_duration_sum']
    if curr_dur_sum in ccfg['dur_sums']:
        ccfg['dur_sums'][curr_dur_sum] += 1
    else:
        ccfg['dur_sums'][curr_dur_sum] = 1

def duration_count_met(ccfg):
    curr_dur_sum = ccfg['curr_duration_sum']
    duration_count_max = ccfg['same_duration_sum_count_max']
    if ccfg['dur_sums'][curr_dur_sum] >= duration_count_max:
        return True
    else:
        return False

def is_duration_changed(ccfg):
    if ccfg["last_duration_sum"] == ccfg["curr_duration_sum"]:
        result = False
    else:
        result = True

    return result

def is_delay_changed(ccfg, idcfg):
    result = False

    if len(ccfg["last_actual_delay"].keys()) == 0:
        result = True
        return result

    # compute the sum of delay by tr_id
    curr_actual_delay_sum = {
        tr_id: 0 for tr_id in idcfg[0]['track_exts'].keys()
    }
    last_delay_sum = {
        tr_id: 0 for tr_id in idcfg[0]['track_exts'].keys()
    }
    for ig_id, _igidcfg in idcfg.items():
        for tr_id, tidx in _igidcfg['req3_tr_tx'].items():
            curr_actual_delay_sum[tr_id] += ccfg['actual_delay'][ig_id][tidx]
            last_delay_sum[tr_id] += ccfg['last_actual_delay'][ig_id][tidx]

    for tr_id in idcfg[0]["track_exts"].keys():
        if curr_actual_delay_sum[tr_id] != last_delay_sum[tr_id]:
            result = True
            break

    #try:
    #    curr_actual_delay_sum = {
    #        tr_id: sum(
    #            ccfg["actual_delay"][inst_id][tr_id] 
    #                for inst_id in ccfg["actual_delay"])
    #            for tr_id in ccfg["actual_delay"][0].keys()
    #    }
    #except KeyError:
    #    print(f"actual_delay:0:keys:{ccfg['actual_delay'][0].keys()}")
    #    print(f" actual_delay:{ccfg['actual_delay']}")
    #    print(f" last_actual_delay:{ccfg['last_actual_delay']}")
    #    raise KeyError

    #try:
    #    last_delay_sum = {
    #        tr_id: sum(
    #            ccfg["last_actual_delay"][inst_id][tr_id]
    #                for inst_id in ccfg["last_actual_delay"])
    #            for tr_id in ccfg["last_actual_delay"][0].keys()
    #    }
    #except KeyError:
    #    print(f"last_actual_delay:0:keys:{ccfg['actual_delay'][0].keys()}")
    #    print(f" actual_delay:{ccfg['actual_delay']}")
    #    print(f" last_actual_delay:{ccfg['last_actual_delay']}")
    #    raise KeyError

    #for tr_id in ccfg["actual_delay"][0]:
    #    if curr_actual_delay_sum[tr_id] != last_delay_sum[tr_id]:
    #        result = True
    #        break

    #for inst_id, curr_actual_delay in ccfg["actual_delay"].items():
    #    for tr_id, curr_delay in curr_actual_delay.items():
    #        if curr_delay != ccfg["last_actual_delay"][inst_id][tr_id]:
    #            result = True
    #            break

    return result

def check_termination_condition(ccfg, idcfg):
    result = False  # False means not terminating (which is progressing)
    duration_count_max = ccfg["same_duration_sum_count_max"]
    delay_count_max = ccfg["same_delay_count_max"]

    if not ccfg["solvable"]:
        result = True
        return result

    update_duration_count(ccfg)
    if duration_count_met(ccfg):
        result = True
    return result

    #if is_duration_changed(ccfg):
    #    update_duration_count(ccfg)
    #    if duration_count_met(ccfg):
    #        result = True
    #        return result
    #    else:
    #        ccfg["same_duration_sum_count"] = 0
    #else:
    #    ccfg["same_duration_sum_count"] += 1
    #    if ccfg["same_duration_sum_count"] >= duration_count_max:
    #        result = True   # True means terminating (which is not progressing)
    #        return result

    #if is_delay_changed(ccfg, idcfg):
    #    ccfg["same_delay_count"] = 0
    #else:
    #    ccfg["same_delay_count"] += 1
    #    if ccfg["same_delay_count"] >= delay_count_max:
    #        result = True   # True means terminating (which is not progressing)
    #        return result

    return result

def solve_iter_id(gencfg, ccfg, id):
    idcfg = {}
    _reqxx = ccfg["_reqxx"]
    _basic2 = ccfg["_basic2"]
    delay_margin = {}
    ccfg["solvable"] = True
    ig_ids = gencfg['igs'][id]['ig_id']
    ccfg["inst_tree_exts"] = {inst_id: {} for inst_id in range(len(ig_ids))}
    _track_ext = {}

    initialize_results(ccfg)
    progressing = True
    #print(f"#SII, 1, id:{id}")
    while progressing:
        #_dur_comparison  = f"curr_dur_sum:{ccfg['curr_duration_sum']}, "
        #_dur_comparison += f"dur_sums:{ccfg['dur_sums']}"
        #print(f"#SII, 2, {_dur_comparison}")
        backup_results(ccfg)
        for ig_id in ig_ids:
            #print(f"#SII, 3, ig_id:{ig_id}")
            ccfg["inst_id"] = int(ig_id[2:])
            _ig_id = int(ig_id[2:])
            idcfg[_ig_id] = {}

            (_inst, _aux, _req) = load_instance_with_reqs(ccfg, id, ig_id)
            _base_code = _inst + _aux + _req + _basic2 + _reqxx

            preds = parse_instance_and_reqs(ccfg, _inst, _req)
            pre_process_for_reqs(gencfg, ccfg, preds)

            # re-compute track_exts for each tr_id through tree_exts
            for tr_id, (tidx, amount) in preds['tree_exts'].items():
                if tr_id not in _track_ext:
                    _track_ext[tr_id] = amount
                else:
                    _track_ext[tr_id] += amount

            _additional_code = get_additional_code(preds, _aux, delay_margin)

            idcfg[_ig_id] |= preds
            ctl = create_control(gencfg, _base_code, _additional_code)
            timeout_remained = gencfg["timeout"]
            tick = time.time()

            _sol = {}
            tock2 = -1
            opt_model = None
            in_progress = True
            with ctl.solve(yield_=True, async_=True) as ret:
                while in_progress:
                    tick2 = time.time()
                    ret.resume()
                    in_progress = ret.wait(timeout_remained)
                    _time = time.time()
                    tock = _time - tick2
                    if in_progress:
                        m = ret.model()
                        if m is None:
                            in_progress = False
                            if str(ret.get()) == "SAT":
                                tock2 = _time - tick
                                opt_model = model
                        else:
                            model = parse_solution_for_reqs(m)
                            if timeout_remained <= tock:
                                in_progress = False
                            timeout_remained -= tock
                if opt_model == None:
                    ret.cancel()
                update_solution(_sol, ccfg, tock2, opt_model)
            #print(f"#SII, 4")
            process_for_req3(idcfg, _ig_id, _sol, ccfg, preds, delay_margin)
        
            if opt_model is None:
                #print(f"#SII, 5, opt_model:{opt_model}")
                ccfg["solvable"] = False
                #break   # we ignore the case when it is not solverable

        progressing = not check_termination_condition(ccfg, idcfg)
        #_dur_sums = f"dur_sums:{ccfg['dur_sums']}"
        #print(f"#SII, 6, progressing:{progressing}, {_dur_sums} ==== ====\n")
    ccfg["id_time"] = time.time() - ccfg["id_tick"]

    idcfg[0]["track_exts"] = _track_ext
    return idcfg

def write_iter_id(gencfg, ccfg, idcfg):
    track_extension = idcfg[0]["track_exts"]
    cfgid = {
        f"ig{_ig_id:0{2 + int(gencfg['inst_count_max']) // 16}x}": {}
            for _ig_id in idcfg.keys()
    }

    ig_ids = {}
    for _ig_id, _ig_id_value in idcfg.items():
        ig_id = f"ig{_ig_id:0{2 + int(gencfg['inst_count_max']) // 16}x}"
        ig_ids[ig_id] = _ig_id_value
    idcfg["ig_ids"] = ig_ids

    cumulative_time = 0
    cumulative_dur = 0
    cumulative_excess = {key: 0 for key in track_extension.keys()}
    cumulative_delay = {key: 0 for key in track_extension.keys()}

    for ig_id in idcfg['ig_ids']:
        _igidcfg = idcfg['ig_ids'][ig_id]
        cfgid[ig_id]['punctuality'] = {}
        cfgid[ig_id]['excess'] = {}
        cfgid[ig_id]['delay'] = {}

        for req1_tree in _igidcfg['owner']['req1']:
            earlist_ones, latest_ones = [], []
            for start in _igidcfg['opt_model']['start']:
                if start.tid in _igidcfg['tree'][req1_tree]:
                    earlist_ones.append((start.tstep, start.tid))
                    _end_dur = _igidcfg['durs'][start.tid]
                    latest_ones.append((start.tstep + _end_dur, start.tid))
            earlist_ones.sort()
            latest_ones.sort(reverse=True)
            min_step = earlist_ones[0][0]
            max_step = latest_ones[0][0]
            earlist = [
                (_t, _step) 
                    for _step, _t in earlist_ones if _step == min_step
            ]
            latest = [
                (_t, start.tstep)
                    for start in _igidcfg['opt_model']['start']
                        for _step, _t in latest_ones 
                            if start.tid == _t and _step == max_step
            ]
            
            req1_tree_dict = {}
            req1_tree_dict["deadline"] = _igidcfg['deadline'][req1_tree]
            req1_tree_dict["earlist"] = earlist
            req1_tree_dict["latest"] = latest
            req1_tree_dict["duration"] = latest_ones[0][0] - earlist_ones[0][0]
            if latest_ones[0][0] == req1_tree_dict["deadline"]:
                req1_tree_dict["result"] = "pass"
            else:
                req1_tree_dict["result"] = "fail"
            cfgid[ig_id]['punctuality'][req1_tree] = req1_tree_dict

        for tr_id, req2_tree in _igidcfg['req2_tr_tx'].items():
            req2_tree_dict = {}
            req2_tree_dict["tree_id"] = req2_tree
            cvalues = _igidcfg['req2_tidx_cvalues'][req2_tree]
            req2_tree_dict['camount'] = cvalues['camount']
            req2_tree_dict['cmargin'] = cvalues['cmargin']
            req2_tree_dict['excess'] = _igidcfg['excess'][tr_id]
            cfgid[ig_id]['excess'][tr_id] = req2_tree_dict

        for tr_id, tidx in _igidcfg['req3_tr_tx'].items():
            dur = _igidcfg['actual_tree_duration0'][tidx]
            delay = _igidcfg['actual_delay0'][tidx]

            req3_tree_dict = {}
            req3_tree_dict["tree_id"] = tidx
            req3_tree_dict["duration"] = dur
            req3_tree_dict["delay"] = delay
            cfgid[ig_id]['delay'][tr_id] = req3_tree_dict

        cumulative_time += _igidcfg["time"]
        cfgid[ig_id]["time"] = _igidcfg["time"]
        cumulative_dur += _igidcfg["total_dur"]
        cfgid[ig_id]["total_dur"] = _igidcfg["total_dur"]
        for tr_id in _igidcfg['req2_tr_tx'].keys():
            cumulative_excess[tr_id] += _igidcfg['excess'][tr_id]

        for tr_id, tidx in _igidcfg['req3_tr_tx'].items():
            cumulative_delay[tr_id] += _igidcfg['actual_delay0'][tidx]

    _idcfg = {}
    _idcfg["ig_ids"] = cfgid
    _idcfg["time"] = cumulative_time
    _idcfg["total_dur"] = cumulative_dur
    _idcfg["excess_per_track"] = cumulative_excess
    _idcfg["delay_per_track"] = cumulative_delay
    _idcfg["track_extension"] = track_extension
    _idcfg["id_time"] = ccfg["id_time"]
    return _idcfg

ccfg = {}
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
    _basic2 = load_file(f"_asp_trim_reqs.lp")
    _req1 = load_file(f"req1_rewritten4.lp")
    _req2 = load_file(f"req2_renamed7.lp")
    _req3 = load_file(f"req3_renamed6.lp")
    ccfg["_basic"] = _basic
    ccfg["_basic2"] = _basic2
    ccfg["_reqxx"] = _req1 + _req2 + _req3

    inst_dir = f"../instances"
    inst_id_dir = f"{inst_dir}/{gencfg['inst_id']}"

    ccfg["inst_id"] = gencfg["inst_id"]
    ccfg["inst_id_dir"] = inst_id_dir

    sol_file = f"{inst_dir}/{gencfg['inst_id']}"
    sol = {}
    sol["inst_id"] = f"{gencfg['inst_id']}"
    sol["task_max_count"] = f"{gencfg['task_max_count']}"
    sol["num_of_insts"] = f"{gencfg['num_of_insts']}"
    sol["inst_count_max"] = f"{gencfg['inst_count_max']}"
    sol["resource_quarter"] = f"{gencfg['resource_quarter']}"
    sol["resource_type_count"] = f"{gencfg['resource_type_count']}"
    sol["timeout"] = f"{gencfg['timeout']}"
    sol["igs"] = {}

    igs_len = len(gencfg['igs'].keys())
    _tick = time.time()
    for idx, id in enumerate(gencfg["igs"].keys()):
        print(f"[{idx:03d}/{igs_len}], {id}, ", end='', flush=True)
        idcfg = solve_iter_id(gencfg, ccfg, id)
        sol["igs"][id] = write_iter_id(gencfg, ccfg, idcfg)
        #if (idx % 5) == 0:
        _tock = time.time() - _tick
        print(f"{_tock} sec")
        if (idx % 5) == 0:
            print(f"\n")
        _tick = time.time()

    # dump the output solution
    with open(sol_file + f"_iter_sol.json", 'w') as f:
        json.dump(sol, f, indent=4, sort_keys=True)
