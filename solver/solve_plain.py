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

def compute_delay_range(ccfg):
    txid_to_tr = {txid: trid for trid, (txid, _) in ccfg["tree_exts"].items()}
    d_range = {
        txid_to_tr[txid]: (0, ccfg["max_time"] - tree_dur)
            for txid, tree_dur in ccfg["min_tree_dur"].items()
                if txid in txid_to_tr
    }
    return d_range

def solve_plain_id(gencfg, ccfg, id):
    idcfg = {}
    #_reqxx = ccfg["_reqxx"]
    _basic = ccfg["_basic"]
    delay_margin = {}
    ccfg["actual_delay"] = {}
    ig_ids = gencfg['igs'][id]['ig_id']
    ccfg["inst_tree_exts"] = {inst_id: {} for inst_id in range(len(ig_ids))}
    _track_ext = {}

    for ig_id in ig_ids:
        ccfg["inst_id"] = int(ig_id[2:])
        _ig_id = int(ig_id[2:])
        idcfg[_ig_id] = {}

        base_id = f"{id}_{ig_id}"
        base = f"{ccfg['inst_id_dir']}/{base_id}"
        _inst = load_file(f"{base}_inst.lp")
        _aux = load_file(f"{base}_aux.lp")
        _req = load_file(f"{base}_reqs.lp")
        _base_code = _inst + _aux + _req + _basic

        preds = {}
        preds["inst_id"] = ccfg["inst_id"]
        preds["inst_tree_exts"] = ccfg["inst_tree_exts"]

        preds |= parse_inst_predicates(_inst)
        preds |= parse_inst_predicates2(_inst)

        parse_instance_for_req1(preds, _req)
        parse_instance_for_req2(preds, _req)
        parse_instance_for_req3(preds, _req)

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

        # re-compute track_exts for each tr_id through tree_exts
        for tr_id, (tidx, amount) in preds['tree_exts'].items():
            if tr_id not in _track_ext:
                _track_ext[tr_id] = amount
            else:
                _track_ext[tr_id] += amount

        # add predicates for req3
        parse_aux_predicates(_aux, preds)
        d_range = compute_delay_range(preds)

        #if len(delay_margin.keys()) == 0:
        #    for trid in d_range.keys():
        #        delay_margin[trid] = 0

        # keep these values to somewhere under the idcfg[_ig_id]
        idcfg[_ig_id] |= preds

        # create control
        ctl = Control()
        ctl.add("base", ["rstar"], _base_code)
        parts = []
        parts.append(("base", [Number(gencfg["rstar"])]))
        ctl.ground(parts)

        # parse the solution
        timeout_remained = gencfg["timeout"]
        tick = time.time()

        # solve
        _sol = {}
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
                        model = parse_solution_for_req1_in_asp(f"{m}")
                        model |= parse_solution_for_req2_in_asp(f"{m}")
                        model |= parse_solution_for_req3_in_asp(f"{m}")
                        if timeout_remained - tock > 0:
                            timeout_remained -= tock
                        else:
                            in_progress = False
            if opt_model == None:
                ret.cancel()
                _sol["total_dur"] = -1
                _sol["time"] = -1
                _sol["excess"] = {r: 0 for r, x in preds['req2_tr_tx'].items()}
                _sol["opt_model"] = None
            else:
                _sol["total_dur"] = opt_model['estart'][-1]
                _sol["time"] = tock2
                #_sol["excess"] = opt_model['excess_in_total']
                _sol["excess"] = {r: 0 for r, x in preds['req2_tr_tx'].items()}
                _sol["opt_model"] = opt_model

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
            #tr_ids = delay_margin.keys()
            #for tr_id in tr_ids:
            #    delay_margin[tr_id] = opt_model["current_delay_margin"][tr_id]

        idcfg[_ig_id]['actual_tree_duration0'] = actual_tree_duration
        idcfg[_ig_id]['actual_delay0'] = actual_delay

    idcfg[0]["track_exts"] = _track_ext

    return idcfg

def write_plain_id(gencfg, ccfg, idcfg):
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
    #_basic2 = load_file(f"_asp_trim_reqs.lp")
    #_req1 = load_file(f"req1_rewritten4.lp")
    #_req2 = load_file(f"req2_renamed7.lp")
    #_req3 = load_file(f"req3_renamed6.lp")
    ccfg["_basic"] = _basic
    #ccfg["_basic2"] = _basic2
    #ccfg["_reqxx"] = _req1 + _req2 + _req3

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
        idcfg = solve_plain_id(gencfg, ccfg, id)
        sol["igs"][id] = write_plain_id(gencfg, ccfg, idcfg)
        _tock = time.time() - _tick
        print(f"{_tock} sec")
        if (idx % 5) == 0:
            print(f"\n")
        _tick = time.time()

    # dump the output solution
    with open(sol_file + f"_plain_sol.json", 'w') as f:
        json.dump(sol, f, indent=4, sort_keys=True)
