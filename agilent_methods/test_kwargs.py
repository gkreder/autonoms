import sys
import os
from test_utils import *

def wrapper_fun(function_name, *args, **kwargs):
    function = globals().get(function_name)
    print(function)
    function(**kwargs)


wrapper_fun('test_fun', fname = 'hellooooo')
