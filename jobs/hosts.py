import argparse
import os


def run(parser : argparse.ArgumentParser, host_parser : argparse.ArgumentParser):
    host_parser.add_argument('ip', help='IP address to add/update')
    host_parser.add_argument('domain', nargs='+', help='Domain(s) to add/update')
    host_parser.add_argument('--merge', dest='merge', action='store_true', default=True, help='Lines are merged by IP after insertion (default=YES).')
    host_parser.add_argument('--dry', dest='dry_run', action='store_true', help='If set, don\'t edit the host file (default=NO).')
    args = parser.parse_args()
    do_job(args)


def do_job(args):
    target_ip = args.ip
    domains = args.domain
    found_domains = set()
    output_file = os.path.expanduser('/etc/hosts')

    try:
        with open(output_file, 'r') as file:
            lines = file.readlines()

            for i, line in enumerate(lines):
                values = line.split()
                if len(values) < 2:
                    continue
                ip = values[0]
                is_ip = values[0] == target_ip

                # We found the IP, check that the domains are in
                final_domains = []
                for domain in values[1:]:
                    if domain in domains:
                        # nothing to change
                        if is_ip:
                            found_domains.add(domain)
                        # oh no, we found the domain
                        # but it was associated with another IP
                        # then, let's remove it
                        else:
                            continue
                    final_domains.append(domain)

                if len(final_domains) == 0:
                    lines[i] = ""
                    continue

                lines[i] = f"{ip}\t{' '.join(final_domains)}"

                if len(domains) == len(found_domains):
                    break

            # if not all domains were found
            if len(domains) != len(found_domains):
                final_domains = []
                for domain in domains:
                    if domain not in found_domains:
                        final_domains.append(domain)
                lines.append(f"{target_ip}\t{' '.join(final_domains)}")

    except FileNotFoundError:
        lines = [f"{target_ip}\t{' '.join(domains)}"]

    # remove empty lines
    if args.merge:
        merged_data = {}
        for line in lines:
            values = line.split()
            if len(values) < 2:
                continue
            ip = values[0]
            value = values[1:]
            if ip in merged_data:
                merged_data[ip].extend(value)
            else:
                merged_data[ip] = value

        lines = []
        max_key_length = max(len(key) for key in merged_data.keys())
        for k, v in merged_data.items():
            lines.append(f"{k:<{max_key_length + 5}}{' '.join(v)}")

    final_lines = '\n'.join(lines)
    print(final_lines)

    # Write 'final_lines' to 'output_file'
    if not args.dry_run:
        try:
            with open(output_file, 'w') as dest:
                dest.writelines(final_lines)
        except PermissionError as e:
            print(f"\nYou need to use 'sudo' to edit {output_file} ({e}).")

