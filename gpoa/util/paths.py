import pathlib


def default_policy_path():
    '''
    Returns path pointing to Default Policy directory.
    '''
    return pathlib.Path('/usr/share/local-policy/default')


def cache_dir():
    '''
    Returns path pointing to gpupdate's cache directory
    '''
    cachedir = pathlib.Path('/var/cache/gpupdate')

    if not cachedir.exists():
        cachedir.mkdir(parents=True, exist_ok=True)

    return cachedir


def local_policy_cache():
    '''
    Returns path to directory where lies local policy settings cache
    transformed into GPT.
    '''
    lpcache = pathlib.Path.joinpath(cache_dir(), 'local-policy')

    if not lpcache.exists():
        lpcache.mkdir(parents=True, exist_ok=True)

    return lpcache

