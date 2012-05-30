import os

def find_base():
    if 'DUKE_DEPLOY_BASE' in os.environ:
        return os.environ['DUKE_DEPLOY_BASE']
    path = os.getcwd()
    while path:
        if os.path.exists(os.path.join(path, CONFIG_FILE)):
            break
        old_path = path
        path = os.path.dirname(path)
        if old_path == path:
            path = None
            break
    if path is None:
        raise IOError(CONFIG_FILE + " not found")

    return path
