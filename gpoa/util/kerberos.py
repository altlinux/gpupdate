import logging
import subprocess

from .util import get_machine_name
from .logging import slogm

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
    result = False
    try:
        subprocess.check_call([ 'klist', '-s' ])
        output = subprocess.check_output('klist', stderr=subprocess.STDOUT).decode()
        logging.info(output)
        result = True
    except:
        logging.error(slogm('Kerberos ticket check unsuccessful'))

    logging.debug(slogm('Ticket check succeed'))

    return result
