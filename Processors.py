from utils import *

from Mem import *
from Cache import *
from Reg import *
from ALU import *
from State import *


# 流水线
class Processor:
    # 初始化
    def __init__(self):
        # 内存
        self.mem = Memory(addressBit=16)
        self.cache = Cache(self.mem)
        
        # 流水线寄存器
        self.wbif = WBIF(0)
        self.ifid = IFID(STAT.AOK.value, ICODE.NOP.value, 0, RF.RNONE.value, RF.RNONE.value, 0, 0)
        self.idex = IDEX(STAT.AOK.value, ICODE.NOP.value, 0, 0, 0, 0, RF.RNONE.value, RF.RNONE.value, RF.RNONE.value,
                         RF.RNONE.value)
        self.exmem = EXMEM(STAT.AOK.value, ICODE.NOP.value, 0, 0, 0, RF.RNONE.value, RF.RNONE.value)
        self.memwb = MEMWB(STAT.AOK.value, ICODE.NOP.value, 0, 0, RF.RNONE.value, RF.RNONE.value)
        
        # 通用寄存器
        self.comregs = ComRegs()
        
        # 状态码
        self.Stat = STAT.AOK.value

    # 设置状态码
    def setcc(self, valE):
        if valE == 0:
            self.comregs.ZF = 1
        else:
            self.comregs.ZF = 0

        if valE < 0:
            self.comregs.SF = 1
        else:
            self.comregs.SF = 0

        if valE > 0x7FFFFFFF:
            self.comregs.OF = 1
        else:
            self.comregs.OF = 0

    # 条件分支
    def cond(self, ifun):
        ZF = self.comregs.ZF
        SF = self.comregs.SF
        OF = self.comregs.OF
        cnd = 0
        if ifun == 0:    # no condition
            cnd = 1
        elif ifun == 1:  # jle cond = (SF^OF)|ZF
            cnd = (SF ^ OF) | ZF
        elif ifun == 2:  # jl cond = SF ^ OF
            cnd = SF ^ OF
        elif ifun == 3:  # je ZF
            cnd = ZF
        elif ifun == 4:  # jne
            cnd = 1 - ZF
        elif ifun == 5:  # jge
            cnd = 1 - (SF ^ OF)
        elif ifun == 6:  # jg
            cnd = (1 - (SF ^ OF)) & (1 - ZF)
        return cnd

    def print(self):
        self.comregs.print()
        self.wbif.print()
        self.ifid.print()
        self.idex.print()
        self.exmem.print()
        self.memwb.print()
        self.cache.print()
        print("============================================================\n\n")

    def ifetch(self):
        f_pc = ''
        f_iReg = ''
        instr_valid = 0
        need_regids = 0
        need_valC = 0
        # Select PC
        if self.exmem.icode == ICODE.JXX.value and not self.exmem.Cnd:
            f_pc = self.exmem.valA
        elif self.memwb.icode == ICODE.RET.value:
            f_pc = self.memwb.valM
        else:
            f_pc = self.wbif.predPC
        # Read 10 bytes at PC
        f_iReg = self.mem.read(f_pc, 10)
        if f_iReg == -1:
            imem_error = 1
        else:
            imem_error = 0
        f_icode = int(f_iReg[0], 16)
        f_ifun = int(f_iReg[1], 16)
        # Instruction valid
        if 0 <= f_icode <= 11:
            instr_valid = 1
        # Need regids
        if f_icode in {ICODE.RRMOV.value, ICODE.OP.value, ICODE.PUSH.value, ICODE.POP.value, ICODE.IRMOV.value,
                       ICODE.RMMOV.value, ICODE.MRMOV.value}:
            need_regids = 1
        # Need valC
        if f_icode in {ICODE.IRMOV.value, ICODE.RMMOV.value, ICODE.MRMOV.value, ICODE.JXX.value, ICODE.CALL.value}:
            need_valC = 1
        # Align
        if (not need_regids) and (not need_valC):
            f_rA = RF.RNONE.value
            f_rB = RF.RNONE.value
            f_valC = 0
        elif need_regids and (not need_valC):
            f_rA = int(f_iReg[2], 16)
            f_rB = int(f_iReg[3], 16)
            f_valC = 0
        elif (not need_regids) and need_valC:
            f_rA = RF.RNONE.value
            f_rB = RF.RNONE.value
            f_valC = lend_hex_to_dec(f_iReg[2: 18])
        else:
            f_rA = int(f_iReg[2], 16)
            f_rB = int(f_iReg[3], 16)
            f_valC = lend_hex_to_dec(f_iReg[4: 20])
        # PC inc
        f_valP = f_pc + 1 + need_regids + need_valC * 8
        f_iReg = f_iReg[0:(f_valP - f_pc) * 2]
        # Predict PC
        if f_icode in {ICODE.JXX.value, ICODE.CALL.value}:
            f_predPC = f_valC
        else:
            f_predPC = f_valP
        # Stat
        if imem_error:
            f_stat = STAT.ADR.value
        elif not instr_valid:
            f_stat = STAT.INS.value
        elif f_icode == ICODE.HALT.value:
            f_stat = STAT.HLT.value
        else:
            f_stat = STAT.AOK.value

        self.comregs.iReg = f_iReg
        self.comregs.PC = f_pc
        # self.f_pc = f_pc
        next_ifid = (f_stat, f_icode, f_ifun, f_rA, f_rB, f_valC, f_valP)
        forwarding = (f_predPC)
        return next_ifid, forwarding

    def idecode(self, e_dstE, e_valE, m_valM):
        d_stat = self.ifid.stat
        d_icode = self.ifid.icode
        d_ifun = self.ifid.ifun
        d_valC = self.ifid.valC
        d_valA = 0
        d_valB = 0
        d_dstE = RF.RNONE.value
        d_dstM = RF.RNONE.value
        d_srcA = RF.RNONE.value
        d_srcB = RF.RNONE.value

        ifid_stat = self.ifid.stat
        ifid_icode = self.ifid.icode
        ifid_ifun = self.ifid.ifun
        ifid_rA = self.ifid.rA
        ifid_rB = self.ifid.rB
        ifid_valC = self.ifid.valC
        ifid_valP = self.ifid.valP
        # ex_mm
        exmem_valE = self.exmem.valE
        # exmm_valM = self.exmem.valM
        exmem_dstE = self.exmem.dstE
        exmem_dstM = self.exmem.dstM
        # mm_wb
        memwb_valE = self.memwb.valE
        memwb_valM = self.memwb.valM
        memwb_dstE = self.memwb.dstE
        memwb_dstM = self.memwb.dstM
        # d_dstE; 写rf时，valE 写到 M[rB]
        if self.ifid.icode in {ICODE.RRMOV.value, ICODE.IRMOV.value, ICODE.OP.value}:
            d_dstE = self.ifid.rB
        elif self.ifid.icode in {ICODE.PUSH.value, ICODE.POP.value, ICODE.CALL.value, ICODE.RET.value}:
            d_dstE = RF.RSP
        # d_dstM; 写rf时。valM 写到 M[rA]： mrmov, pop
        if self.ifid.icode in {ICODE.MRMOV.value, ICODE.POP.value}:
            d_dstM = self.ifid.rA
        # d_srcA; 读rf时，valA 读自 M[rA]
        if self.ifid.icode in {ICODE.RRMOV.value, ICODE.RMMOV.value, ICODE.OP.value, ICODE.PUSH.value}:
            d_srcA = self.ifid.rA
        elif self.ifid.icode in {ICODE.POP.value, ICODE.RET.value}:
            d_srcA = RF.RSP
        # d_srcB; 读rf时，valB 读自 M[rB]
        # ICODE.RMMOV, ICODE.MRMOV, ICODE.OP
        if self.ifid.icode in {ICODE.RMMOV.value, ICODE.MRMOV.value, ICODE.OP.value}:
            d_srcB = self.ifid.rB
        elif self.ifid.icode in {ICODE.PUSH.value, ICODE.POP.value, ICODE.CALL.value, ICODE.RET.value}:
            d_srcB = RF.RSP
        # read rf
        d_rvalA = self.comregs.readrf(d_srcA)
        d_rvalB = self.comregs.readrf(d_srcB)
        # Sel + FwdA
        if self.ifid.icode in {ICODE.CALL.value, ICODE.JXX.value}:
            d_valA = self.ifid.valP  # 将valA 与 valP合并
        elif d_srcA == e_dstE:  # forward valE from execute
            d_valA = e_valE  # 3执行-译码数据冒险
        elif d_srcA == exmem_dstM:  # forward valM from memory
            d_valA = m_valM  # 2访存-译码数据冒险
        elif d_srcA == exmem_dstE:  # forward valE from memory
            d_valA = exmem_valE  # 2访存-译码数据冒险
        elif d_srcA == memwb_dstE:  # forward valE from write back
            d_valA = memwb_valE  # 1写回-译码数据冒险
        elif d_srcA == memwb_dstM:
            d_valA = memwb_valM
        else:
            d_valA = d_rvalA
        # FwdB
        if d_srcB == e_dstE:  # forward valE from execute
            d_valB = e_valE  # 3执行-译码数据冒险
        elif d_srcB == exmem_dstM:  # forward valM from memory
            d_valB = m_valM  # 2访存-译码数据冒险
        elif d_srcB == exmem_dstE:  # forward valE from memory
            d_valB = exmem_valE  # 2访存-译码数据冒险
        elif d_srcB == memwb_dstE:  # forward valE from write back
            d_valB = memwb_valE  # 1写回-译码数据冒险
        elif d_srcB == memwb_dstM:
            d_valB = memwb_valM
        else:
            d_valB = d_rvalB
        next_idex = (d_stat, d_icode, d_ifun, d_valC, d_valA, d_valB, d_dstE, d_dstM, d_srcA, d_srcB)
        forwarding = (d_srcA, d_srcB)
        return next_idex, forwarding

    def execute(self, m_stat):
        # id_ex
        idex_stat = self.idex.stat
        idex_icode = self.idex.icode
        idex_ifun = self.idex.ifun
        idex_valC = self.idex.valC
        idex_valA = self.idex.valA
        idex_valB = self.idex.valB
        idex_dstE = self.idex.dstE
        idex_dstM = self.idex.dstM
        idex_srcA = self.idex.srcA
        idex_srcB = self.idex.srcB

        # aluA
        if idex_icode in {ICODE.RRMOV.value, ICODE.OP.value}:
            aluA = idex_valA
        elif idex_icode in {ICODE.IRMOV.value, ICODE.RMMOV.value, ICODE.MRMOV.value}:
            aluA = idex_valC
        elif idex_icode in {ICODE.PUSH.value, ICODE.POP.value}:
            aluA = -8
        elif idex_icode in {ICODE.CALL.value, ICODE.RET.value}:
            aluA = 8
        else:
            aluA = 0
        # aluB
        if idex_icode in {ICODE.RMMOV.value, ICODE.MRMOV.value, ICODE.OP.value, ICODE.CALL.value,
                          ICODE.RET.value, ICODE.PUSH.value, ICODE.POP.value}:
            aluB = idex_valB
        elif idex_icode in {ICODE.RRMOV.value, ICODE.IRMOV.value}:
            aluB = 0
        else:
            aluB = 0
        # alufun
        if idex_icode == ICODE.OP.value:
            alufun = idex_ifun
        else:
            alufun = ALUFUN.ADD.value

        memexp = m_stat in {STAT.ADR.value, STAT.INS.value, STAT.HLT.value}
        wbexp = self.memwb.stat in {STAT.ADR.value, STAT.INS.value, STAT.HLT.value}
        # set_cc 仅在OP指令中设置条件码
        if self.idex.icode == ICODE.OP.value and not memexp and not wbexp:
            # and m_stat not in {STAT.ADR, STAT.INS, STAT.HLT}:
            # and w_stat not in {STAT.ADR, STAT.INS, STAT.HLT}:
            set_cc = 1
        else:
            set_cc = 0
        # valE
        if alufun == ALUFUN.ADD.value:
            e_valE = aluA + aluB
        elif alufun == ALUFUN.SUB.value:
            e_valE = aluB - aluA
        elif alufun == ALUFUN.AND.value:
            e_valE = aluA & aluB
        elif alufun == ALUFUN.XOR.value:
            e_valE = aluA ^ aluB
        else:
            e_valE = 0
        # 设置条件码
        if set_cc == 1:
            self.setcc(e_valE)  # set ZF SF OF

        # e_cnd 根据ifun和cc条件码设置cond
        # 若cnd == 1, 则跳转; cnd == 0, 则不跳转
        e_cnd = self.cond(idex_ifun)

        # e_dstE 对于条件传送指令，条件成立时，才能写回寄存器
        e_dstE = idex_dstE
        if idex_icode == ICODE.RRMOV.value and e_cnd == 0:
            e_dstE = RF.RNONE.value
        next_exmem = (idex_stat, idex_icode, e_cnd, e_valE, idex_valA, e_dstE, idex_dstM)
        forwarding = (e_dstE, e_valE, e_cnd)
        return next_exmem, forwarding

    def memory(self):

        exmem_stat = self.exmem.stat
        exmem_icode = self.exmem.icode
        exmem_valE = self.exmem.valE
        exmem_valA = self.exmem.valA
        exmem_dstE = self.exmem.dstE
        exmem_dstM = self.exmem.dstM

        # mem_addr
        if exmem_icode in {ICODE.RMMOV.value, ICODE.MRMOV.value, ICODE.PUSH.value, ICODE.CALL.value}:
            mem_addr = exmem_valE
        elif exmem_icode in {ICODE.POP.value, ICODE.RET.value}:
            mem_addr = exmem_valA
        else:
            mem_addr = 0
        # mem_read
        if exmem_icode in {ICODE.MRMOV.value, ICODE.POP.value, ICODE.RET.value}:
            mem_read = 1
        else:
            mem_read = 0
        # mem_write
        if exmem_icode in {ICODE.RMMOV.value, ICODE.PUSH.value, ICODE.CALL.value}:
            mem_write = 1
        else:
            mem_write = 0

        dmem_error = 0
        # mem
        m_valM = 0
        if mem_read == 1:
            m_valM = self.cache.read_data_buffer(mem_addr)
            # m_valM = self.cache.read_data(mem_addr)
            # m_valM = self.mem.read_data(mem_addr)
            if m_valM == None:
                dmem_error = 1

        if mem_write == 1:
            tmp = self.cache.write_buffer(mem_addr, exmem_valA)
            # tmp = self.cache.write(mem_addr, exmem_valA)
            # tmp = self.mem.write(mem_addr, exmem_valA)
            if tmp == -1:
                dmem_error = 1
        # m_stat
        if dmem_error == 1:
            m_stat = STAT.ADR.value
        else:
            m_stat = exmem_stat
        next_mwmwb = (m_stat, exmem_icode, exmem_valE, m_valM, exmem_dstE, exmem_dstM)
        forwarding = (m_valM, m_stat)
        return next_mwmwb, forwarding

    def writeback(self):
        self.comregs.writerf(self.memwb.dstM, self.memwb.valM)
        self.comregs.writerf(self.memwb.dstE, self.memwb.valE)

        # P312
        if self.memwb.stat == STAT.BUB:
            self.Stat = STAT.AOK
        else:
            self.Stat = self.memwb.stat
        next_wbif = ()
        forwarding = (self.memwb.icode, self.memwb.valE, self.memwb.valM, self.memwb.dstE, self.memwb.dstM)
        return next_wbif, forwarding

    def control_logic(self, d_srcA, d_srcB, e_cnd, m_stat):
        wbif_stall = 0
        ifid_bubble = 0
        ifid_stall = 0
        idex_bubble = 0
        exmem_bubble = 0
        memwb_stall = 0
        isloaduse = self.idex.icode in {ICODE.MRMOV.value, ICODE.POP.value} and self.idex.dstM in {d_srcA, d_srcB}
        isret = ICODE.RET.value in {self.idex.icode, self.exmem.icode, self.ifid.icode}
        ismisbranch = self.idex.icode == ICODE.JXX.value and not e_cnd
        # 1 当 加载使用冒险 或 ret，wbif阶段stall
        if isloaduse or isret:
            wbif_stall = 1
        else:
            wbif_stall = 0
        # 2 当 分支预测错误 或 ret，ifid阶段bubble
        # 2 当 加载使用冒险 且 ret，ifid阶段not bubble
        if isloaduse and isret:
            ifid_bubble = 0
        elif ismisbranch or isret:
            ifid_bubble = 1
        else:
            ifid_bubble = 0

        # 3 当 加载使用冒险时
        if isloaduse:
            ifid_stall = 1
        else:
            ifid_stall = 0
        # 4当 加载使用冒险 或 分支预测错误时
        if ismisbranch or isloaduse:
            idex_bubble = 1
        else:
            idex_bubble = 0
        # 5 当 mem 或 wb 阶段有异常存在时，exmem阶段bubble
        memexp = m_stat in {STAT.ADR.value, STAT.INS.value, STAT.HLT.value}
        wbexp = self.memwb.stat in {STAT.ADR.value, STAT.INS.value, STAT.HLT.value}
        if memexp or wbexp:
            exmem_bubble = 1
        else:
            exmem_bubble = 0

        if wbexp:
            memwb_stall = 1
        else:
            memwb_stall = 0

        return wbif_stall, ifid_bubble, ifid_stall, idex_bubble, exmem_bubble, memwb_stall

    def run(self):
        next_wbif, fdwb = self.writeback()
        next_mwmwb, fdmem = self.memory()
        next_exmem, fdex = self.execute(fdmem[1]) # m_stat
        next_idex, fdid = self.idecode(fdex[0], fdex[1], fdmem[0])
        next_ifid, fdif = self.ifetch()

        wbif_stall, ifid_bubble, ifid_stall, idex_bubble, exmem_bubble, memwb_stall = self.control_logic(fdid[0],
                                                                                                         fdid[1],
                                                                                                         fdex[2],
                                                                                                         fdmem[1])

        self.wbif.update(wbif_stall, fdif)
        self.ifid.update(ifid_bubble, ifid_stall, *next_ifid)
        self.idex.update(idex_bubble, *next_idex)
        self.exmem.update(exmem_bubble, *next_exmem)
        self.memwb.update(memwb_stall, *next_mwmwb)
