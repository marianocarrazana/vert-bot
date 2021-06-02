import random

funds = 100
profit = 1.0028
loss = 0.998
for i in range(1000):
    funds = funds - (funds*(0.075/100))#buy
    v = random.choice([profit,loss,profit,profit])
    funds = (funds*v) - ((funds*v)*(0.075/100))
print('Final:',funds)