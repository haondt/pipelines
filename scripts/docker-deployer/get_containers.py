import yaml, argparse

def main():
    parser = argparse.ArgumentParser(prog='get-containers')
    parser.add_argument('changes', help='repository map')
    parser.add_argument('project', help='services to get containers from')
    args = parser.parse_args()

    with open(args.changes) as f:
        data = yaml.safe_load(f)

    if args.project not in data['projects']:
        return

    if data['projects'][args.project]['status'] == 'modified':
        print('\n'.join(data['projects'][args.project]['services'].keys()))
    else:
        for k, v in data['projects'][args.project]['services'].items():
            if v['status'] == 'modified':
                print(k)

if __name__ == '__main__':
    main()
