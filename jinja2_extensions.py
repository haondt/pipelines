from utils import regex_ismatch

def setup_filters(env):
    env.filters['regex_ismatch'] = regex_ismatch
    env.filters['raise_value_error'] = _raise_value_error

def _raise_value_error(value):
    raise ValueError(value)

