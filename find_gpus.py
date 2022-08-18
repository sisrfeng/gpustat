import os

def find_gpus(need_n_gpus=4):
    need_n_gpus  = int(need_n_gpus)
    os.system('nvidia-smi -q -d Memory | grep -A4 GPU | grep Free >/tmp/free_gpus')
    with open('/tmp/free_gpus', 'r') as lines:
        frees = lines.readlines()
        id_freeMem = [ (idx, int(x.split()[2]))
                                for idx, x in enumerate(frees) ]
    id_freeMem.sort(reverse=True)  # 0号卡经常有人抢，让最后一张卡在下面的sort中优先
    id_freeMem.sort(key=lambda my_tuple: my_tuple[1], reverse=True)
    your_gpus = [str(id_mem_pair[0]) for id_mem_pair in
                    id_freeMem[:need_n_gpus] ]
    your_gpus = ','.join(your_gpus)
    #  print('    using GPUs:')
    for pair in id_freeMem[:need_n_gpus]:
        pass
                                         # >4  右端对齐,补足4字符,
    return your_gpus


import sys
out = find_gpus(sys.argv[1] )  # 必须在import torch前面
print(out)

# f-string导致无法传给shell
# print(f'{out= }')



