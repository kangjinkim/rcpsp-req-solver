
def calculate_eis(psrel, dur):
    # NOTE: It works for a dummy task (having 0 duration) in the head, coming
    #    with its psrel (predecessor-successor relation).
    # Forward Pass
    eis = {}        # Earlist Start Times for each task
    visited = set()

    snodes = set()
    for (p1, s1) in psrel:
        found = False
        for (p2, s2) in psrel:
            if p1 == s2:
                found = True
                break
        if not found:
            snodes.add(p1)

    for snode in snodes:
        #eis[snode] = 1
        eis[snode] = 0      # The earlist time step starts from step 0.
    stack = [(p, s) for (p, s) in psrel if p in snodes]

    while len(stack) > 0:
        (p, s) = stack.pop(-1)
        #if (p, s) in visited:
        #    continue
        #visited.add((p, s))
        if s not in eis:
            eis[s] = eis[p] + dur[p]
        else:
            eis[s] = max(eis[s], eis[p] + dur[p])
        for (p2, s2) in psrel:
            if s == p2:
            #if s == p2 and (p2, s2) not in visited:
                stack.append((p2, s2))
    return eis

def calculate_lis(psrel, dur):
    # NOTE: It works for a dummy task (having 0 duration in the tail, coming
    #    with its psrel (predecessor-successor relation).
    # Backward Pass
    lis = {}    # Latest Start Times for each task
    #total_dur = sum(dur.values()) + 2
    total_dur = sum(dur.values())
    visited = set()
    enodes = set()

    for (p1, s1) in psrel:
        found = False
        for (p2, s2) in psrel:
            if s1 == p2:
                found = True
                break
        if not found:
            enodes.add(s1)
    for enode in enodes:
        lis[enode] = total_dur - dur[enode]
    stack = [(p, s) for (p, s) in psrel if s in enodes]

    while len(stack) > 0:
        (p, s) = stack.pop(-1)
        if (p, s) in visited:
            continue
        #visited.add((p, s))
        if p not in lis:
            lis[p] = lis[s] - dur[p]
        else:
            lis[p] = min(lis[p], lis[s] - dur[p])
        for (p2, s2) in psrel:
            if p == s2:
            #if p == s2 and (p2, s2) not in visited:
                stack.append((p2, s2))
    return lis
