import sys
import yaml


def prune_changes(data: dict):
    output = {"projects": {}}
    for project_name, project in data.get("projects", {}).items():
        status = project.get("status")
        if status in ("modified", "removed"):
            output["projects"][project_name] = {
                "status": status,
            }
        else:
            services = project.get("services", {})
            filtered_services = {
                k: v for k, v in services.items() if v.get("status") != "unchanged"
            }
            if len(filtered_services) > 0:
                output["projects"][project_name] = {
                    "status": status,
                    "services": filtered_services
                }
    return output

def main():
    if len(sys.argv) < 2:
        print("Usage: prune_changes.py <changes.yml>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    output = prune_changes(data)

    print(yaml.safe_dump(output, sort_keys=False))

if __name__ == '__main__':
    main()
