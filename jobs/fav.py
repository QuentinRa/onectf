import argparse

hard_coded_commands = {
    "nmap" : [
        "sudo nmap -Pn -p- -min-rate 5000 ${IP} -v",
        "sudo nmap -Pn -sU -p- --min-rate 10000 ${IP} -v",
        "rustscan -a ${IP} -- -sVC"
    ],
    "gobuster": [
        "gobuster dir -u ${IP} -w /usr/share/wordlists/dirb/common.txt -t 64",
        "gobuster dir -u ${IP} -w /usr/share/seclists/Discovery/Web-Content/quickhits.txt -t 64",
        "gobuster dir -u ${IP} -w /usr/share/wordlists/dirbuster/directory-list-2.3-small.txt -t 64",
        "gobuster dir -u ${IP} -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -t 64",
    ],
    "smb": [
        "smbclient -L ${IP} -U Anonymous -N"
        "smbclient -L ${IP} -U ${USER} -N"
    ]
}


def run(parser : argparse.ArgumentParser, fav_parser : argparse.ArgumentParser):
    fav_parser.add_argument('category', help='The category of the command to fetch.')
    fav_parser.add_argument('-u', metavar='target', dest='target', help='The IP or domain name to target.')
    args = parser.parse_args()
    do_job(args)


def do_job(args):
    if args.category in hard_coded_commands:
        result = '\n'.join(hard_coded_commands[args.category])
        if args.target is not None:
            result = result.replace("${IP}", args.target)
            result = result.replace("${URL}", args.target)
        print(result)
