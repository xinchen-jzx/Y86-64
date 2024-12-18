# 假设: 
#   1. 数据 -> 8字节对齐
#   2. 地址 -> 10位

from utils import *

# 内存 (主存 - 数据, 指令、栈)
class Memory:
    # 内存初始化 (默认内存地址为10位)
    def __init__(self, addressBit=10):
        self.addressBit = addressBit
        self.address = pow(2, self.addressBit)
        self.mem = ['00'] * self.address  # 地址位: addressBit位

    # 读取nbytes字节的指令
    def read(self, baseaddr, nbytes=8) -> str:
        # 如果地址不合法, 抛出异常, return -1
        if baseaddr < 0 or baseaddr >= self.address - nbytes:
            return -1

        # 如果地址合法, 读取内存
        datastr = ''
        for offset in range(nbytes):
            memaddr = baseaddr + offset
            datastr += self.mem[memaddr]
        return datastr

    # 读取nbytes字节的数据
    def read_data(self, baseaddr, nbytes=8) -> int:
        # 如果地址不合法, 抛出异常
        if baseaddr < 0 or baseaddr >= self.address - nbytes:
            return None

        # 如果地址合法, 读取内存
        datastr = ''
        for offset in range(nbytes):
            memaddr = baseaddr + offset
            datastr = self.mem[memaddr] + datastr  # 倒序存储 -> 小端法存储数据
        return int(datastr, 16)

    # 将nbytes字节的数据写入内存
    def write(self, baseaddr, data, nbytes=8):
        # 如果地址或数据不合法, 抛出异常
        if baseaddr < 0 or baseaddr >= self.address - nbytes:
            return -1

        # 如果地址合法, 写入内存
        datalist = split_string_by_length(dec_to_lend_hex_width(data, 2 * nbytes), 2)
        datalist.reverse()  # little end
        for offset in range(nbytes):
            maddr = baseaddr + offset
            self.mem[maddr] = datalist[offset]
        return 1

    # 加载程序
    def load(self, filename):
        with open(filename, 'r') as file:
            memaddr = 0
            while True:
                line = file.readline().strip()
                if line == '':
                    break
                bytes = split_string_by_length(line, 2)
                for byte in bytes:
                    self.mem[memaddr] = byte
                    memaddr = memaddr + 1
        print("The program has been loaded!")
