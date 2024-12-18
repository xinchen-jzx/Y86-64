import Cache
import Mem

import numpy as np
import argparse

# 设置Cache相关参数
addr = 0
LINE = 0
BLOCK = 0
CacheSize = 0
GROUP = 0

# 矩阵乘法相关参数 (大小n、块大小block)
n = 0
block = 0

def mul(n, arrA, arrB, arrC):
    mem = Mem.Memory(addr)
    cache = Cache.Cache(mem, LINE=LINE, BLOCK=BLOCK, GROUP=GROUP)

    # 朴素矩阵乘法
    for i in range(n):
        for j in range(n):
            for k in range(n):
                cache.read_data(arrA[i][k], nbytes=4)
                cache.read_data(arrB[k][j], nbytes=4)
            cache.write(arrC[i][j], arrC[i][j], nbytes=4)
    
    # 输出Cache相关信息
    print("朴素矩阵乘法: ")
    cache.print()


def mul_block(n, block, arrA, arrB, arrC):
    mem = Mem.Memory(addr)
    cache = Cache.Cache(mem, LINE=LINE, BLOCK=BLOCK, GROUP=GROUP)

    for jj in range(0, n, block):
        for kk in range(0, n, block):
            for i in range(n):  # 行
                for j in range(jj, min(jj + block, n)):
                    for k in range(kk, min(kk + block, n)):
                        cache.read_data(arrA[i][k], nbytes=4)
                        cache.read_data(arrB[k][j], nbytes=4)
                    cache.read_data(arrC[i][j], nbytes=4)
                    cache.write(arrC[i][j], arrC[i][j], nbytes=4)

    # 输出cache相关信息
    print("分块矩阵乘法: ")
    cache.print()

if __name__ == '__main__':
    # 用户设置相关参数
    parser = argparse.ArgumentParser()

    # 1. 内存
    parser.add_argument('--addr', type=int, default=20, help='Memory Address Bit (Default: 20)')

    # 2. 矩阵规模 and 分块因子
    parser.add_argument('--n', type=int, default=100, help='Scale of Matrix (Default: 100*100)')
    parser.add_argument('--block', type=int, default=25, help='Block Factor (Default: 25)')

    # 3. Cache相关参数
    parser.add_argument('--CacheSize', type=int, default=12, help='Cache Size (Default: 12)')
    parser.add_argument('--LINE', type=int, default=6, help='Cache Line (Default: 6)')
    parser.add_argument('--BLOCK', type=int, default=6, help='Cache Block (Default: 6)')

    args = parser.parse_args()


    # 传递参数
    addr = args.addr
    n = args.n
    block = args.block
    CacheSize = pow(2, args.CacheSize)
    LINE = pow(2, args.LINE)
    BLOCK = pow(2, args.BLOCK)
    GROUP = int(CacheSize / LINE / BLOCK)

    # 地址 (arrA, arrB, arrC)
    arrA = np.array([[0 for j in range(n)] for i in range(n)])
    arrB = np.array([[0 for j in range(n)] for i in range(n)])
    arrC = np.array([[0 for j in range(n)] for i in range(n)])

    # 分配地址
    num = 0
    for i in range(n):
        for j in range(n):
            arrA[i][j] = num
            arrB[i][j] = num + n * n * 4
            arrC[i][j] = num + 2 * n * n * 4
            num += 4
    
    mul(n, arrA, arrB, arrC)
    mul_block(n, block, arrA, arrB, arrC)
