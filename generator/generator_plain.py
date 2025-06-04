from instance import *
import instance as instance_core
from mass import *
import os.path
import os
import errno
import sys
import time
import json

sys.path.append('../solver')
from asp_form import load_file
from asp_form import parse_inst_predicates
from asp_form import create_extra_stuff
from asp_form import create_aux_predicates
from preprocess import calculate_eis, calculate_lis

def create_dir(dir_name):
    if os.path.exists(dir_name):
        pass
    else:
        try:
            os.mkdir(dir_name)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                print(f"Failed to create {dir_name}.")
            raise OSError

def get_default_gencfg():
    gencfg = instance_core.cfg
    gencfg['duration_max'] = 5
    gencfg['task_max_count'] = 20
    #gencfg['task_max_count'] = 40
    gencfg['resource_type_count'] = 4
    gencfg['resource_quarter'] = 2
    #gencfg['amount_quarter'] = 3
    gencfg['amount_quarter'] = 5
    gencfg['low_bound'] = 2
    gencfg['high_bound'] = 5

    gencfg['inst_count_max'] = 1
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
    gencfg['timeout'] = 600 # ten minutes

    return gencfg

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
    #print(f"{new_inst_id}")

    new_inst_id_dir = inst_dir + "/" + f"{new_inst_id}"
    create_dir(new_inst_id_dir)
    inst_list[new_inst_id] = (0, 0)

    # generate a config file for generating instances of ASP
    # gencfg.py

    # file exists?
    gencfg_file = "../gencfg.json"
    if os.path.exists(gencfg_file):
        #print(f"{gencfg_file} exists!")
        # then load the gencfg file
        with open(gencfg_file) as f:
            _gencfg = json.load(f)
        # TODO: Replace the previously assigend inst_id with a new one
        gencfg = instance_core.cfg
        for key, value in _gencfg.items():
            gencfg[key] = value
        gencfg['ids'] = []
    else:
        # then generate the gencfg file
        #print(f"{gencfg_file} doesn't exist!")
        gencfg = get_default_gencfg()
        # TODO: Replace the None value of the inst_id with a new one
    gencfg['inst_id'] = new_inst_id
    inst_list[new_inst_id] = (gencfg['num_of_insts'], gencfg['task_max_count'])

    # generate ids for num_of_insts
    for _ in range(gencfg['num_of_insts']):
        while True:
            new_id = id_generator()
            if new_id not in gencfg['ids']:
                gencfg['ids'].append(new_id)
                break

    idth = 0
    igs = {key: {} for key in gencfg['ids']}
    for id in igs.keys():
        igs[id]['igs'] = []
        ig = generate_subprojects(gencfg)
        _inst = convert_to_asp_form(ig)
        len_igs = len(igs[id]['igs'])
        ig_id = f'ig{len_igs:0{2 + gencfg["inst_count_max"] // 16}x}'
        igs[id]['igs'].append((ig_id, ig))

        base = f"{new_inst_id_dir}/{id}_{ig_id}"
        inst_file = f"{base}_inst.lp"
        aux_file = f"{base}_aux.lp"

        with open(inst_file, 'w') as f:
            f.writelines(_inst)

        _inst = load_file(inst_file)
        preds = parse_inst_predicates(_inst)
        preds = create_extra_stuff(preds)
        preds["eis"] = calculate_eis(preds["psrels"], preds["durs"])
        preds["lis"] = calculate_lis(preds["psrels"], preds["durs"])
        _aux = create_aux_predicates(preds)

        # write aux
        with open(aux_file, 'w') as f:
            f.writelines(_aux)

        print( \
              f"{idth:04d} " + \
              f"Instance \"{base}\", " + \
              f"for {len(ig.values())} tasks" \
        )

        idth += 1

    gencfg['igs'] = igs

    # write the gencfg to the sub-folder
    gencfg_file_new = new_inst_id_dir + "/" + f"{gencfg_file[2:]}"

    _gencfg = {}
    _gencfg = gencfg.copy()
    for id in _gencfg['igs'].keys():
        (ig_id, ig) = _gencfg['igs'][id]['igs'][0]
        _gencfg['igs'][id]['ig_id'] = ig_id

        del _gencfg['igs'][id]['igs']

    with open(gencfg_file_new, 'w') as f:
        json.dump(_gencfg, f, indent=4, sort_keys=True)

    # add the gencfg to the current folder
    with open(gencfg_file, 'w') as f:
        json.dump(_gencfg, f, indent=4, sort_keys=True)

    with open(inst_list_file, 'w') as f:
        json.dump(inst_list, f, indent=4, sort_keys=True)
