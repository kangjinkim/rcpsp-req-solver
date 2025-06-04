from itertools import product
from pulp import *

class RCPSP:
    def __init__(self, timeout=0):
        self.prob = LpProblem("RCPSP", LpMinimize)
        self.x = None
        self.max_time = -1
        self.etask = -1
        self.solver = PULP_CBC_CMD(
            mip=True,
            msg=False,
            timeLimit=None if timeout == 0 else timeout
        )
        self.status = None

    def setup_instance(self):
        self.n = len(self.predicates["tasks"])
        self.J = range(len(self.predicates["durs"]))
        #self.R = range(len(self.predicates["limits"]))
        self.R = range(max(self.predicates["limits"]) + 1)
        self.T = range(sum(self.predicates["durs"].values()))
        self.p = [self.predicates["durs"][j] for j in self.J]
        self.u = {j:[] for j in self.J}
        #print(f"self.R:{self.R}")
        for j in self.J:
            resources = [0 for _ in self.R]
            #print(f"  resources:{resources}")
            if j in self.predicates["rsreqs"]:
                #print(f"  j:{j}")
                for (r2, k2) in self.predicates["rsreqs"][j].items():
                    #print(f"    (r2:{r2}, k2:{k2})")
                    resources[r2] = k2
            self.u[j] = resources

        self.S = self.predicates["psrels"]  # We already added psrel from _aux.
        #self.c = [self.predicates["limits"][r] for r in self.R]
        self.c = [
            self.predicates["limits"][r] if r in self.predicates["limits"]
            else 0
                for r in self.R
        ]

    def set_objective(self):
        self.x = LpVariable.dicts(
            "X",
            [(j, t) for j in self.J for t in self.T],
            lowBound=0,
            upBound=1,
            cat='Binary'
        )
        self.prob += lpSum(t * self.x[(self.n + 1, t)] for t in self.T)

    def set_constraints(self):
        for j in self.J:
            self.prob += lpSum(self.x[(j, t)] for t in self.T) == 1

        for (r, t) in product(self.R, self.T):
            self.prob += lpSum(
                self.u[j][r] * self.x[(j, t2)]
                    for j in self.J
                        for t2 in range(max(0, t - self.p[j] + 1), t + 1)
            ) <= self.c[r]

        for (j, s) in self.S:
            self.prob += lpSum(
                t * self.x[(s, t)] - t * self.x[(j, t)] for t in self.T
            ) >= self.p[j]

    def solve(self):
        self.status = self.prob.solve(self.solver)

    def convert_sol_to_asp_form(self):
        buff = ""
        for (j, t) in product(self.J, self.T):
            x_v = value(self.x[(j, t)])
            if value(self.x[(j, t)]) != 0:
                buff += f"start({j}, {t}).\n"
        total_dur = value(self.prob.objective)
        buff += f"total_dur({int(total_dur)}).\n"

        return buff
