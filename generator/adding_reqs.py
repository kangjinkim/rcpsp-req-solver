import re
from math import ceil, floor
import random
from clingo import Control
from take_parts import get_track_count

def parse_pert_chart(buff, cfg):
    task_pattern = re.compile(r'task\((\d+)\)')
    dur_pattern = re.compile(r'dur\((\d+),\s(\d+)\)')
    psrel_pattern = re.compile(r'psrel\((\d+),\s(\d+)\)')
    rsreq_pattern = re.compile(r'rsreq\((\d+),\s(\d+),\s(\d+)\)')
    total_dur_pattern = re.compile(r'total_dur\((\d+)\)')
    limit_pattern = re.compile(r'limit\((\d+),\s(\d+)\)')
    ig_id_pattern = re.compile(r'ig_id\(\"(\w+)\"\)')
    tree_id_pattern = re.compile(r'tree_id\(\"(\w+)\"\)')
    #owner_pattern = re.compile(r'owner\((\d+),\s\"(\w+)\"\)')
    owner_pattern = re.compile(r'owner\(\"(\w+)\",\s\"(\w+)\"\)')
    tree_pattern = re.compile(r'tree\(\"(\w+)\",\s(\d+)\)')


    tasks = [int(match.group(1)) for match in task_pattern.finditer(buff)]
    durs = {
        int(match.group(1)): int(match.group(2))
            for match in dur_pattern.finditer(buff)
    }
    psrels = [
        (int(match.group(1)), int(match.group(2)))
            for match in psrel_pattern.finditer(buff)
    ]
    rsreq_list = {
        (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            for match in rsreq_pattern.finditer(buff)
    }
    rsreqs = {
        t1: {r: a for t2, r, a in rsreq_list if t2 == t1}
            for t1 in tasks
    }
    limits = {
        int(match.group(1)): int(match.group(2))
            for match in limit_pattern.finditer(buff)
    }
    ig_id = [str(match.group(1)) for match in ig_id_pattern.finditer(buff)][0]
    tree_id = set([
        str(match.group(1)) 
            for match in tree_id_pattern.finditer(buff)
    ])
    owners = {}
    for match in owner_pattern.finditer(buff):
        #if int(match.group(1)) not in owners:
        #    owners[int(match.group(1))] = []
        #owners[int(match.group(1))].append(str(match.group(2)))
        if str(match.group(1)) not in owners:
            owners[str(match.group(1))] = []
        owners[str(match.group(1))].append(str(match.group(2)))
    trees = {}
    for match in tree_pattern.finditer(buff):
        if str(match.group(1)) not in trees:
            trees[str(match.group(1))] = []
        trees[str(match.group(1))].append(int(match.group(2)))

    cfg["tasks"] = tasks
    cfg["durs"] = durs
    cfg["psrels"] = psrels
    cfg["rsreq"] = rsreqs
    cfg["limits"] = limits
    cfg["owner"] = owners
    cfg["ig_id"] = ig_id
    cfg["trees"] = trees
    cfg["tree_id"] = tree_id

def decide_factors_for_req1(cfg, inst_cfg, gencfg, req_uid, req_idx):
    cfg[req_idx]["last_tasks"] = {}
    for i, icfg in inst_cfg.items():
        #tree_start_end_time = compute_punctual_end_times(icfg, req_uid)
        tree_start_end_time = compute_punctual_end_times(icfg, req_idx)
        last_tasks = calculate_longest_pairs(icfg, tree_start_end_time)
        cfg[req_idx]["last_tasks"] |= last_tasks

    #(cdur, tree_dur) = solve_treewise(cfg, inst_cfg, gencfg, req_uid)
    (cdur, tree_dur) = solve_treewise(cfg, inst_cfg, gencfg, req_idx)
    cfg[req_idx]["total_dur"] = tree_dur

def decide_factors_for_req2(cfg, inst_cfg, gencfg, req_uid, req_idx):
    rstar = gencfg["rstar"]
    entire_cmargin = 0

    ### get tracks
    track_count = get_track_count(gencfg["task_max_count"])

    tracks = {j:[] for j in range(track_count)}
    for i, icfg in inst_cfg.items():
        cmargin = 0
        _tidx_list = icfg['owner'][req_idx]
        for idx_j, tidx in enumerate(icfg["owner"][req_idx]):
            tree_margin = 0
            for t in icfg["forest"].trees[tidx]:
                if rstar in icfg["forest"].tdict[t.tid]:
                    amount = icfg["forest"].tdict[t.tid].amount(rstar)
                    margin = icfg["forest"].rstar_max - amount
                    tree_margin += margin
            tracks[idx_j].append(tree_margin)
            cmargin += tree_margin
        entire_cmargin += cmargin

    ### get preferable_amounts
    preferable_amounts = {
        j: sum(tracks[j]) // 2
            for j in tracks.keys()
    }
    cfg[req_idx]["preferable_amounts"] = preferable_amounts
    cfg[req_idx]["tracks"] = tracks
    cfg[req_idx]["tree_range"] = {idx: {} for idx in tracks.keys()}

    ### decide initial pairs of lowb and highb
    for idx_j in tracks.keys():
        remained = preferable_amounts[idx_j]
        for i, icfg in inst_cfg.items():
            tidx_list = icfg["owner"][req_idx]
            try:
                tidx = icfg["owner"][req_idx][idx_j]
            except IndexError:
                raise IndexError(f"idx_j:{idx_j}")
            rel_tasks = {}
            tree_margin = 0
            for t in icfg["forest"].trees[tidx]:
                # gather how many tasks have rstar resource in it, and the list
                if gencfg["rstar"] in icfg["forest"].tdict[t.tid]:
                    amount = icfg["forest"].tdict[t.tid].amount(rstar)
                    rel_tasks[t.tid] = icfg["forest"].rstar_max - amount
                    # gather margins for the list
                    tree_margin += rel_tasks[t.tid]
            cq = tracks[idx_j][i]
            tq = sum(tracks[idx_j][i:])
            rea = (cq / tq) * remained
            rea_ru = round(rea)
            if ceil(rea) == round(rea):
                rea_lb = ceil(rea)
                rea_hb = rea_lb + 1
            else:
                rea_lb = floor(rea)
                rea_hb = rea_lb + 1
            remained -= rea_lb
            cfg[req_idx]["tree_range"][idx_j][tidx] = (rea_lb, rea_hb)
        assert remained == 0

def compute_punctual_end_times(cfg, req_idx):
    tree_start_end_time = {}
    #print(f"req_idx:{req_idx}, cfg['owner'].keys():{cfg['owner'].keys()}")
    #print(f"cfg.keys:{cfg.keys()}")
    #print(f"cfg['owner']:{cfg['owner']}")
    for tidx in cfg["owner"][req_idx]:
        try:
            a_tree = cfg["forest"].trees[tidx]
        except KeyError:
            print(f"CPET #1, tidx:{tidx}, " + \
                  f"cfg_forest_trees:{cfg['forest'].trees}")
            raise KeyError
        min_eis = min(cfg["eis"][t.tid] for t in cfg["forest"].trees[tidx])
        max_termination = max(
            cfg["eis"][t.tid] + cfg["durs"][t.tid] 
                for t in cfg["forest"].trees[tidx]
        )
        tree_start_end_time[tidx] = (min_eis, max_termination)

    min_dur, max_dur = min(cfg["durs"].values()), max(cfg["durs"].values())

    alpha_steps = [
        random.randint(min_dur, max_dur) 
            for _ in range(len(tree_start_end_time.keys()) - 1)
    ]

    #print(f"alpha_steps:{alpha_steps}")
    _starts, _ends = [], []
    _num_of_trees = len(cfg["owner"][req_idx])
    min_start = cfg["total_dur"] // (_num_of_trees + 1)
    max_start = cfg["total_dur"] // _num_of_trees
    for _idx, tidx in enumerate(cfg["owner"][req_idx]):
        if _idx == 0:
            start_timestep = random.randint(min_start, max_start)
        else:
            start_timestep = _ends[-1] + alpha_steps[_idx - 1]

        end_timestep = start_timestep + tree_start_end_time[tidx][1]
        _starts.append(start_timestep)
        _ends.append(end_timestep)

    start_end_time = {
        tidx: (_starts[_idx], _ends[_idx])
            for _idx, tidx in enumerate(cfg["owner"][req_idx])
    }

    return start_end_time

def calculate_longest_pairs(cfg, start_end_time):
    last_tasks = {}
    for tidx, (start_ts, end_ts) in start_end_time.items():
        #### find all pairs having the maximum value of eis + dur
        #longest_tasks = [
        #    (cfg["eis"][t.tid] + cfg["durs"][t.tid], t.tid)
        #        for t in cfg["forest"].trees[tidx]
        #]
        #longest_tasks.sort(reverse=True)
        #max_eis_dur = longest_tasks[0][0]

        #### find their eis
        #### decide the proper decision variable (pairs of task_id + start_time)
        #_last_tasks = [
        #    #(t.tid, end_ts - cfg["durs"][t.tid])
        #    (t.tid, end_ts) # switched to keep txid, not the longest last task
        #        for t in cfg["forest"].trees[tidx]
        #            if cfg["eis"][t.tid] + cfg["durs"][t.tid] == max_eis_dur
        #]
        #last_tasks[tidx] = _last_tasks
        last_tasks[tidx] = [end_ts]

    return last_tasks

def decide_factors_for_req3(cfg, inst_cfg, gencfg, req_uid, req_idx):
    #(cdur, tree_dur) = solve_treewise(cfg, inst_cfg, gencfg, req_uid)
    (cdur, tree_dur) = solve_treewise(cfg, inst_cfg, gencfg, req_idx)

    extra = {idx: dur_sum // 2 for idx, dur_sum in cdur.items()}
    tree_extra = {
        idx: {
            i: round((tdur / cdur[idx]) * extra[idx])
                for i, tdur in tree_dur[idx].items()
        }
            for idx in tree_dur.keys()
    }
    cfg[req_idx]["extra"] = extra
    cfg[req_idx]["tree_extra"] = tree_extra
    cfg[req_idx]["total_dur"] = tree_dur
    cfg[req_idx]["cdur"] = cdur


def convert_to_individual_instances(cfg, inst_cfg, req_idx):
    #print(f"convert_to_ind, req_idx:{req_idx}")
    for i, icfg in inst_cfg.items():
        icfg["ind_inst"] = {}
        icfg["ind_inst_max_time"] = {}
        for idx_j, tidx in enumerate(icfg["owner"][req_idx]):
            itasks = set([t.tid for t in icfg["forest"].trees[tidx]])
            buff = ""
            for t in icfg["forest"].trees[tidx]:
                buff += f"task({t.tid}).\n"
            for t in icfg["forest"].trees[tidx]:
                buff += f"dur({t.tid}, {t.dur}).\n"
            for t in icfg["forest"].trees[tidx]:
                for p in t.pred:
                    buff += f"psrel({p.tid}, {t.tid}).\n"
            for t in icfg["forest"].trees[tidx]:
                for rtype, ramount in t.resources.items():
                    buff += f"rsreq({t.tid}, {rtype}, {ramount}).\n"
            for rtype, lamount in icfg["limits"].items():
                buff += f"limit({rtype}, {lamount}).\n"

            # add eis and lis
            eis = calculate_individual_eis(icfg["psrels"], icfg["durs"],itasks)
            for tid, eis_step in eis.items():
                if tid in itasks:
                    buff += f"eis({tid}, {eis_step}).\n"

            lis = calculate_individual_lis(icfg["psrels"], icfg["durs"],itasks)
            for tid, lis_step in lis.items():
                if tid in itasks:
                    buff += f"lis({tid}, {lis_step}).\n"

            # add max_time and step
            # NOTE: for the case when it is a singly connected tree, 
            #   if we add 2 to the dur. sum, it becomes that eis[A] == lis[A].
            #   For the safety purpose, by adding 3 to the dur. sum,
            #   we strictly makes eis[A] < lis[A].
            max_time = sum([t.dur for t in icfg["forest"].trees[tidx]]) + 3

            buff += f"max_time({max_time}).\n"
            #buff += f"step(1..{max_time}).\n"
            buff += f"step(0..{max_time}).\n"   # step starts from 0.
            buff += f"level(0..{max(icfg['limits'].values())}).\n"

            # get tails
            tails = set([
                t for t in icfg["forest"].trees[tidx]
                    if len(t.succ) == 0
            ])

            # add extra task to tails
            etask_id = max([tid for tid in icfg["eis"].keys()]) + 1
            buff += f"etask({etask_id}).\n"
            buff += f"task({etask_id}).\n"
            #buff += f"dur({etask_id}, 1).\n"
            buff += f"dur({etask_id}, 0).\n"    # dummy task should have 0 dur.
            for tail in tails:
                buff += f"psrel({tail.tid}, {etask_id}).\n"
            #buff += f"lis({etask_id}, {max_time - 1}).\n"
            buff += f"lis({etask_id}, {max_time}).\n"
            latest_tails = [
                (eis[t.tid] + t.dur, t)
                    for t in icfg["forest"].trees[tidx]
            ]
            latest_tails.sort(key=lambda x: x[0], reverse=True)
            #print(f"latest_tails:{latest_tails}")
            ltail_step, ltail = latest_tails[0]
            buff += f"eis({etask_id}, {ltail_step}).\n"

            icfg["ind_inst"][tidx] = buff
            icfg["ind_inst_max_time"][tidx] = max_time
            #print(f"    ind_inst[{tidx}]:{buff}\n\n")

def compute_individual_tree_dur(cfg, inst_cfg, required_user_id):
    _base = ""
    with open("../solver/_asp_trim.lp") as f:
        read_data = f.read()
        _base += read_data

    cdur = {idx:0 for idx in cfg['req2']['tracks'].keys()}

def parse_solution_for_ind_inst(buff):
    estart_pattern = re.compile(r'estart\((\d+)\)')
    Estart = [int(match.group(1)) for match in estart_pattern.finditer(buff)]

    predicates = {}
    if len(Estart) > 0:
        predicates["estart"] = Estart

    return predicates

def solve_treewise(cfg, inst_cfg, gencfg, req_idx):
    track_count = get_track_count(gencfg["task_max_count"])

    convert_to_individual_instances(cfg, inst_cfg, req_idx)
    _base = ""

    with open("../solver/_asp_trim.lp") as f:
        read_data = f.read()
        _base += read_data

    cdur = {idx: 0 for idx in range(track_count)}
    tree_dur = {idx: {} for idx in range(track_count)}
    for i, icfg in inst_cfg.items():
        for idx_j, tidx in enumerate(icfg["owner"][req_idx]):
            ctl = Control()
            codes = icfg["ind_inst"][tidx] + _base
            ctl.add("base", [], codes)
            parts = []
            parts.append(("base", []))
            ctl.ground(parts)

            opt_model = []
            with ctl.solve(yield_ = True) as ret:
                opt_model = parse_solution_for_ind_inst(f"{list(ret)[-1]}")
            total_dur = opt_model['estart'][-1]
            print(f"  success!, tidx:{tidx}, " + \
                  f"max_time:{icfg['ind_inst_max_time'][tidx]}, " + \
                  f"total_dur:{total_dur}")
            cdur[idx_j] += total_dur
            tree_dur[idx_j][tidx] = total_dur

    return (cdur, tree_dur)

def write_factors_for_req1(cfg, inst_cfg, req_uid, req_idx):
    for icfg in inst_cfg.values():
        buff = "" if "buff" not in icfg else icfg["buff"]

        buff += f"\n%%%% factors for \"{req_idx}\" %%%%\n"
        #tidx_list = icfg["owner"][req_uid]
        tidx_list = icfg["owner"][req_idx]
        for tidx, value in cfg[req_idx].items():
            if tidx == "last_tasks":
                for _tidx, _value in value.items():
                    if _tidx in tidx_list:
                        buff += f"deadline(\"{_tidx}\", {_value[0]}).\n"
                        #buff += f"deadline(\"{_tidx}\", {_value[0][1]}).\n"
                        #        f"{_value[0][0]}, {_value[0][1]}).\n"
            elif tidx == "total_dur":
                for track_id, _pair in value.items():
                    for _tidx, dur in _pair.items():
                        if _tidx in tidx_list:
                            buff += f"min_tree_dur(\"{_tidx}\", {dur}).\n"
        icfg["buff"] = buff

def write_factors_for_req2(cfg, inst_cfg, req_uid, req_idx):
    for i, icfg in inst_cfg.items():
        buff = "" if "buff" not in icfg else icfg["buff"]

        buff += f"\n%%%% factors for \"{req_idx}\" %%%%\n"
        #tidx_list = icfg["owner"][req_uid]
        tidx_list = icfg["owner"][req_idx]
        for tidx, value in cfg[req_idx].items():
            if tidx == "preferable_amounts":
                for track_id, amount in value.items():
                    buff += f"preferable_amount({track_id}, {amount}).\n"
            elif tidx == "tracks":
                for track_id, _quarters in value.items():
                    tid = track_id
                    _tidx = tidx_list[track_id]
                    amount = _quarters[i]
                    buff += f"quarter({tid}, \"{_tidx}\", {amount}).\n"
            elif tidx == "tree_range":
                for track_id, _pair in value.items():
                    for _tidx, (lb, hb) in _pair.items():
                        if _tidx in tidx_list:
                            buff += f"preferable_range" + \
                                    f"({track_id}, \"{_tidx}\", {lb}, {hb}).\n"
        icfg["buff"] = buff

def write_factors_for_req3(cfg, inst_cfg, req_uid, req_idx):
    for icfg in inst_cfg.values():
        buff = "" if "buff" not in icfg else icfg["buff"]

        buff += f"\n%%%% factors for \"{req_idx}\" %%%%\n"
        #tidx_list = icfg["owner"][req_uid]
        tidx_list = icfg["owner"][req_idx]
        for tidx, value in cfg[req_idx].items():
            if tidx == "extra":
                for track_id, amount in value.items():
                    buff += f"track_extension({track_id}, {amount}).\n"
            elif tidx == "tree_extra":
                for track_id, _pair in value.items():
                    for _tidx, amount in _pair.items():
                        if _tidx in tidx_list:
                            buff += f"tree_extension" + \
                                    f"({track_id}, \"{_tidx}\", {amount}).\n"
            elif tidx == "total_dur":
                for track_id, _pair in value.items():
                    for _tidx, dur in _pair.items():
                        if _tidx in tidx_list:
                            buff += f"min_tree_dur(\"{_tidx}\", {dur}).\n"
            elif tidx == "cdur":
                for track_id, dur in value.items():
                    buff += f"cumulative_dur({track_id}, {dur}).\n"
        icfg["buff"] = buff

def calculate_individual_eis(psrel, dur, itasks):
    # Forward Pass
    eis = {}        # Earlist Start Times for each task
    visited = set()

    snodes = set()

    _psrel = set([(p, s) for (p, s) in psrel if p in itasks and s in itasks])
    for (p1, s1) in _psrel:
        found = False
        for (p2, s2) in _psrel:
            if p1 == s2:
                found = True
                break
        if not found:
            snodes.add(p1)

    for snode in snodes:
        #eis[snode] = 1
        eis[snode] = 0      # The earlist time step starts from step 0.
    stack = [(p, s) for (p, s) in _psrel if p in snodes]

    while len(stack) > 0:
        (p, s) = stack.pop(-1)
        #if (p, s) in visited:
        #    continue
        #visited.add((p, s))
        if s not in eis:
            eis[s] = eis[p] + dur[p]
        else:
            eis[s] = max(eis[s], eis[p] + dur[p])
        for (p2, s2) in _psrel:
            if s == p2:
            #if s == p2 and (p2, s2) not in visited:
                stack.append((p2, s2))

    #_dur = {key:value for key, value in dur.items() if key in itasks}
    #print(f"cal_ind_eis #1, _psrel:{_psrel}, eis:{eis}, dur:{_dur}")
    return eis

def calculate_individual_lis(psrel, dur, itasks):
    # Backward Pass
    lis = {}    # Latest Start Times for each task
    total_dur = sum(dur[t] for t in itasks)
    #total_dur = sum(dur[t] for t in itasks) + 1
    #total_dur = sum(dur.values()) + 1
    visited = set()
    enodes = set()

    _psrel = [(p, s) for (p, s) in psrel if p in itasks and s in itasks]

    for (p1, s1) in _psrel:
        found = False
        for (p2, s2) in _psrel:
            if s1 == p2:
                found = True
                break
        if not found:
            enodes.add(s1)
    for enode in enodes:
        lis[enode] = total_dur - dur[enode]
    stack = [(p, s) for (p, s) in _psrel if s in enodes]
    while len(stack) > 0:
        (p, s) = stack.pop(-1)
        if (p, s) in visited:
            continue
        #visited.add((p, s))
        if p not in lis:
            lis[p] = lis[s] - dur[p]
        else:
            lis[p] = min(lis[p], lis[s] - dur[p])
        for (p2, s2) in _psrel:
            if p == s2:
            #if p == s2 and (p2, s2) not in visited:
                stack.append((p2, s2))
    #_dur = {key:value for key, value in dur.items() if key in itasks}
    #print(f"cal_ind_lis #1, _psrel:{_psrel}, lis:{lis}, dur:{_dur}")
    return lis

factor_decision_vectors = [
    decide_factors_for_req1,
    decide_factors_for_req2,
    decide_factors_for_req3
]

req_list = ["req1", "req2", "req3"]
to_req_uid = {
    req_idx: req_uid
        for req_uid, req_idx in enumerate(req_list)
}
to_req_idx = {
    req_uid: req_idx
        for req_idx, req_uid in to_req_uid.items()
}

factor_write_vectors = [
    write_factors_for_req1,
    write_factors_for_req2,
    write_factors_for_req3
]
