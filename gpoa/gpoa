#! /usr/bin/env python3

import argparse
import logging
import os

from backend import backend_factory
from frontend.frontend_manager import frontend_manager, determine_username
from plugin import plugin_manager

from util.util import get_machine_name
from util.kerberos import machine_kinit
from util.users import (
    is_root,
    get_process_user
)
from util.arguments import (
    set_loglevel,
    process_target
)

def parse_arguments():
    arguments = argparse.ArgumentParser(description='Generate configuration out of parsed policies')
    arguments.add_argument('user',
        type=str,
        nargs='?',
        default=get_machine_name(),
        help='Domain username ({}) to parse policies for'.format(get_machine_name()))
    arguments.add_argument('--dc',
        type=str,
        help='FQDN of the domain to replicate SYSVOL from')
    arguments.add_argument('--nodomain',
        action='store_true',
        help='Operate without domain (apply local policy)')
    arguments.add_argument('--target',
        type=str,
        help='Specify if it is needed to update user\'s or computer\'s policies')
    arguments.add_argument('--noupdate',
        action='store_true',
        help='Don\'t try to update storage, only run appliers')
    arguments.add_argument('--noplugins',
        action='store_true',
        help='Don\'t start plugins')
    arguments.add_argument('--loglevel',
        type=int,
        default=0,
        help='Set logging verbosity level')
    return arguments.parse_args()

class gpoa_controller:
    __kinit_successful = False
    __args = None

    def __init__(self):
        self.__kinit_successful = machine_kinit()
        self.__args = parse_arguments()
        set_loglevel(self.__args.loglevel)

        uname = get_process_user()
        uid = os.getuid()
        logging.debug('The process was started for user {} with UID {}'.format(uname, uid))

        if not is_root():
            self.username = uname
        else:
            self.username = determine_username(self.__args.user)
        self.target = process_target(self.__args.target)

    def run(self):
        '''
        GPOA controller entry point
        '''
        self.start_backend()
        self.start_frontend()
        self.start_plugins()

    def start_backend(self):
        '''
        Function to start update of settings storage
        '''
        if not self.__args.noupdate:
            if is_root():
                back = backend_factory(self.__args.dc, self.username)
                if back:
                    back.retrieve_and_store()

    def start_frontend(self):
        '''
        Function to start appliers
        '''
        try:
            appl = frontend_manager(self.username, self.target)
            appl.apply_parameters()
        except Exception as exc:
            logging.error('Error occured while running applier: {}'.format(exc))

    def start_plugins(self):
        '''
        Function to start supplementary facilities
        '''
        if not self.__args.noplugins:
            pm = plugin_manager()
            pm.run()


def main():
    controller = gpoa_controller()
    controller.run()

if __name__ == "__main__":
    main()

