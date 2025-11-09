from gm.api import *
set_token("da029d7f7a13bbff9f9a39a9a01a169c3489aff1")

symbol = 'SHSE.000300'
history_data = history(symbol=symbol, frequency='1d', start_time='2010-07-28',  end_time='2017-07-30', adjust=2, df= True)
print(history_data)

h = get_history_symbol(symbol=symbol, start_date=None, end_date=None, df=False)
print(h)