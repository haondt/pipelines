from jinja2 import Environment, FileSystemLoader
import os

def load_file(fn):
    with open(fn, 'r') as f:
        return f.read()

_jinja_env = None
def get_jinja():
    global _jinja_env
    if _jinja_env is None:
        templates_path = os.path.join(os.path.dirname(__file__), '..', 'templates')
        env = Environment(loader=FileSystemLoader(templates_path))
        _jinja_env = env
    return _jinja_env

def render_template(template: str, **kwargs):
    template_text = get_jinja().get_template(template)
    return template_text.render(**kwargs)
