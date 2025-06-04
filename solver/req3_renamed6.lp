tr_rel(TR, A) :- owner("req3", X), tree(X, A), tree_extension(TR, X, _).
tr_psrel(TR, A, B) :- psrel(A, B), tr_rel(TR, A), tr_rel(TR, B).
tr(TR) :- tr_rel(TR, _).

heads(TR, A) :- tr_rel(TR, A), 0 == #count {1: tr_psrel(TR, B, A)}.
tails(TR, A) :- tr_rel(TR, A), 0 == #count {1: tr_psrel(TR, A, B)}.

min_tree_duration(TR, I) :- tree_extension(TR, X, _), min_tree_dur(X, I).

actual_tree_duration(TR, I3):-
    I1 = #min {I: start(A, I), heads(TR, A)}, tr(TR),
    I2 = #max {I + D: start(B, I), dur(B, D), tails(TR, B)},
    I3 + I1 == I2, I1 < I2, step(I3).

actual_delay(TR, L3) :- 
    min_tree_duration(TR, L1), actual_tree_duration(TR, L2), 
    L3 + L1 == L2, L1 <= L2, delay_range(TR, L3).

:- 0 == #count {1: actual_delay(TR, L3)}.

within_range(TR, CD1) :-
    tree_extension(TR, _, L1), actual_delay(TR, L2), 
    L1 == L2 + CD1, delay_range(TR, CD1).

outside_range(TR, CD1) :-
    tree_extension(TR, _, L1), actual_delay(TR, L2),
    L1 + CD1 == L2, CD1 >= 1, delay_range(TR, CD1).

current_delay_margin(TR, CD2) :-
    outside_range(TR, CD1), delay_margin(TR, CD),
    CD1 + CD2 == CD, CD2 <= CD, CD1 <= CD, delay_range(TR, CD2).

current_delay_margin(TR, CD2) :-
    within_range(TR, CD1), delay_margin(TR, CD), 
    CD1 + CD == CD2, delay_range(TR, CD2).

:- tree_extension(TR, _, L1), actual_delay(TR, L2), 
    delay_margin(TR, L3), L2 - L3 > L1.

#show min_tree_duration/2.
#show actual_tree_duration/2.

#show actual_delay/2.
#show current_delay_margin/2.
#show within_range/2.
#show outside_range/2.
