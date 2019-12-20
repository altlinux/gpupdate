import os
import pwd

def is_root():
    '''
    Check if current process has root permissions.
    '''
    if 0 == os.getuid():
        return True
    return False

def get_process_user():
    '''
    Get current process username.
    '''
    username = None

    uid = os.getuid()
    username = pwd.getpwuid(uid).pw_name

    return username

def username_match_uid(username):
    '''
    Check the passed username matches current process UID.
    '''
    uid = os.getuid()
    process_username = get_process_user()

    if process_username == username:
        return True

    return False

