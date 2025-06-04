punctual_candidate(A, I2) :-
    task(A), tree(X, A), owner("req1", X), start(A, I2),
    0 == #count {1: psrel(A, B), tree(X, B)}.

:- punctual_candidate(A, I2), deadline(X, I), dur(A, I1),
    tree(X, A), I2 > I - I1, step(I2).

:- deadline(X, I1), min_tree_dur(X, I2), I1 < I2.

deadline_met(X) :-
    punctual_candidate(A, I2), deadline(X, I),
    tree(X, A), I2 == I - I1, dur(A, I1).

:- C1 = #count {1, X: deadline(X, _)}, C1 != C2,
    C2 = #count {1, X: deadline_met(X)}.

#show punctual_candidate/2.
#show deadline_met/1.
