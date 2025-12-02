import asyncio
from processor import df_preprocess

if __name__ == "__main__":
   res = asyncio.run(df_preprocess(stock_code="sh510050", stock_type=1))
   print(res)