__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.2"


def AND(args):
    """
    @descripton Logical AND
    @var_in args input arguments
    """
    for a in args:
        if not a:
            return False
    return True


def OR(args):
    """
    @descripton Logical OR
    @var_in args input arguments
    """
    for a in args:
        if a:
            return True
    return False


def XOR(value1, value2):
    """
    @descripton Logical XOR
    @var_in value1 input value 1
    @var_in value2 input value 2
    """
    return value1 != value2


def ADD(args):
    """
    @description Arithmetic addition
    @var_in args Values to sum
    """
    result = 0
    for a in args:
        result += a
    return result


def SUB(IN1, IN2=None):
    """
    @description Arithmetic substraction
    @var_in IN1 initial value
    @var_in IN2 value to substract
    """
    result = IN1
    if IN2:
        result -= IN2
    return result


def MUL(args):
    """
    @description Arithmetic multiplication
    @var_in args Values to multiplicate
    """
    result = 1
    for a in args:
        result *= a
    return result


def DIV(IN1, IN2=None):
    """
    @description Arithmetic division
    @var_in IN1 divisible
    @var_in IN2 divider
    """
    result = IN1
    if IN2 is not None:
        result /= IN2
    return result


def EQ(args):
    """
    @description Comparison (equal)
    @var_in args Values to compare
    """
    i = args[0]
    if len(args) > 1:
        for a in args[1:]:
            if i != a:
                return False
    return True


def NE(args):
    """
    @description Comparison (non-equal)
    @var_in args Values to compare
    """
    i = args[0]
    if len(args) > 1:
        for a in args[1:]:
            if i == a:
                return False
    return True


def LT(IN, args):
    """
    @description Comparison (less)
    @var_in IN Input value
    @var_in args Values to compare
    """
    for a in args:
        if IN >= a:
            return False
    return True


def LE(IN, args):
    """
    @description Comparison (less or equal)
    @var_in IN Input value
    @var_in args Values to compare
    """
    for a in args:
        if IN > a:
            return False
    return True


def GT(IN, args):
    """
    @description Comparison (greater)
    @var_in IN Input value
    @var_in args Values to compare
    """
    for a in args:
        if IN <= a:
            return False
    return True


def GE(IN, args):
    """
    @description Comparison (greater or equal)
    @var_in IN Input value
    @var_in args Values to compare
    """
    for a in args:
        if IN < a:
            return False
    return True


def SEL(G, IN0, IN1):
    """
    @description Selection
    @var_in G selector
    @var_in IN0 value if False
    @var_in IN1 value if True
    """
    return IN1 if g else IN0


def MUX(K, args):
    """
    @description Array element selection
    @var_in K selector
    @var_in args values to select from
    """
    if isinstance(K, bool):
        K = 0 if K else 1
    return args[K]


def LIMIT(IN, MIN, MX):
    """
    @description Limiter
    @var_in IN Input value
    @var_in MIN minimal value
    @var_in MX maximal value
    """
    if IN < MIN:
        return MIN
    if IN > MX:
        return MX
    return IN


def MOVE(IN, EN):
    """
    @description Move if True
    @var_in IN Input value
    @var_in EN Pass if True
    """
    return IN if EN else None


g = {
    'AND': AND,
    'OR': OR,
    'XOR': XOR,
    'ADD': ADD,
    'SUB': SUB,
    'MUL': MUL,
    'DIV': DIV,
    'EQ': EQ,
    'NE': NE,
    'LT': LT,
    'LE': LE,
    'GT': GT,
    'GE': GE,
    'SEL': SEL,
    'MUX': MUX,
    'LIMIT': LIMIT,
    'MOVE': MOVE,
}
