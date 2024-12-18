from math import log
import random
import threading
import time

from utils import *
from Mem import *

# Cache大类
class Cache:
    # 初始化
    def __init__(self, mem, LINE=16, BLOCK=16, GROUP=1, bufferSize=32):
        # Memory
        self.mem:Memory = mem

        # Cache结构 (行数 - 块大小 - 组数)
        self.line = LINE
        self.block = BLOCK
        self.group = GROUP

        self.lineBit = int(log(self.line, 2))
        self.blockBit = int(log(self.block, 2))
        self.tagBit = int(self.mem.addressBit - self.lineBit - self.blockBit)

        # 直接映射/组相联/全相联 Cache
        # 1. [index][group][offset]
        self.data = [[['00' for block in range(self.block)] for group in range(self.group)] for line in range(self.line)]

        # 2. tag/dirty/valid 字段 [index][group]
        self.tag = [['0' * self.tagBit for group in range(self.group)] for line in range(self.line)]
        self.dirty = [[0 for group in range(self.group)] for line in range(self.line)]
        self.valid = [[0 for group in range(self.group)] for line in range(self.line)]

        # 3. LRU替换策略 [index][group]
        #   0   - 最近被访问
        #   非0 - 离上次被访问的久远程度
        self.lastAccess = [[0 for group in range(self.group)] for line in range(self.line)]
        
        # 输出信息提示
        self.HIT = 0
        self.MISS = 0

        # 写缓冲 (择机将写缓冲区内的内容写入内存)
        self.bufferSize:int = bufferSize

        # 1. 写缓冲存储 (data - addr - bytes)
        self.buffer_data = [0 for i in range(self.bufferSize)]
        self.buffer_addr = [0 for i in range(self.bufferSize)]

        # 2. 双指针
        self.start:int = 0
        self.end:int = 0

        # # 3. 写缓冲区状态
        # self.full:bool = False

        # # 4. 写缓冲线程
        # self.t_write = threading.Thread(target=self.Write_Buffer2Mem)
        # self.lock = threading.Lock()  # 互斥锁 -> 防止资源竞争
        # self.stop:int = False  # 信号量
        # self.t_write.start()  # 开启写缓冲线程

    # 将块数据从内存写入缓存
    def write_Mem2Cache(self, baseaddr:int, group:int):
        # 数据
        data = self.mem.read_data(baseaddr, nbytes=self.block)
        datalist = split_string_by_length(dec_to_lend_hex_width(data, 2 * self.block), 2)
        datalist.reverse()  # little end

        # 缓存的位置
        addr = bin(baseaddr)[2:].zfill(self.mem.addressBit)
        if self.lineBit == 0:
            index = 0
        else:
            index = int(addr[self.tagBit:self.tagBit + self.lineBit], 2)

        # 写入数据
        for bytes in range(self.block):
            self.data[index][group][bytes] = datalist[bytes]

    # 将块数据从缓存写入内存
    def write_Cache2Mem(self, baseaddr:int, group:int):
        # 缓存的位置
        datastr = ''
        addr = bin(baseaddr)[2:].zfill(self.mem.addressBit)
        if self.lineBit == 0:
            index = 0
        else:
            index = int(addr[self.tagBit:self.tagBit + self.lineBit], 2)
        
        # 数据
        for byte in range(self.block):
            datastr = self.data[index][group][byte] + datastr  # 倒序存储 -> 小端法存储数据
        
        # 写入数据
        data = int(datastr, 16)
        self.mem.write(baseaddr, data, nbytes=self.block)

    # 1. 无写缓冲
    def read_data(self, baseaddr:int, nbytes:int=8) -> int:
        # 如果地址不合法, 抛出异常, return None
        if baseaddr < 0 or baseaddr >= self.mem.address - nbytes:
            return None
        
        # 地址分位
        address = bin(baseaddr)[2:].zfill(self.mem.addressBit)
        # 1. tag 字段
        tag = address[0:self.tagBit]
        # 2. line 字段
        if self.lineBit == 0:
            index = 0
        else:
            index = int(address[self.tagBit:self.tagBit + self.lineBit], 2)
        # 3. offset 字段
        offset = int(address[self.tagBit + self.lineBit:self.tagBit + self.lineBit + self.blockBit], 2)

        # Cache匹配
        newGroup = -1
        # 1. 匹配成功
        for group in range(self.group):
            if self.tag[index][group] == tag and self.valid[index][group] == 1:
                self.HIT += 1
                newGroup = group
                break

        # 2. 匹配失败
        if newGroup == -1:
            self.MISS += 1

            # 2.1 空表项
            for group in range(self.group):
                if self.valid[index][group] == 0:
                    newGroup = group
                    break
            
            # 2.2 替换表项
            if newGroup == -1:
                newGroup = random.randint(0, self.group - 1)
                for group in range(self.group):
                    if self.lastAccess[index][newGroup] > self.lastAccess[index][group]:
                        newGroup = group
            
            if self.lineBit == 0:
                newaddr = int(tag + '0' * self.blockBit, 2)
            else:
                newaddr = int(tag + bin(index)[2:].zfill(self.lineBit) + '0' * self.blockBit, 2)
            
            if self.valid[index][newGroup] == 1 and self.dirty[index][newGroup] == 1:
                self.write_Cache2Mem(newaddr, newGroup)
            
            self.write_Mem2Cache(newaddr, newGroup)
            self.valid[index][newGroup] = 1; self.dirty[index][newGroup] = 0; self.tag[index][newGroup] = tag

        # 读取数据
        datastr = ''
        for bytes in range(nbytes):
            datastr = self.data[index][newGroup][offset + bytes] + datastr
        
        # 更新LRU记录变量
        for line in range(self.line):
            for group in range(self.group):
                if self.valid[line][group] == 1:
                    self.lastAccess[line][group] += 1
                else:
                    self.lastAccess[line][group] = 0
        self.lastAccess[index][newGroup] = 0
        return int(datastr, 16)

    def write(self, baseaddr:int, data:int, nbytes:int=8) -> int:
        # 如果地址不合法, 抛出异常, return -1
        if baseaddr < 0 or baseaddr >= self.mem.address - nbytes:
            return -1
        
        # 地址分位
        address = bin(baseaddr)[2:].zfill(self.mem.addressBit)
        # 1. tag 字段
        tag = address[0:self.tagBit]
        # 2. line 字段
        if self.lineBit == 0:
            index = 0
        else:
            index = int(address[self.tagBit:self.tagBit + self.lineBit], 2)
        # 3. offset 字段
        offset = int(address[self.tagBit + self.lineBit:self.tagBit + self.lineBit + self.blockBit], 2)

        # Cache匹配
        newGroup = -1
        # 1. 匹配成功
        for group in range(self.group):
            if self.tag[index][group] == tag and self.valid[index][group] == 1:
                newGroup = group
                self.HIT += 1
                break
        
        # 2. 匹配失败
        if newGroup == -1:
            self.MISS += 1

            # 2.1 空表项
            for group in range(self.group):
                if self.valid[index][group] == 0:
                    newGroup = group
                    break
            
            # 2.2 替换表项
            if newGroup == -1:
                newGroup = random.randint(0, self.group - 1)
                for group in range(self.group):
                    if self.lastAccess[index][newGroup] > self.lastAccess[index][group]:
                        newGroup = group
            
            if self.lineBit == 0:
                newaddr = int(tag + '0' * self.blockBit, 2)
            else:
                newaddr = int(tag + bin(index)[2:].zfill(self.lineBit) + '0' * self.blockBit, 2)
            
            if self.valid[index][newGroup] == 1 and self.dirty[index][newGroup] == 1:
                self.write_Cache2Mem(newaddr, newGroup)
            
            self.write_Mem2Cache(newaddr, newGroup)
            self.valid[index][newGroup] = 1; self.dirty[index][newGroup] = 0; self.tag[index][newGroup] = tag

        # 向缓存写入数据
        datalist = split_string_by_length(dec_to_lend_hex_width(data, 2 * nbytes), 2)
        datalist.reverse()  # little end
        for bytes in range(nbytes):
            self.data[index][newGroup][offset + bytes] = datalist[bytes]
        self.dirty[index][newGroup] = 1

        # 更新LRU记录变量
        for line in range(self.line):
            for group in range(self.group):
                if self.valid[line][group] == 1:
                    self.lastAccess[line][group] += 1
                else:
                    self.lastAccess[line][group] = 0
        self.lastAccess[index][newGroup] = 0
        return 1

    # Cache相关信息输出
    def print(self):
        print("\n\n")
        try:
            print("================================")
            print(f"Cache miss: {self.MISS}, Cache hit: {self.HIT}")
            print(f"Cache miss rate: {self.MISS / (self.HIT + self.MISS) * 100:.2f}%")
            print(f"Cache hit rate: {self.HIT / (self.HIT + self.MISS) * 100:.2f}%")
            print("================================")
        except:
            print("未访问缓存", end='')
        print("\n\n")

    # 写缓冲择机将数据写回内存 (单开线程并行运行)
    def Write_Buffer2Mem(self):
        while True:
            # 缓冲区为空
            if self.full == False and self.start == self.end:
                if self.stop == True:  # 主线程通知结束子线程
                    break
                else:  # 线程睡眠
                    time.sleep(2)
                    continue

            # 缓冲区不为空 (写出数据后写缓冲肯定不为空) - 互斥资源访问
            self.lock.acquire()
            print(f"WriteBuffer向Memory地址位{self.buffer_data[self.start]}写入块数据{self.buffer_data[self.start]}")
            self.mem.write(self.buffer_addr[self.start], self.buffer_data[self.start], self.block)
            self.start = (self.start + 1) % self.bufferSize
            self.full = False
            self.lock.release()

    # 将块数据从缓存写入写缓冲
    def write_Cache2Buffer(self, baseaddr:int, group:int) -> bool:
        if self.full == True:
            return False
        
        # 缓存的位置
        datastr = ''
        addr = bin(baseaddr)[2:].zfill(self.mem.addressBit)
        if self.lineBit == 0:
            index = 0
        else:
            index = int(addr[self.tagBit:self.tagBit + self.lineBit], 2)
        
        # 数据
        for byte in range(self.block):
            datastr = self.data[index][group][byte] + datastr  # 倒序存储 -> 小端法存储数据
        
        # 写入数据
        self.lock.acquire()
        data = int(datastr, 16)
        self.buffer_data[self.end] = data
        self.buffer_addr[self.end] = baseaddr

        self.end = (self.end + 1) % self.bufferSize
        if self.end == self.start:  # end指针赶上start指针, 则缓冲区满
            self.full = True
        else:  # 否则缓冲区未满
            self.full = False
        self.lock.release()
        return True

     # 将块数据从写缓冲写入缓存
    def write_Buffer2Cache(self, baseaddr:int, group:int, index:int) -> bool:
        if self.full == False and self.start == self.end:  # 缓冲区为空
            return False

        # 数据
        self.lock.acquire()
        data = self.buffer_data[index]
        self.lock.release()
        datalist = split_string_by_length(dec_to_lend_hex_width(data, 2 * self.block), 2)
        datalist.reverse()  # little end

        # 缓存的位置
        addr = bin(baseaddr)[2:].zfill(self.mem.addressBit)
        if self.lineBit == 0:
            index = 0
        else:
            index = int(addr[self.tagBit:self.tagBit + self.lineBit], 2)

        # 写入数据
        for bytes in range(self.block):
            self.data[index][group][bytes] = datalist[bytes]
        return True

    # 2. 有写缓冲
    def read_data_buffer(self, baseaddr:int, nbytes:int=8) -> int:
        # 如果地址不合法, 抛出异常, return None
        if baseaddr < 0 or baseaddr >= self.mem.address - nbytes:
            return None
        
        # 地址分位
        address = bin(baseaddr)[2:].zfill(self.mem.addressBit)
        # 1. tag 字段
        tag = address[0:self.tagBit]
        # 2. line 字段
        if self.lineBit == 0:
            index = 0
        else:
            index = int(address[self.tagBit:self.tagBit + self.lineBit], 2)
        # 3. offset 字段
        offset = int(address[self.tagBit + self.lineBit:self.tagBit + self.lineBit + self.blockBit], 2)

        # 块数据起始地址
        if index == 0:
            newaddr = int(tag + '0' * self.blockBit, 2)
        else:
            newaddr = int(tag + bin(index)[2:].zfill(self.lineBit) + '0' * self.blockBit, 2)

        # Cache匹配
        newGroup = -1
        # 1. Cache匹配成功
        for group in range(self.group):
            if self.tag[index][group] == tag and self.valid[index][group] == 1:
                self.HIT += 1
                newGroup = group
                break

        # 2. Cache匹配失败 (写缓冲 OR 内存 (块数据) -> 缓存)
        if newGroup == -1:
            self.MISS += 1

            # 2.1 确定Cache表项
            # 2.1.1 写入空表项
            for group in range(self.group):
                if self.valid[index][group] == 0:
                    newGroup = group
                    break
            
            # 2.1.2 替换已有表项 (随机 + LRU)
            if newGroup == -1:
                newGroup = random.randint(0, self.group - 1)
                for group in range(self.group):
                    if self.lastAccess[index][newGroup] > self.lastAccess[index][group]:
                        newGroup = group

            # 2.2 匹配写缓冲/内存
            BufferIndex = -1
            start = self.start
            full = self.full
            
            while True:  # 遍历写缓冲
                if full == True and start == self.end:  # 缓冲区满
                    full = False
                elif full == False and start == self.end:  # 缓冲区空白
                    break

                # 匹配到对应的数据
                if self.buffer_addr[start] <= baseaddr <= self.buffer_addr[start] + self.block - 1:
                    BufferIndex = start
                start = (start + 1) % self.bufferSize

            if BufferIndex == -1:
                self.write_Mem2Cache(newaddr, newGroup)
            else:
                self.write_Buffer2Cache(newaddr, newGroup, BufferIndex)
            self.valid[index][newGroup] = 1; self.tag[index][newGroup] = tag

        # 读取数据
        datastr = ''
        for bytes in range(nbytes):
            datastr = self.data[index][newGroup][offset + bytes] + datastr

        # 更新LRU记录变量
        for line in range(self.line):
            for group in range(self.group):
                if self.valid[line][group] == 1:
                    self.lastAccess[line][group] += 1
                else:
                    self.lastAccess[line][group] = 0
        self.lastAccess[index][newGroup] = 0
        return int(datastr, 16)
    
    # 有写缓冲写入数据
    def write_buffer(self, baseaddr:int, data:int, nbytes:int=8) -> int:
        # 如果地址不合法, 抛出异常, return -1
        if baseaddr < 0 or baseaddr >= self.mem.address - nbytes:
            return -1
        
        # 地址分位
        address = bin(baseaddr)[2:].zfill(self.mem.addressBit)
        # 1. tag 字段
        tag = address[0:self.tagBit]
        # 2. line 字段
        if self.lineBit == 0:
            index = 0
        else:
            index = int(address[self.tagBit:self.tagBit + self.lineBit], 2)
        # 3. offset 字段
        offset = int(address[self.tagBit + self.lineBit:self.tagBit + self.lineBit + self.blockBit], 2)

         # 块数据起始地址
        if index == 0:
            newaddr = int(tag + '0' * self.blockBit, 2)
        else:
            newaddr = int(tag + bin(index)[2:].zfill(self.lineBit) + '0' * self.blockBit, 2)

        # Cache匹配
        newGroup = -1
        # 1. Cache匹配成功
        for group in range(self.group):
            if self.tag[index][group] == tag and self.valid[index][group] == 1:
                newGroup = group
                self.HIT += 1
                break
        
        # 2. Cache匹配失败
        if newGroup == -1:
            self.MISS += 1

            # 2.1 确定Cache表项
            # 2.1.1 写入空表项
            for group in range(self.group):
                if self.valid[index][group] == 0:
                    newGroup = group
                    break
            
            # 2.1.2 替换已有表项 (随机 + LRU)
            if newGroup == -1:
                newGroup = random.randint(0, self.group - 1)
                for group in range(self.group):
                    if self.lastAccess[index][newGroup] > self.lastAccess[index][group]:
                        newGroup = group
            
            # 2.2 从内存读取块数据到Cache
            self.write_Mem2Cache(newaddr, newGroup)
            self.valid[index][newGroup] = 1; self.tag[index][newGroup] = tag

        # 向Cache and Buffer写入数据
        # 1. 向Cache写入数据
        datalist = split_string_by_length(dec_to_lend_hex_width(data, 2 * nbytes), 2)
        datalist.reverse()  # little end
        for bytes in range(nbytes):
            self.data[index][group][offset + bytes] = datalist[bytes]
        
        # 2. 向Buffer写入数据
        while not self.write_Cache2Buffer(newaddr, newGroup):
            time.sleep(2)

        # 更新LRU记录变量
        for line in range(self.line):
            for group in range(self.group):
                if self.valid[line][group] == 1:
                    self.lastAccess[line][group] += 1
                else:
                    self.lastAccess[line][group] = 0
        self.lastAccess[index][newGroup] = 0
        return 1
