from utils import *
from Processors import *
from Mem import *


if __name__ == '__main__':
    filename = "test/sum.txt"
    # 初始化
    mypc = Processor()
    mypc.mem.load(filename)

    # 运行
    while True:
        mypc.run()
        mypc.print()
        if mypc.Stat == STAT.HLT.value:
            print('Halt!')
            
            # 终止写缓冲线程
            mypc.cache.stop = 1
            mypc.cache.t_write.join()

            break