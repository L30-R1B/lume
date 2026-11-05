from logic import merge_intervals
import copy
args=copy.deepcopy(([[4, 5], [1, 3], [2, 4]],))
before=copy.deepcopy(args)
assert merge_intervals(*args)==[[1, 5]]
assert args==before
args=copy.deepcopy(([[1, 2], [4, 6]],))
before=copy.deepcopy(args)
assert merge_intervals(*args)==[[1, 2], [4, 6]]
assert args==before
args=copy.deepcopy(([[-3, -1], [-1, 0]],))
before=copy.deepcopy(args)
assert merge_intervals(*args)==[[-3, 0]]
assert args==before
args=copy.deepcopy(([],))
before=copy.deepcopy(args)
assert merge_intervals(*args)==[]
assert args==before
