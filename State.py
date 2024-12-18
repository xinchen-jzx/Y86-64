from enum import Enum

# 状态
class STAT(Enum):
    RST = 0
    AOK = 1
    ADR = 2
    INS = 3
    HLT = 4
    BUB = 5


# icode字段
class ICODE(Enum):
    HALT = 0
    NOP = 1
    RRMOV = 2
    IRMOV = 3
    RMMOV = 4
    MRMOV = 5
    OP = 6
    JXX = 7
    COMVXX = 2
    CALL = 8
    RET = 9
    PUSH = 10
    POP = 11