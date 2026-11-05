from app import offset
assert offset(1,10)==0 and offset(4,20)==60
for page,size in ((0,10),(1,0),(1,101)):
    try: offset(page,size)
    except ValueError: pass
    else: raise AssertionError((page,size))
