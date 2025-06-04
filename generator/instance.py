from random import randint
from random import random
from random import sample
from random import randrange
from math import ceil, floor

class task:
    def __init__(self, tid, dur, rdict):
        self.tid = tid
        self.dur = dur
        self.succ = set()
        self.pred = set()
        self.resources = rdict

    def __repr__(self):
        p = f"T({self.tid:04d}, "
        p += f"{self.dur:02d}, "
        p += f"{self.resources}, "
        p += f"pred:["
        for i, p_task in enumerate(list(self.pred)):
            if i == len(self.pred) - 1:
                p += f"{p_task.tid}"
            else:
                p += f"{p_task.tid}, "
        p += f"], "
        p += f"succ:["
        for i, s_task in enumerate(list(self.succ)):
            if i == len(self.succ) - 1:
                p += f"{s_task.tid}"
            else:
                p += f"{s_task.tid}, "
        p += f"])"
        return p

    def __iter__(self):
        return self

    def __hash__(self):
        return hash(self.tid)

    def __contains__(self, resource):
        return resource in self.resources

    def amount(self, resource):
        assert resource in self.resources

        return self.resources[resource]

    def rtypes(self):
        return set(self.resources.keys())


def get_duration():
    global cfg

    return randint(1, cfg['duration_max'])

def get_resource_amount_pairs():
    global cfg

    resource_count = randint(1, cfg['resource_quarter'])
    rdict = {}
    while len(rdict) < resource_count:
        rtype = randint(0, cfg['resource_type_count'])
        ramount = randint(1, cfg['amount_quarter'])
        rdict[rtype] = ramount
    return rdict

def convert_to_asp_form(g):
    buf = f"%%%%%% Total {len(g)} tasks %%%%%%\n"
    for task in g.values():
        buf += f"task({task.tid}).\n"
    buf += f"\n"
    for task in g.values():
        buf += f"dur({task.tid}, {task.dur}).\n"
    buf += f"\n"
    for task in g.values():
        for succ in task.pred:
            buf += f"psrel({task.tid}, {succ.tid}).\n"
    buf += f"\n"
    resource_limits = {}
    for task in g.values():
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

    return buf

def partition(total_count, low_bound, high_bound):
    low_count = total_count // low_bound
    high_count = total_count // high_bound
    sampled = []
    found = False
    while True:
        sampled = []
        for j in range(high_count, low_count + 1):
            sampled.append(randint(low_bound, high_bound))
            if sum(sampled) == total_count:
                found = True
                break
            elif sum(sampled) > total_count:
                break
        if found:
            break

    cursor = 1
    parts = []
    for size_p in sampled:
        parts.append((cursor, cursor + size_p - 1))
        cursor += size_p
    return parts

def gen_tasks(cursor, count):
    task_list = []
    for i in range(cursor, cursor + count):
        dur = get_duration()
        rdict = get_resource_amount_pairs()
        task_list.append(task(i, dur, rdict))
    return task_list

def connect(t1, t2):
    t1.succ.add(t2)
    t2.pred.add(t1)

def shape_2_1(cursor):
    global cfg

    (t1, t2) = gen_tasks(cursor, 2)
    connect(t1, t2)

    return [t1, t2]

def shape_3_1(cursor):
    global cfg

    (t1, t2, t3) = gen_tasks(cursor, 3)
    connect(t1, t3)
    connect(t2, t3)

    return [t1, t2, t3]

def shape_3_2(cursor):
    global cfg

    (t1, t2, t3) = gen_tasks(cursor, 3)
    connect(t1, t2)
    connect(t1, t3)

    return [t1, t2, t3]

def shape_3_3(cursor):
    global cfg

    (t1, t2, t3) = gen_tasks(cursor, 3)
    connect(t1, t2)
    connect(t2, t3)

    return [t1, t2, t3]

def shape_4_1(cursor):
    global cfg

    (t1, t2, t3, t4) = gen_tasks(cursor, 4)
    connect(t1, t3)
    connect(t2, t3)
    connect(t3, t4)

    return [t1, t2, t3, t4]

def shape_4_2(cursor):
    global cfg

    (t1, t2, t3, t4) = gen_tasks(cursor, 4)
    connect(t1, t2)
    connect(t2, t3)
    connect(t2, t4)

    return [t1, t2, t3, t4]

def shape_4_3(cursor):
    global cfg

    (t1, t2, t3, t4) = gen_tasks(cursor, 4)
    connect(t1, t2)
    connect(t1, t3)
    connect(t3, t4)

    return [t1, t2, t3, t4]

def shape_4_4(cursor):
    global cfg

    (t1, t2, t3, t4) = gen_tasks(cursor, 4)
    connect(t1, t2)
    connect(t2, t3)
    connect(t4, t3)

    return [t1, t2, t3, t4]

def shape_4_5(cursor):
    global cfg

    (t1, t2, t3, t4) = gen_tasks(cursor, 4)
    connect(t1, t2)
    connect(t2, t3)
    connect(t3, t4)

    return [t1, t2, t3, t4]

def shape_5_1(cursor):
    global cfg

    (t1, t2, t3, t4, t5) = gen_tasks(cursor, 5)
    connect(t1, t3)
    connect(t2, t3)
    connect(t3, t4)
    connect(t4, t5)

    return [t1, t2, t3, t4, t5]

def shape_5_2(cursor):
    global cfg

    (t1, t2, t3, t4, t5) = gen_tasks(cursor, 5)
    connect(t1, t2)
    connect(t2, t3)
    connect(t3, t4)
    connect(t3, t5)

    return [t1, t2, t3, t4, t5]


def shape_5_3(cursor):
    global cfg

    (t1, t2, t3, t4, t5) = gen_tasks(cursor, 5)
    connect(t1, t2)
    connect(t1, t3)
    connect(t3, t4)
    connect(t4, t5)

    return [t1, t2, t3, t4, t5]


def shape_5_4(cursor):
    global cfg

    (t1, t2, t3, t4, t5) = gen_tasks(cursor, 5)
    connect(t1, t2)
    connect(t2, t3)
    connect(t3, t4)
    connect(t5, t4)

    return [t1, t2, t3, t4, t5]


def shape_5_5(cursor):
    global cfg

    (t1, t2, t3, t4, t5) = gen_tasks(cursor, 5)
    connect(t1, t2)
    connect(t2, t3)
    connect(t2, t4)
    connect(t3, t5)

    return [t1, t2, t3, t4, t5]


def shape_5_6(cursor):
    global cfg

    (t1, t2, t3, t4, t5) = gen_tasks(cursor, 5)
    connect(t1, t2)
    connect(t2, t3)
    connect(t4, t3)
    connect(t3, t5)

    return [t1, t2, t3, t4, t5]


def shape_5_7(cursor):
    global cfg

    (t1, t2, t3, t4, t5) = gen_tasks(cursor, 5)
    connect(t1, t2)
    connect(t2, t3)
    connect(t3, t4)
    connect(t4, t5)

    return [t1, t2, t3, t4, t5]

def generate_subprojects(cfg, ids=False):
    global _var, shape

    total_count = cfg['task_max_count']
    low_bound = cfg['low_bound']
    high_bound = cfg['high_bound']

    parts = partition(total_count, low_bound, high_bound)
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

    task_dict = {t.tid: t for t in tasks}
    if ids:
        return (task_dict, tree_dict)
    else:
        return task_dict

_var = {2:1, 3:3, 4:5, 5:7}
shapes = {
    2: {1: shape_2_1}, \
    3: {1: shape_3_1, 2: shape_3_2, 3: shape_3_3}, \
    4: {1: shape_4_1, 2: shape_4_2, 3: shape_4_3, 4: shape_4_4, 5: shape_4_5},\
    5: {1: shape_5_1, 2: shape_5_2, 3: shape_5_3, 4: shape_5_4, 5: shape_5_5, \
        6: shape_5_6, 7: shape_5_7}
}

cfg = {}

if __name__ == "__main__":
    cfg['duration_max'] = 5
    cfg['task_max_count'] = 20
    cfg['resource_type_count'] = 3
    cfg['resource_quarter'] = 2
    cfg['amount_quarter'] = 3
    cfg['div_base'] = 10
    cfg['low_bound'] = 2
    cfg['high_bound'] = 5

    ig = generate_subprojects(cfg)
    for tid, task in ig.items():
        print(f"tid:{tid:04}, task:{task}")
    buf = convert_to_asp_form(ig)
    print(f"{buf}")
