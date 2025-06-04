from instance import *
import instance as instance_core
from mass import *
import re
import os.path
import os
import errno
import sys
from random import randint, sample

from clingo import Control

def get_track_count(task_max_count, req_count = 3):
    track_count = (task_max_count // req_count) // req_count
    return track_count

def get_req_tree_count(track_count, req_count = 3):
    tree_count = track_count * req_count
    return tree_count

def parse_sol(buff):
    part_pattern = re.compile(r'part\((\d+),(\d+)\)')

    _parts = [
        (int(match.group(1)), int(match.group(2)))
            for match in part_pattern.finditer(buff)
    ]

    parts = [0] * len(_parts)
    for (i, p) in _parts:
        parts[i - 1] = p

    return parts

def generate_parts(gencfg, req_count = 3):
    task_max_count = gencfg['task_max_count']
    lb, hb = gencfg['low_bound'], gencfg['high_bound']

    track_count = get_track_count(task_max_count)
    tree_count = get_req_tree_count(track_count)

    base = f"bound({lb}..{hb}).\n"
    base += f"task_max({gencfg['task_max_count']}).\n"
    base += f"tree_index(1..{tree_count}).\n"
    base += f"extra({tree_count + 1}).\n\n"

    if task_max_count < 20:
        r_indices = sample(range(1, tree_count + 1), track_count)
        r_parts = []
        for index in r_indices:
            r_p = randint(lb, hb)
            r_parts.append((index, r_p))

        for (i, p) in r_parts:
            base += f"part({i}, {p}).\n\n"

        #print(f"  ==> {r_parts}")

    base += "1{part(I, P): bound(P)}1 :- tree_index(I).\n"
    base += "{part(I, P): bound(P)} :- extra(I).\n\n"
    base += ":- S1 = #sum {P, I:part(I, P)}, task_max(S2), S1 != S2.\n"
    base += ":- part(I1, P1), part(I2, P2), I1 == I2, P1 != P2.\n"
    base += "#show part/2."

    ctl = Control()
    ctl.add("base", [], base)
    _parts = []
    _parts.append(("base", []))
    ctl.ground(_parts)

    r_count = randint(1, 1000)
    ctl.configuration.solve.models = r_count

    with ctl.solve(yield_ = True) as ret:
        #print(f"# of models:{len(list(ret))}")
        models = list(ret)
        #model_num = len(list(ret))
        model_num = len(models)
        #model_index = min(r_count - 1, model_num - 1)
        if model_num < r_count:
            model_index = randint(1, model_num - 1)
        else:
            model_index = r_count - 1
        #print(f" => model_num:{model_num}, " + \
        #      f"r_count:{r_count}, model_index:{model_index}")
        #parts = parse_sol(f"{list(ret)[r_count - 1]}")
        #parts = parse_sol(f"{list(ret)[model_index]}")
        _parts = parse_sol(f"{models[model_index]}")

    cursor = 1
    parts = []
    for size_p in _parts:
        parts.append((cursor, cursor + size_p - 1))
        cursor += size_p
    return parts

if __name__ == "__main__":
    gencfg = instance_core.cfg

    gencfg['duration_max'] = 5
    gencfg['task_max_count'] = 20
    gencfg['resource_type_count'] = 4
    gencfg['resource_quarter'] = 2
    gencfg['amount_quarter'] = 5
    gencfg['low_bound'] = 2
    gencfg['high_bound'] = 5
    gencfg['r3_low'] = 20
    gencfg['r3_high'] = 30

    gencfg['inst_count_max'] = 3
    gencfg['igs'] = {}
    gencfg['forests'] = {}
    gencfg['owners'] = ['req1', 'req2', 'req3']
    for key in gencfg['owners']:
        gencfg[key] = []
    #gencfg['user1'] = []
    #gencfg['user2'] = []
    #gencfg['user3'] = []
    gencfg['remained'] = []

    gencfg['cmargin'] = 0
    gencfg['camount'] = 0

    #gencfg['id'] = id_generator()
    gencfg['ids'] = []
    gencfg['num_of_insts'] = 5
    gencfg['inst_id'] = "000000"
    gencfg['rstar'] = 1
    gencfg['timeout'] = 600

    for i in range(30):
        parts = generate_parts(gencfg)
        print(f"parts:{parts}")
        if i % 5 == 4:
            print("---- ----")
