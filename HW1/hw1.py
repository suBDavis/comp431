import sys
import re

SPECIAL = ['<', '>', '(', ')', '[', ']', '\\', '.', ',', ';', ':', '@', '"']
WHITESPACE = [' ', '\t']
SP = ' '
MAIL = "MAIL"
FROM = "FROM:"
AT = '@'

def log_error(errorstring):
    print("ERROR -- {error}".format(
        error=errorstring))

def parse_mail_from_cmd(command):
    assert(command[:4] == MAIL)
    assert(command[4] == SP)
    assert(command[5:10] == FROM)
    return command[10:].strip()

def parse_path(reverse_path):
    assert(reverse_path[0] == '<')
    assert(reverse_path[-1] == '>')
    return reverse_path[1:-2]

def parse_mailbox(mailbox): 

    assert('@' in mailbox)
    assert(len(mailbox.split('@')) == 2)

    parse_list = mailbox.split('@')

    assert(len(parse_list[0]) >= 1)
    assert(len(parse_list[1]) >= 1)

    return parse_list[0], parse_list[1]

def parse_local_part(local_part):

    excluded_char_list = SPECIAL + WHITESPACE
    for excluded_char in excluded_char_list:
        assert(excluded_char not in local_part)

    # Verify the string was ASCII
    assert(len(local_part) == len(local_part.encode()))

    return local_part

def parse_domain(domain):

    assert(len(domain) >= 2)
    element_list = domain.split('.')
    return element_list


for command in sys.stdin:  # For each command line
    
    print(command[:-1])  # Remove the newline
    
    command_whitespace_removed = ' '.join(command.split())
    
    try:
        reverse_path = parse_mail_from_cmd(command_whitespace_removed)
    except:
        log_error("mail-from-cmd")
        continue 

    try:
        mailbox = parse_path(reverse_path)
    except:
        log_error("path")
        continue

    try:
        local_part, domain = parse_mailbox(mailbox)
    except:
        log_error("mailbox")
        continue

    try:
        valid_local_part = parse_local_part(local_part)
    except:
        log_error("local-part")
        continue

    try:
        element_list = parse_domain(domain)
    except:
        log_error("domain")
        continue

    # TODO: finish parsing the domain

    print("Sender ok")

else:
    pass