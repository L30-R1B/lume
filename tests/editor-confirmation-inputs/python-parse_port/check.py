from logic import parse_port
import copy
args=copy.deepcopy(('1',))
before=copy.deepcopy(args)
assert parse_port(*args)==1
assert args==before
args=copy.deepcopy(('65535',))
before=copy.deepcopy(args)
assert parse_port(*args)==65535
assert args==before
args=copy.deepcopy(('8080',))
before=copy.deepcopy(args)
assert parse_port(*args)==8080
assert args==before
args=copy.deepcopy(('0',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
args=copy.deepcopy(('65536',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
args=copy.deepcopy(('-1',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
args=copy.deepcopy(('1x',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
args=copy.deepcopy(('',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
args=copy.deepcopy((' 80',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
args=copy.deepcopy(('１２',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
args=copy.deepcopy(('١٢',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
args=copy.deepcopy(('99999999999999999999999999',))
before=copy.deepcopy(args)
assert parse_port(*args)==None
assert args==before
