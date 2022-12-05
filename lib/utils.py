
def distance(ip1, ip2):
    parts1 = ip1.split('.')
    parts2 = ip2.split('.')
    dist = 0
    for i in range(4):
        dist += abs(int(parts1[i]) - int(parts2[i])) * max(1, 256 ** (3-i))
    return dist