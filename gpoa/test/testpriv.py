#! /usr/bin/env python3

from gpoa.util.users import with_privileges
from gpoa.util.arguments import set_loglevel

def test_fn():
    with open('testfile', 'w') as f:
        f.write('test')

def main():
    set_loglevel(1)
    with_privileges('test', test_fn)

if '__main__' == __name__:
    main()

