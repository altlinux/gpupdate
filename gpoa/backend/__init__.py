import logging

from util.windows import smbcreds
from .samba_backend import samba_backend

def backend_factory(dc, username):
    '''
    Return one of backend objects
    '''
    sc = smbcreds(dc)
    domain = sc.get_domain()
    back = None

    try:
        back = samba_backend(sc, username, domain)
    except Exception as exc:
        logging.error('Unable to initialize Samba backend')

    return back

