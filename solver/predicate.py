
class Predicate:
    def __init__(self, name):
        self.name = name
        self.tid = 0
        self.tstep = 0
        self.ti = 0
        self.tj = 0
        self.ri = 0
        self.ai = 0

    def __repr__(self):
        m = f"{self.name}({self.tid},{self.tstep},{self.ti},{self.tj})"
        return m

class Start(Predicate):
    def __init__(self, task_id, timestep):
        self.name = "start"
        self.tid = task_id
        self.tstep = timestep

    def __repr__(self):
        m = f"{self.name}({self.tid}, {self.tstep})"
        return m

