import argparse

hard_coded_commands = {
    "onectf": [
        "onectf fav -t ${IP} nmap",
        "onectf fav -t ${IP} gobuster",
        "onectf fav -t ${IP} smb",
        "onectf fav -t ${IP} ssh",
        "onectf fav -t $(ip addr show tun0 | grep -oP 'inet \K[\d.]+') smb",
    ],
    "nmap": [
        "sudo nmap -Pn -p- -min-rate 5000 ${IP} -v -sV",
        "sudo nmap -Pn -sU -p- --min-rate 10000 ${IP} -v -sV",
        "rustscan -a ${IP} -- -sVC"
    ],
    "gobuster": [
        "gobuster dir -u ${IP} -w /usr/share/seclists/Discovery/Web-Content/common.txt -t 64 -o /tmp/links.txt",
        "gobuster dir -u ${IP} -w /usr/share/seclists/Discovery/Web-Content/quickhits.txt -t 64 -o /tmp/links.txt",
        "gobuster dir -u ${IP} -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-small.txt -t 64 -o /tmp/links.txt",
        "gobuster dir -u ${IP} -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt -t 64 -o /tmp/links.txt",
        "gobuster dir -u ${IP} -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-big.txt -t 64 -o /tmp/links.txt",
    ],
    "smb": [
        "smbclient -L ${IP} -U Anonymous -N"
        "smbclient -L ${IP} -U ${USER} -N",
        "impacket-smbserver -smb2support share .",
        "impacket-smbserver -smb2support -username username -password password share .",
        "copy file \\\\${IP}\share",
        "net use s: \\\\${IP}\share /user:username password"
    ],
    "ssh": [
        "sshpass -p '${PASS}' ssh -o StrictHostKeyChecking=no ${USER}@${IP}",
        "sshpass -p '${PASS}' scp -o StrictHostKeyChecking=no ${USER}@${IP}"
    ]
}


def run(parser: argparse.ArgumentParser, fav_parser: argparse.ArgumentParser):
    fav_parser.add_argument('category', help='The category of the command to fetch.', choices=list(hard_coded_commands))
    fav_parser.add_argument('-t', dest='target', help='The IP or domain name to target.')
    fav_parser.add_argument('-u', dest='username', help='The username to inject.')
    fav_parser.add_argument('-p', dest='password', help='The password to inject.')
    args = parser.parse_args()
    do_job(args)


def do_job(args):
    if args.category in hard_coded_commands:
        result = '\n'.join(hard_coded_commands[args.category])
        if args.target is not None:
            result = result.replace("${IP}", args.target)
            result = result.replace("${URL}", args.target)
        if args.username is not None:
            result = result.replace("${USER}", args.username)
        if args.password is not None:
            result = result.replace("${PASS}", args.password)
        print(result)
