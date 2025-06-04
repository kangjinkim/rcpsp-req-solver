1 {start(A, I):step(I)} 1 :- task(A).

:- psrel(P, S), dur(P, D1), start(P, I1), start(S, I2), I2 < I1 + D1.

%assigned_res(TS, A, R, AM) :- 
%    step(TS), task(A), rsreq(A, R, AM), dur(A, AD), start(A, TS1), 
%    TS1 <= TS < TS1 + AD.

sum_assigned_res(TS, R, AM) :- step(TS), limit(R, _), 
    AM = #sum {AM1, A: assigned_res(TS, A, R, AM1)}.

:- sum_assigned_res(TS, R, AM), step(TS), limit(R, L), AM > L.
:- sum_assigned_res(TS, R, AM1), AM2 = #sum {AM: assigned_res(TS, A, R, AM), 
    task(A)}, AM1 < AM2.

estart(I) :- start(A, I), etask(A).

#minimize {I : estart(I)}.

#show start/2.

#show etask/1.
#show estart/1.
#show sum_assigned_res/3.
#show assigned_res/4.
