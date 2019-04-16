def AND(*args):
    for a in args:
        if not a: return False
    return True

def OR(*args):
    for a in args:
        if a: return True
    return False

def XOR(value1, value2):
    return value1 != value2

def ADD(IN0, *args):
    result = IN0
    for a in args:
        result += a
    return result

def SUB(IN1, IN2=None):
    result = IN1
    if IN2:
        result -= IN2
    return result

def MUL(*args):
    for a in args:
        result *= a
    return result

def DIV(IN1, IN2=None):
    result = IN1
    if IN2 is not None:
        result /= IN2
    return result

def EQ(IN, *args):
    for a in args:
        if IN != a:
            return False
    return True

def NE(IN, *args):
    for a in args:
        if IN == a:
            return False
    return True

def LT(IN, *args):
    for a in args:
        if IN >= a:
            return False
    return True

def LE(IN, *args):
    for a in args:
        if IN > a:
            return False
    return True

def GT(IN, *args):
    for a in args:
        if IN <= a:
            return False
    return True

def GE(IN, *args):
    for a in args:
        if IN < a:
            return False
    return True

def SEL(G, IN0, IN1):
    return IN1 if g else IN0

def MUX(K, *args):
    if isinstance(K, bool):
        K = 0 if K else 1
    return args[K]

def LIMIT(MIN, IN, MX):
    if IN < MIN: return MIN
    if IN > MX: return MX
    return IN

def MOVE(IN, EN):
    return IN if EN else None


