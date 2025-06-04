excessed(A, 0) :- task(A), tree(X, A), not owner("req2", X).
excessed(A, 0) :- 
    task(A), tree(X, A), owner("req2", X), 
    0 == #count {L: rsreq(A, rstar, L)}.

overassignable(A) :-
    task(A), tree(X, A), owner("req2", X), rsreq(A, rstar, L1),
    limit(rstar, L2), L1 <= L2.

1 { excessed(A, L1): level(L1)} 1 :- 
    overassignable(A), tree(X, A), owner("req2", X).
:- excessed(A, L1), rsreq(A, rstar, L2), limit(1, L3), L1 + L2 > L3.

:- preferable_range(I, X, LB, HB), AM < LB, excess_in_total(I, AM).
:- preferable_range(I, X, LB, HB), HB < AM, excess_in_total(I, AM).

assigned_res(TS, A, rstar, AM) :-
    step(TS), overassignable(A), excessed(A, L1), dur(A, AD), start(A, TS1),
    TS1 <= TS < TS1 + AD, rsreq(A, rstar, L2), AM = L1 + L2.

assigned_res(TS, A, rstar, L2) :-
    step(TS), not overassignable(A), task(A), dur(A, AD), start(A, TS1),
    TS1 <= TS < TS1 + AD, rsreq(A, rstar, L2).

assigned_res(TS, A, R, L2) :-
    step(TS), task(A), dur(A, AD), start(A, TS1), TS1 <= TS < TS1 + AD,
    rsreq(A, R, L2), R != rstar.

excess_in_total(I, AM) :-
    preferable_range(I, X, LB, HB), 
    AM = #sum {L, A: excessed(A, L), tree(X, A)}.

#show overassignable/1.
#show excessed/2.
#show excess_in_total/2.
