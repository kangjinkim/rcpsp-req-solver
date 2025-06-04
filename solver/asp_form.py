# - load a file to a string buffer
# - parse predicates from a file (or a string buffer) in asp form
# - create a string buffer with predicates in asp form
import re
from predicate import Start

def load_file(infile):
    buff = ""
    with open(infile, encoding="utf-8") as f:
        read_data = f.read()
        buff += read_data
    return buff

def write_file(buff, outfile):
    with open(outfile, 'w') as f:
        f.writelines(buff)

def parse_inst_predicates(buff):
    # NOTE: Aware that the original instance (from buff) doesn't specify 
    #   head and tail tasks. Hence, the auxiliary predicates including their 
    #   relations (psrel), dur, eis, lis, etask, etc, are absent too.
    task_pattern = re.compile(r'task\((\d+)\)')
    dur_pattern = re.compile(r'dur\((\d+),\s(\d+)\)')
    psrel_pattern = re.compile(r'psrel\((\d+),\s(\d+)\)')
    rsreq_pattern = re.compile(r'rsreq\((\d+),\s(\d+),\s(\d+)\)')
    total_dur_pattern = re.compile(r'total_dur\((\d+)\)')
    limit_pattern = re.compile(r'limit\((\d+),\s(\d+)\)')

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
    predicates = {
        "tasks": tasks,
        "durs": durs,
        "psrels": psrels,
        "rsreqs": rsreqs,
        "limits": limits
    }
    return predicates

def parse_inst_predicates2(buff):
    tree_pattern = re.compile(r'tree\(\"(\w+)\",\s(\d+)\)')
    owner_pattern = re.compile(r'owner\(\"(\w+)\",\s\"(\w+)\"\)')
    ig_id_pattern = re.compile(r'ig_id\(\"(\w+)\"\)')

    trees = {
        str(match.group(1)): set()
            for match in tree_pattern.finditer(buff)
    }
    for match in tree_pattern.finditer(buff):
        trees[str(match.group(1))].add(int(match.group(2)))
    owners = {
        str(match.group(1)): set()
            for match in owner_pattern.finditer(buff)
    }
    for match in owner_pattern.finditer(buff):
        owners[str(match.group(1))].add(str(match.group(2)))
    ig_id = [str(match.group(1)) for match in ig_id_pattern.finditer(buff)][0]

    predicates = {
        "tree": trees,
        "owner": owners,
        "ig_id": ig_id
    }
    return predicates

def parse_aux_predicates(buff, preds):
    #head_pattern = re.compile(r'task\')
    head = 0
    tail_pattern = re.compile(r'etask\((\d+)\)')
    tail = [int(match.group(1)) for match in tail_pattern.finditer(buff)][0]
    psrel_pattern = re.compile(r'psrel\((\d+),\s(\d+)\)')
    psrels = [
        (int(match.group(1)), int(match.group(2)))
            for match in psrel_pattern.finditer(buff)
    ]
    for pred, succ in psrels:
        preds["psrels"].append((pred, succ))
    dur_pattern = re.compile(r'dur\((\d+),\s(\d+)\)')
    durs = {
        int(match.group(1)): int(match.group(2))
            for match in dur_pattern.finditer(buff)
    }
    for task_id, task_dur in durs.items():
        preds["durs"][task_id] = task_dur
    max_time_pattern = re.compile(r'max_time\((\d+)\)')
    preds["max_time"] = [
        int(match.group(1)) 
            for match in max_time_pattern.finditer(buff)
    ][0]
    return preds

def parse_reqs_predicates(buff):
    pass

def parse_solution_in_asp(buff):
    # define regex patterns for necessary predicates
    start_pattern = re.compile(r'start\((\d+),(\d+)\)')
    etask_pattern = re.compile(r'etask\((\d+)\)')
    estart_pattern = re.compile(r'estart\((\d+)\)')

    # parse the buff and create objects
    Starts = [
        Start(int(match.group(1)), int(match.group(2)))
            for match in start_pattern.finditer(buff)
    ]

    Etask = [int(match.group(1)) for match in etask_pattern.finditer(buff)]

    Estart = [int(match.group(1)) for match in estart_pattern.finditer(buff)]

    predicates = {}
    if len(Starts) > 0:
        predicates["start"] = Starts
    if len(Etask) > 0:
        predicates["etask"] = Etask
    if len(Estart) > 0:
        predicates["estart"] = Estart

    return predicates

def parse_initial_solution(buff):
    # define regex patterns for necessary predicates
    start_pattern = re.compile(r'start\((\d+),\s(\d+)\)')
    total_dur_pattern = re.compile(r'total_dur\((\d+)\)')

    # parse the buff and create objects
    Starts = [
        Start(int(match.group(1)), int(match.group(2)))
            for match in start_pattern.finditer(buff)
    ]

    total_dur = [int(m.group(1)) for m in total_dur_pattern.finditer(buff)][0]

    predicates = {}
    if len(Starts) > 0:
        predicates["start"] = Starts
    if total_dur:
        predicates["total_dur"] = total_dur

    return predicates

def create_extra_stuff(preds):
    ## add dummies
    heads = set()
    for task in preds["tasks"]:
        found_pred = False
        for (pred, succ) in preds["psrels"]:
            if task == succ:
                found_pred = True
                break
        if not found_pred:
            heads.add(task)

    tails = set()
    for task in preds["tasks"]:
        found_succ = False
        for (pred, succ) in preds["psrels"]:
            if task == pred:
                found_succ = True
                break
        if not found_succ:
            tails.add(task)

    dummy_head_psrel = [(0, head) for head in heads]
    dummy_tail_psrel = [(tail, len(preds["tasks"]) + 1) for tail in tails]
    preds["psrels"] += dummy_head_psrel
    preds["psrels"] += dummy_tail_psrel

    preds["durs"][0] = 0
    preds["durs"][len(preds["tasks"]) + 1] = 0
    return preds

def create_aux_predicates(preds):
    buffa = f"\n%%%%% Extra predicates for auxiliary stuff\n"
    buffa += f"etask({len(preds['tasks']) + 1}).\n"
    buffa += f"task(0).\n"
    buffa += f"task({len(preds['tasks']) + 1}).\n"
    head, tail = 0, len(preds["tasks"]) + 1
    for pred, succ in preds["psrels"]:
        if pred == head:
            buffa += f"psrel({pred}, {succ}).\n"
        if succ == tail:
            buffa += f"psrel({pred}, {succ}).\n"

    buffa += f"dur(0, 0).\n"
    buffa += f"dur({len(preds['tasks']) + 1}, 0).\n"

    for j, t in preds["eis"].items():
        buffa += f"eis({j}, {t}).\n"
    for j, t in preds["lis"].items():
        buffa += f"lis({j}, {t}).\n"

    buffa += f"max_time({sum(preds['durs'].values())}).\n"
    buffa += f"step(0..{sum(preds['durs'].values())}).\n"
    buffa += f"level(0..{max(preds['limits'].values())}).\n"
    return buffa

def create_reqs_predicates(rcpsp):
    pass

def parse_solution_for_req1_in_asp(buff):
    punctual_candidate_pattern = re.compile(
        r'punctual_candidate\((\d+),(\d+)\)'
    )
    deadline_met_pattern = re.compile(r'deadline_met\(\"(\w+)\"\)')

    punctual_candidates = {
        int(match.group(1)): int(match.group(2))
            for match in punctual_candidate_pattern.finditer(buff)
    }
    deadline_mets = [
        str(match.group(1)) for match in deadline_met_pattern.finditer(buff)
    ]

    predicates = {}
    if len(punctual_candidates) > 0:
        predicates["punctual_candidate"] = punctual_candidates
    if len(deadline_mets) > 0:
        predicates["deadline_met"] = deadline_mets

    return predicates

def parse_solution_for_req2_in_asp(buff):
    # define regex patterns for necessary predicates
    start_pattern = re.compile(r'start\((\d+),(\d+)\)')
    etask_pattern = re.compile(r'etask\((\d+)\)')
    estart_pattern = re.compile(r'estart\((\d+)\)')
    excessed_pattern = re.compile(r'excessed\((\d+),(\d+)\)')
    excess_in_total_pattern = re.compile(r'excess_in_total\((\d+),(\d+)\)')

    # parse the buff and create objects
    Starts = [
        Start(int(match.group(1)), int(match.group(2)))
            for match in start_pattern.finditer(buff)
    ]

    Etask = [int(match.group(1)) for match in etask_pattern.finditer(buff)]

    Estart = [int(match.group(1)) for match in estart_pattern.finditer(buff)]

    ExcessTotal = {
        int(match.group(1)): int(match.group(2))
            for match in excess_in_total_pattern.finditer(buff)
    }

    predicates = {}
    if len(Starts) > 0:
        predicates["start"] = Starts
    if len(Etask) > 0:
        predicates["etask"] = Etask
    if len(Estart) > 0:
        predicates["estart"] = Estart
    if len(ExcessTotal) > 0:
        predicates["excess_in_total"] = ExcessTotal

    return predicates

def parse_solution_for_req3_in_asp(buff):
    current_delay_margin_pattern = re.compile(
        r'current_delay_margin\((\d+),(\d+)\)'
    )
    actual_delay_pattern = re.compile(r'actual_delay\((\d+),(\d+)\)')
    actual_tree_duration_pattern = re.compile(
        r'actual_tree_duration\((\d+),(\d+)\)'
    )
    min_tree_duration_pattern = re.compile(
        r'min_tree_duration\((\d+),(\d+)\)'
    )

    CurrentDelayMargins = {
        int(match.group(1)): int(match.group(2))
            for match in current_delay_margin_pattern.finditer(buff)
    }
    ActualDelays = {
        int(match.group(1)): int(match.group(2))
            for match in actual_delay_pattern.finditer(buff)
    }
    ActualTreeDurations = {
        int(match.group(1)): int(match.group(2))
            for match in actual_tree_duration_pattern.finditer(buff)
    }
    MinTreeDurations = {
        int(match.group(1)): int(match.group(2))
            for match in min_tree_duration_pattern.finditer(buff)
    }

    predicates = {}
    if len(CurrentDelayMargins) > 0:
        predicates["current_delay_margin"] = CurrentDelayMargins
    if len(ActualDelays) > 0:
        predicates["actual_delay"] = ActualDelays
    if len(ActualTreeDurations) > 0:
        predicates["actual_tree_duration"] = ActualTreeDurations
    if len(MinTreeDurations) > 0:
        predicates["min_tree_duration"] = MinTreeDurations

    return predicates

def parse_instance_for_req1(code_config, buff):
    deadline_pattern = re.compile(
        r'deadline\(\"(\w+)\",\s(\d+)\)'
    )
    code_config["deadline"] = {
        str(match.group(1)): int(match.group(2))
            for match in deadline_pattern.finditer(buff)
    }
    min_tree_dur_pattern = re.compile(
        r'min_tree_dur\(\"(\w+)\",\s(\d+)\)'
    )
    code_config["min_tree_dur"] = {
        str(match.group(1)): int(match.group(2))
            for match in min_tree_dur_pattern.finditer(buff)
    }

def parse_instance_for_req2(code_config, buff):
    pref_range_pattern = re.compile(
        r'preferable_range\((\d+),\s\"(\w+)\",\s(\d+),\s(\d+)\)'
    )
    code_config["pref_r"] = {
        int(match.group(1)): (int(match.group(3)), int(match.group(4)))
            for match in pref_range_pattern.finditer(buff)
    }
    code_config["prefr_obuff"] = ""
    for key, value in code_config["pref_r"].items():
        code_config["prefr_obuff"] += f"[{key}]:{value}, "

    code_config["req2_tr_tx"] = {
        int(match.group(1)): str(match.group(2))
            for match in pref_range_pattern.finditer(buff)
    }

def parse_instance_for_req3(code_config, buff):
    track_ext_pattern = re.compile(
        r'track_extension\((\d+),\s(\d+)\)'
    )
    code_config["track_exts"] = {
        int(match.group(1)): int(match.group(2))
            for match in track_ext_pattern.finditer(buff)
    }

    tree_ext_pattern = re.compile(
        r'tree_extension\((\d+),\s\"(\w+)\",\s(\d+)\)'
    )
    code_config["tree_exts"] = {
        int(match.group(1)): (str(match.group(2)), int(match.group(3)))
            for match in tree_ext_pattern.finditer(buff)
    }
    inst_id = code_config["inst_id"]
    if len(code_config["inst_tree_exts"][inst_id].keys()) == 0:
        for tr_id, (tidx, amount) in code_config["tree_exts"].items():
            code_config["inst_tree_exts"][inst_id][tr_id] = (tidx, amount)

    #print(f"code_config['inst_tree_exts']:\n{code_config['inst_tree_exts']}")
    #sys.exit()
    code_config["req3_tr_tx"] = {
        int(match.group(1)): str(match.group(2))
            for match in tree_ext_pattern.finditer(buff)
    }

    min_tree_dur_pattern = re.compile(
        r'min_tree_dur\(\"(\w+)\",\s(\d+)\)'
    )
    min_tree_dur_dict = {
        str(match.group(1)): int(match.group(2))
            for match in min_tree_dur_pattern.finditer(buff)
    }
    if "min_tree_dur" in code_config:
        code_config["min_tree_dur"] |= min_tree_dur_dict
    else:
        code_config["min_tree_dur"] = min_tree_dur_dict

