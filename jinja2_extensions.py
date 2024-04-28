from utils import regex_ismatch

def setup_filters(env):
    env.filters['regex_ismatch'] = regex_ismatch

