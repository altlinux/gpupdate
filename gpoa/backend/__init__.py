import logging

from util.windows import smbcreds
from .samba_backend import samba_backend

def backend_factory(dc, username):
    '''
    Return one of backend objects. Please note that backends must
    store their configuration in a storage with administrator
    write permissions in order to prevent users from modifying
    policies enforced by domain administrators.
    '''
    sc = smbcreds(dc)
    domain = sc.get_domain()
    back = None

    try:
        back = samba_backend(sc, username, domain)
    except Exception as exc:
        logging.error('Unable to initialize Samba backend: {}'.format(exc))

    return back

