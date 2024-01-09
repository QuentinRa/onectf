
hard_coded_commands = {}


def do_job(args):
    if args.category in hard_coded_commands:
        result = '\n'.join(hard_coded_commands[args.category])
        if args.target is not None:
            result = result.replace("${IP}", args.target)
            result = result.replace("${URL}", args.target)
        print(result)

