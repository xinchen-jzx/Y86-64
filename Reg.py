from enum import Enum

from State import *


# 寄存器文件
rf_name = ['rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi',
           'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'no']


# 寄存器文件
class RF(Enum):
    RAX = 0
    RCX = 1
    RBX = 2
    RDX = 3
    RSP = 4
    RBP = 5
    RSI = 6
    RDI = 7
    R8 = 8
    R9 = 9
    R10 = 10
    R11 = 11
    R12 = 12
    R13 = 13
    R14 = 14
    RNONE = 15


# 写回-取指 寄存器
class WBIF:
    def __init__(self, predPC):
        self.predPC = predPC

    def update(self, stall, predPC):
        if stall:
            self.predPC = self.predPC
        else:
            self.predPC = predPC

    def print(self):
        print("wbif(predPC: 0x%x)" % self.predPC)


# 取指-译码 寄存器
class IFID:
    def __init__(self, stat, icode, ifun, rA, rB, valC, valP):
        self.stat = stat
        self.icode = icode
        self.ifun = ifun
        self.rA = rA
        self.rB = rB
        self.valC = valC
        self.valP = valP

    def update(self, stall, bubble, stat, icode, ifun, rA, rB, valC, valP):
        if stall:
            self.stat = self.stat
            self.icode = self.icode
            self.ifun = self.ifun
            self.rA = self.rA
            self.rB = self.rB
            self.valC = self.valC
            self.valP = self.valP
        elif bubble:
            self.stat = STAT.BUB.value
            self.icode = ICODE.NOP.value
            self.ifun = 0
            self.rA = RF.RNONE.value
            self.rB = RF.RNONE.value
            self.valC = 0
            self.valP = 0
        else:
            self.stat = stat
            self.icode = icode
            self.ifun = ifun
            self.rA = rA
            self.rB = rB
            self.valC = valC
            self.valP = valP

    def print(self):
        print("ifid(stat: %d, icode: %d, ifun: %d, rA: %d, rB: %d, valC: 0x%x, valP: 0x%x)" % (
            self.stat, self.icode, self.ifun, self.rA, self.rB, self.valC, self.valP))


# 译码-执行 寄存器
class IDEX:
    def __init__(self, stat, icode, ifun, valC, valA, valB, dstE, dstM, srcA, srcB):
        self.stat = stat
        self.icode = icode
        self.ifun = ifun
        self.valC = valC
        self.valA = valA
        self.valB = valB
        self.dstE = dstE
        self.dstM = dstM
        self.srcA = srcA
        self.srcB = srcB

    def update(self, bubble, stat, icode, ifun, valC, valA, valB, dstE, dstM, srcA, srcB):
        if bubble:
            self.stat = STAT.BUB.value
            self.icode = ICODE.NOP.value
            self.ifun = 0
            self.valC = 0
            self.valA = 0
            self.valB = 0
            self.dstE = RF.RNONE.value
            self.dstM = RF.RNONE.value
            self.srcA = RF.RNONE.value
            self.srcB = RF.RNONE.value
        else:
            self.stat = stat
            self.icode = icode
            self.ifun = ifun
            self.valC = valC
            self.valA = valA
            self.valB = valB
            self.dstE = dstE
            self.dstM = dstM
            self.srcA = srcA
            self.srcB = srcB

    def print(self):
        print("idex(stat: %d, icode: %d, ifun: %d, valC: 0x%x, valA: 0x%x, valB: 0x%x, dstE: %d, dstM: %d, srcA: %d, srcB: %d)" % (
                self.stat, self.icode, self.ifun, self.valC, self.valA, self.valB, self.dstE, self.dstM, self.srcA,
                self.srcB))


# 执行-访存 寄存器
class EXMEM:
    def __init__(self, stat, icode, Cnd, valE, valA, dstE, dstM):
        self.stat = stat
        self.icode = icode
        self.Cnd = Cnd
        self.valE = valE
        self.valA = valA
        self.dstE = dstE
        self.dstM = dstM

    def update(self, bubble, stat, icode, Cnd, valE, valA, dstE, dstM):
        if bubble:
            self.stat = STAT.BUB.value
            self.icode = ICODE.NOP.value
            self.Cnd = 0
            self.valE = 0
            self.valA = 0
            self.dstE = RF.RNONE.value
            self.dstM = RF.RNONE.value
        else:
            self.stat = stat
            self.icode = icode
            self.Cnd = Cnd
            self.valE = valE
            self.valA = valA
            self.dstE = dstE
            self.dstM = dstM

    def print(self):
        print("exmem(stat: %d, icode: %d, Cnd: %d, valE: 0x%x, valA: 0x%x, dstE: %d, dstM: %d)" % (
            self.stat, self.icode, self.Cnd, self.valE, self.valA, self.dstE, self.dstM))


# 访存-写回 寄存器
class MEMWB:
    def __init__(self, stat, icode, valE, valM, dstE, dstM):
        self.stat = stat
        self.icode = icode
        self.valE = valE
        self.valM = valM
        self.dstE = dstE
        self.dstM = dstM

    def update(self, stall, stat, icode, valE, valM, dstE, dstM):
        if stall:
            self.stat = self.stat
            self.icode = self.icode
            self.valE = self.valE
            self.valM = self.valM
            self.dstE = self.dstE
            self.dstM = self.dstM
        else:
            self.stat = stat
            self.icode = icode
            self.valE = valE
            self.valM = valM
            self.dstE = dstE
            self.dstM = dstM

    def print(self):
        print("memwb(stat: %d, icode: %d, valE: 0x%x, valM: 0x%x, dstE: %d, dstM: %d)" % (
            self.stat, self.icode, self.valE, self.valM, self.dstE, self.dstM))


class ComRegs:
    def __init__(self):
        self.regs = [0] * 16
        self.ZF = 0
        self.SF = 0
        self.OF = 0
        self.PC = 0
        self.iReg = ''

    # 读取寄存器
    def readrf(self, dstX):
        if dstX == RF.RNONE.value:
            return 0
        else:
            return self.regs[dstX]

    # 写入寄存器
    def writerf(self, dstX, valX):
        if dstX != RF.RNONE.value:
            self.regs[dstX] = valX

    # 输出信息
    def print(self):
        print("PC: 0x%x" % self.PC)
        print("iReg: %s" % self.iReg)
        print("ZF: %-3d" % self.ZF, end='|')
        print("SF: %-3d" % self.SF, end='|')
        print("OF: %d" % self.OF)
        for i in range(16):
            print("%-3x " % i, end='')
        print()
        for i in range(16):
            print("%-3s " % rf_name[i], end='')
        print()
        for i in range(16):
            print("%-3d " % self.regs[i], end='')
        print()