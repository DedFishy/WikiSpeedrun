banlist = []

with open("banlist.txt", "r") as banlist_file:
    banlist = banlist_file.readlines()

def get_is_banned(ip):
    return ip in banlist