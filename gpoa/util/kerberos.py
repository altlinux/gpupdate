from .util import get_machine_name

import logging
import subprocess

def machine_kinit():
    '''
    Perform kinit with machine credentials
    '''
    host = get_machine_name()
    subprocess.call(['kinit', '-k', host])
    return check_krb_ticket()

def check_krb_ticket():
    '''
    Check if Kerberos 5 ticket present
    '''
    try:
        subprocess.check_call([ 'klist', '-s' ])
        output = subprocess.check_output('klist', stderr=subprocess.STDOUT).decode()
        logging.info(output)
    except:
        logging.error('Kerberos ticket check unsuccessful')
        return False
    logging.debug('Ticket check succeed')
    return True
