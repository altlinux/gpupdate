import logging

from util.windows import smbcreds
from .samba_backend import samba_backend

def backend_factory(dc, username):
    '''
    Return one of backend objects
    '''
    sc = smbcreds()
    result_dc = sc.select_dc(dc)
    domain = sc.get_domain(result_dc)
    back = None

    try:
        back = samba_backend(sc, result_dc, username, domain)
    except Exception as exc:
        logging.error('Unable to initialize Samba backend')

    return back

