#! /usr/bin/env python3

import argparse

# Our native control facility
import util
from backend import backend_factory
import frontend
from plugin import plugin_manager

# Remove print() from code
import logging
logging.basicConfig(level=logging.DEBUG)

def parse_arguments():
    arguments = argparse.ArgumentParser(description='Generate configuration out of parsed policies')
    arguments.add_argument('user',
        type=str,
        nargs='?',
        default=util.get_machine_name(),
        help='Domain username ({}) to parse policies for'.format(util.get_machine_name()))
    arguments.add_argument('--dc',
        type=str,
        help='FQDN of the domain to replicate SYSVOL from')
    arguments.add_argument('--nodomain',
        action='store_true',
        help='Operate without domain (apply local policy)')
    return arguments.parse_args()

class gpoa_controller:
    __kinit_successful = False
    __args = None

    def __init__(self):
        self.__kinit_successful = util.machine_kinit()
        self.__args = parse_arguments()

        username = self.__args.user

        back = backend_factory(self.__args.dc, username)
        if back:
            back.retrieve_and_store()

        appl = frontend.applier(username)
        appl.apply_parameters()

        pm = plugin_manager()
        pm.run()

def main():
    controller = gpoa_controller()

if __name__ == "__main__":
    main()

