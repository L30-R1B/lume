from logic import unique
import copy
args=copy.deepcopy(([3, 1, 3, 2, 1],))
before=copy.deepcopy(args)
assert unique(*args)==[3, 1, 2]
assert args==before
args=copy.deepcopy(([],))
before=copy.deepcopy(args)
assert unique(*args)==[]
assert args==before
args=copy.deepcopy(([-1, -1, 0],))
before=copy.deepcopy(args)
assert unique(*args)==[-1, 0]
assert args==before
