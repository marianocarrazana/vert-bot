import pandas as pd 

df = pd.DataFrame([[5,5],[6,6],[2,6],[1,6],[14,6]], columns=['price','qty'])
df = df.astype({'price': float,'qty': float})
df.set_index('price',inplace = True)

df2 = pd.DataFrame([[2,2],[6,12]], columns=['price','qty'])
df2 = df2.astype({'price': float,'qty': float})
df2.set_index('price',inplace = True)

df.sort_index(inplace=True)
index = df.index.get_loc(12, method ='nearest') + 1
print(index)

print(df.iloc[0:index])
