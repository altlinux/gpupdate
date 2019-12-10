from .samba_backend import samba_backend

def backend_factory(loadparm, creds, sid, dc, username):
    '''
    Return one of backend objects
    '''
    return samba_backend(loadparm, creds, sid, dc, username)

