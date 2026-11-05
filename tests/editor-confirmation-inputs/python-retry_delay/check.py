from logic import retry_delay
import copy
args=copy.deepcopy((0, 2, 100))
before=copy.deepcopy(args)
assert retry_delay(*args)==2
assert args==before
args=copy.deepcopy((3, 2, 100))
before=copy.deepcopy(args)
assert retry_delay(*args)==16
assert args==before
args=copy.deepcopy((60, 10, 1000))
before=copy.deepcopy(args)
assert retry_delay(*args)==1000
assert args==before
args=copy.deepcopy((20, 0, 100))
before=copy.deepcopy(args)
assert retry_delay(*args)==0
assert args==before
args=copy.deepcopy((2, 3, 0))
before=copy.deepcopy(args)
assert retry_delay(*args)==0
assert args==before
