from instance import *
import instance as instance_core
from instance import _var
from instance import shapes
from adding_reqs import *
from mass import *
from take_parts import generate_parts
from math import ceil, floor
import re
import os.path
import os
import errno
import sys
import json
from random import randint

def get_track_count(task_max_count, req_count = 3):
    track_count = (task_max_count // req_count) // req_count
    return track_count

def get_req_tree_count(track_count, req_count = 3):
    tree_count = track_count * req_count
    return tree_count

def generate_proper_subprojects(cfg, ids=False):
    total_count = cfg['task_max_count']
    low_bound = cfg['low_bound']
    high_bound = cfg['high_bound']

    parts = generate_parts(cfg)
    tasks, cursor, idx, tree_dict = [], 1, 1, {}
    for (lob, highb) in parts:
        t_type = highb - lob + 1
        t_shape = 1 if t_type == 2 else randint(1, _var[t_type])
        _tree = shapes[t_type][t_shape](cursor)
        tasks += _tree
        tree_dict[idx] = _tree
        cursor = highb + 1
        idx += 1

    #print(f"tasks:{tasks}")
    #print(f"parts:{parts}")
    #for i, task in enumerate(tasks):
    #    print(f"  i:{i+1:02d}, task:{task}")

    task_dict = {t.tid: t for t in tasks}
    if ids:
        return (task_dict, tree_dict)
    else:
        return task_dict

def calculate_rstar_bound(gencfg):
    task_max_count = gencfg['task_max_count']
    rtype_count = gencfg['resource_type_count']
    r_q = gencfg['resource_quarter']
    a_q = gencfg['amount_quarter']

    # low count: ((r_quarter/rtype_count) * task_max_count) * a_quarter * (1/3)
    rstar_low = floor(((r_q / rtype_count) * task_max_count) * a_q * (1/3))

    # high count:((r_quarter/rtype_count) * task_max_count) * a_quarter * (2/3)
    rstar_high = ceil(((r_q / rtype_count) * task_max_count) * a_q * (2/3))

    return (rstar_low, rstar_high)

def sample_trees_sorted_for_req1(forest, gencfg):
    tlist = []
    for tidx, tree in forest.trees.items():
        has_rstar = False
        for t in list(tree):
            if gencfg['rstar'] in forest.tdict[t.tid]:
                has_rstar = True
                break
        if has_rstar:
            tlist.append((len(tree), tidx))

    tlist.sort()
    assert len(tlist) >= 2, f"|tlist|:{len(tlist)}"

    return tlist

def sample_trees_sorted_for_req2(forest, gencfg):
    tlist = []
    for tidx, tree in forest.trees.items():
        cmargin = 0
        for t in list(tree):
            if gencfg['rstar'] in forest.tdict[t.tid]:
                amount = forest.tdict[t.tid].amount(gencfg['rstar'])
                margin = forest.rstar_max - amount
                cmargin += margin
        if cmargin > 0:
            tlist.append((cmargin, len(tree), tidx))

    tlist.sort(reverse = True)
    assert len(tlist) >= 2, f"|tlist|:{len(tlist)}"

    return [(len_t, tidx) for (_, len_t, tidx) in tlist]

def sample_trees_sorted_for_req3(forest, gencfg):
    tlist = []
    for tidx, tree in forest.trees.items():
        has_rstar = False
        for t in list(tree):
            if gencfg['rstar'] in forest.tdict[t.tid]:
                has_rstar = True
        if not has_rstar:
            tlist.append((len(tree), tidx))

    tlist.sort(reverse = True)
    assert len(tlist) >= 2, f"|tlist|:{len(tlist)}"

    return tlist

def calculate_cumulatives(gencfg, igs_id, user_id):
    cmargin = 0
    camount = 0
    for (ig_id, tidx) in igs_id[user_id]:
        tree = igs_id['forests'][ig_id].trees[tidx]
        forest = igs_id['forests'][ig_id]
        _margin = 0
        _amount = 0
        for t in list(tree):
            if gencfg['rstar'] in forest.tdict[t.tid]:
                amount = forest.tdict[t.tid].amount(gencfg['rstar'])
                margin = forest.rstar_max - amount
                cmargin += margin
                camount += amount
                _margin += margin
                _amount += amount
    igs_id['cmargin'] = cmargin
    igs_id['camount'] = camount

def generate_proper_req_instances(gencfg):
    gencfg['rstar_low'], gencfg['rstar_high'] = calculate_rstar_bound(gencfg)

    track_count = get_track_count(gencfg['task_max_count'])

    sample_tree_vectors = [
        sample_trees_sorted_for_req1,
        sample_trees_sorted_for_req2,
        sample_trees_sorted_for_req3
    ]

    #owners = ['user1', 'user2', 'user3']

    igs = {key: {} for key in gencfg['ids']}
    for id in igs.keys():
        igs[id]['igs'] = []
        igs[id]['forests'] = {}
        for req_id in gencfg['owners']:
            igs[id][req_id] = []
        #for user_id in owners:
        #    igs[id][user_id] = []
        igs[id]['remained'] = []
        igs[id]['cmargin'] = 0
        igs[id]['camount'] = 0

        #print(f"igs[{id}].keys():{igs[id].keys()}")

        while len(igs[id]['igs']) < gencfg['inst_count_max']:
            ig, tree_dict = generate_proper_subprojects(gencfg, ids=True)

            rstar_amount = 0
            rstar_max = -1
            for tid, t in ig.items():
                if gencfg['rstar'] in t:
                    rstar_amount += t.amount(gencfg['rstar'])
                    rstar_max = max(rstar_max, t.amount(gencfg['rstar']))

            if rstar_max == -1:
                # This means that no tree has the rstar resource in its tasks.
                continue

            if gencfg['rstar_low'] <= rstar_amount <= gencfg['rstar_high']:
                len_igs = len(igs[id]['igs'])
                ig_id = f'ig{len_igs:0{2 + gencfg["inst_count_max"] // 16}x}'

                forest = Forest(ig, tree_dict)
                forest.ig_id = ig_id
                forest.rstar_max = rstar_max

                visited = set()
                error_occured = False
                req_tree_dict = {j:[] for j in range(len(sample_tree_vectors))}
                for tidx, sample_trees_fc in enumerate(sample_tree_vectors):
                    try:
                        tlist = sample_trees_fc(forest, gencfg)
                    except AssertionError:
                        error_occured = True
                        break

                    added_tree_count = len(visited)
                    while len(visited) < added_tree_count + track_count:
                        try:
                            _, tree = tlist.pop(0)
                        except IndexError:
                            error_occured = True
                            break
                        except ValueError:
                            print(f"tlist:{tlist}")
                            raise ValueError
                        if tree not in visited:
                            req_tree_dict[tidx].append(tree)
                            visited.add(tree)

                    if error_occured:
                        break

                if not error_occured:
                    igs[id]['igs'].append((ig_id, ig))
                    igs[id]['forests'][forest.ig_id] = forest
                    covered = set()

                    #for uidx, user in enumerate(owners):
                    for uidx, user in enumerate(gencfg["owners"]):
                        for tree in req_tree_dict[uidx]:
                            igs[id][user].append((ig_id, tree))
                            covered.add(tree)

                    for tree in set(forest.trees.keys()) - covered:
                        igs[id]['remained'].append((ig_id, tree))

        #calculate_cumulatives(gencfg, igs[id], 'user2')
        calculate_cumulatives(gencfg, igs[id], 'req2')
    gencfg['igs'] = igs

if __name__ == "__main__":
    gencfg = instance_core.cfg

    gencfg['duration_max'] = 5
    gencfg['task_max_count'] = 20
    gencfg['resource_type_count'] = 4
    gencfg['resource_quarter'] = 2
    gencfg['amount_quarter'] = 5
    gencfg['low_bound'] = 2
    gencfg['high_bound'] = 5

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

    for _ in range(gencfg['num_of_insts']):
        while True:
            new_id = id_generator()
            if new_id not in gencfg['ids']:
                gencfg['ids'].append(new_id)
                break

    generate_proper_req_instances(gencfg)

    print(f"{gencfg['igs'].keys()}")
    for key, value in gencfg['igs'].items():
        print(f"key:{key}")
        for key2, value2 in value.items():
            print(f"  key2:{key2}")
            print(f"  value2:{value2}")
            print(f"---- ---- ---- ----")
        print(f"==== ==== ==== ====")
