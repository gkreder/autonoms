import rpyc
from rpyc.utils.server import ThreadedServer
from mochams.agilent_methods.utils_rapidFire import *
import sys

class RapidFireService(rpyc.Service):
    def exposed_call_function(self, function_name, *args, **kwargs):
        print(f"Looking for function name {function_name}")
        function = globals().get(function_name)
        if function:
            result = function(*args, **kwargs)
            print(f'Im done running {function}. It had return value {result}')
            return(result)
        else:
            raise ValueError(f"Function '{function_name}' not found in utils_rapidFire.py")
        
if __name__ == '__main__':
    port = 18861
    server = ThreadedServer(RapidFireService, port = port, protocol_config = {"allow_puyblic_attrs":True})
    print(f"starting server on port {port}")
    server.start()