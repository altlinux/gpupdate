import rpm

def is_rpm_installed(rpm_name):
    '''
    Check if the package named 'rpm_name' is installed
    '''
    ts = rpm.TransactionSet()
    pm = ts.dbMatch('name', rpm_name)

    if pm.count() > 0:
        return True

    return False

