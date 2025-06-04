import string
import random

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class Forest:
    def __init__(self, tasks_dict, tree_dict=None):
        self.ig_id = None
        #self.r3_max = -1
        self.rstar_max = -1
        self.tdict = tasks_dict
        self.trees = set()
        visited = set()
        while tree_dict is None and visited != set(self.tdict.keys()):
            new_tree = set()
            for tid in self.tdict.keys():
                if len(new_tree) == 0:
                    if tid in visited:
                        continue
                    new_tree.add(tid)
                    visited.add(tid)
                    task = self.tdict[tid]
                    new_tree |= set([s.tid for s in task.succ])
                    new_tree |= set([p.tid for p in task.pred])
                    continue
                if tid in new_tree:
                    visited.add(tid)
                    task = self.tdict[tid]
                    new_tree |= set([s.tid for s in task.succ])
                    new_tree |= set([p.tid for p in task.pred])
            self.trees.add(tuple(new_tree))

        if tree_dict is not None:
            self.trees = tree_dict

    def __repr__(self):
        m = ""
        for k, v in self.tdict.items():
            m += f"{k}: {v}\n"
        return m

    def get_tree(self, tid):
        for tree in self.trees:
            if tid in set(tree):
                return set(tree)
        raise (KeyError)
        return set()

    def reachable(self, tid1, tid2):
        # 1) they are in a same tree, and
        if not self.is_in_same_tree(tid1, tid2):
            return False

        # 2) tid2 is the direct or indirect successor of tid1
        visited = set() # for preventing cycling
        found = False
        queue = [s.tid for s in self.tdict[tid1].succ]
        while len(queue) > 0:
            sid = queue.pop(0)
            if sid == tid2:
                found = True
                break
            if sid in visited:
                continue
            visited.add(sid)
            queue += [s.tid for s in self.tdict[sid].succ]

        return found

    def is_in_same_tree(self, tid1, tid2):
        tree1 = self.get_tree(tid1)
        tree2 = self.get_tree(tid2)
        return tree1 == tree2

    def get_head_from(self, tid):
        tree = self.get_tree(tid)
        return self.get_head_of(tree)

    def get_head_of(self, tree):
        heads = set()
        for _tid in tree:
            task = self.tdict[_tid]
            if len(task.pred) == 0:
                heads.add(_tid)
        return heads

    def get_tail_from(sef, tid):
        tree = self.get_tree(tid)
        return self.get_tail_of(tree)

    def get_tail_of(self, tree):
        tails = set()
        for _tid in tree:
            task = self.tdict[_tid]
            if len(task.succ) == 0:
                tails.add(_tid)
        return tails

    def get_all_preds(self, tid):
        visited = set()
        preds = set()
        queue = [p.tid for p in self.tdict[tid].pred]
        while len(queue) > 0:
            pid = queue.pop(0)
            if pid in visited:
                continue
            visited.add(pid)
            preds.add(pid)
            queue += [pp.tid for pp in self.tdict[pid].pred]
        return preds

    def get_all_succs(self, tid):
        visited = set()
        succs = set()
        queue = [p.tid for p in self.tdict[tid].succ]
        while len(queue) > 0:
            pid = queue.pop(0)
            if pid in visited:
                continue
            visited.add(pid)
            succs.add(pid)
            queue += [pp.tid for pp in self.tdict[pid].succ]
        return succs 

    def get_preds(self, t):
        tid = t if t in self.tdict else t.tid
        return self.tdict[tid].pred

    def get_succs(self, t):
        tid = t if t in self.tdict else t.tid
        return self.tdict[tid].succ
