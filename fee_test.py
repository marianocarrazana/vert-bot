import random

funds = 100
profit = 1.0029
loss = 0.998
for i in range(1440):
    funds = funds - (funds*(0.075/100))#buy
    v = loss if random.randint(1,100) > 80 else profit
    funds = (funds*v) - ((funds*v)*(0.075/100))
print('Final:',funds)