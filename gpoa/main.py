#! /usr/bin/env python3

import argparse

# Facility to determine GPTs for user
import optparse
from samba import getopt as options

# Our native control facility
import util
from backend import backend_factory
import frontend

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
    __parser = optparse.OptionParser('GPO Applier')
    __args = None
    __sambaopts = options.SambaOptions(__parser)
    __credopts = options.CredentialsOptions(__parser)
    # Initialize loadparm context
    __lp = __sambaopts.get_loadparm()
    __creds = __credopts.get_credentials(__lp, fallback_machine=True)

    def __init__(self):
        self.__kinit_successful = util.machine_kinit()
        self.__args = parse_arguments()

        # Determine the default Samba DC for replication and try
        # to overwrite it with user setting.
        dc = util.select_dc(self.__lp, self.__creds, self.__args.dc)

        username = self.__args.user
        domain = util.get_domain_name(self.__lp, self.__creds, dc)

        sid = util.get_sid(domain, username)

        back = backend_factory(self.__lp, self.__creds, sid, dc, username)
        back.retrieve_and_store()

        appl = frontend.applier(sid, username)
        appl.apply_parameters()

def main():
    logging.info('Working with Samba DC')
    controller = gpoa_controller()

if __name__ == "__main__":
    main()

