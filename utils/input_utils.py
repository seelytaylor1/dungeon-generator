# input_utils.py
def is_affirmative(response):
    return response.strip().lower() in ['yes', 'y', 'debug']


def get_input(prompt, args):
    if args.debug:
        print(f"{prompt} [debug mode auto-no]")
        return 'debug'
    if args.yes: return 'yes'
    if args.no: return 'no'
    return input(prompt).strip().lower()
