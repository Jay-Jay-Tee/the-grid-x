import websockets
import sys
import inspect
print('websockets package:', websockets)
print('has exceptions attribute:', hasattr(websockets, 'exceptions'))
print('module file:', getattr(websockets, '__file__', None))
print('dir sample:', [name for name in dir(websockets) if name.startswith('ex') or 'exceptions' in name])
try:
    import importlib
    mod = importlib.import_module('websockets.exceptions')
    print('websockets.exceptions loaded:', mod)
except Exception as e:
    print('error importing websockets.exceptions:', e)
print('sys.path sample:', sys.path[:5])
