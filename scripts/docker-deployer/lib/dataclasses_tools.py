from dataclasses import asdict
import yaml

class NoAliasDumper(yaml.Dumper):
    def ignore_aliases(self, data):
        return True

def dataclass_to_yaml(dc) -> str:
    return yaml.dump(asdict(dc), default_flow_style=False, Dumper=NoAliasDumper)
