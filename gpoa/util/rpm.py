import rpm

def is_rpm_installed(rpm_name):
    '''
    Check if the package named 'rpm_name' is installed
    '''
    ts = rpm.TransactionSet()
    pm = ts.dbMatch()
    pm.pattern('name', rpm.RPMMIRE_GLOB, rpm_name)

    for pkg in pm:
        if pkg['name'] == rpm_name:
            return True

    return False

