import time

n1 = time.time()
time.sleep(2)
n2 = time.time()
print(n2-n1 > 3)