import logging

def set_loglevel(loglevel_num=None):
    '''
    Set the log level global value.
    '''
    loglevels = ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL']
    log_num = loglevel_num
    log_level = 10

    # A little bit of defensive programming
    if not log_num:
        log_num = 1
    if 0 > log_num:
        log_num = 0
    if 5 < log_num:
        log_num = 5

    log_level = 10 * log_num

    print('Setting log level to {}'.format(loglevels[log_num]))
    logging.getLogger().setLevel(log_level)

def process_target(target_name=None):
    '''
    The target may be 'All', 'Computer' or 'User'. This function
    determines which one was specified.
    '''
    target = 'All'

    if 'Computer' == target_name:
        target = 'Computer'

    if 'User' == target_name:
        target = 'User'

    logging.debug('Target is: {}'.format(target))

    return target

