import pandas as pd
import pymysql
from datetime import datetime
from datetime import timedelta
import re 

class MarketDB:
  def __init__(self):
    self.conn=pymysql.connect(host='호스트 주소', user='아이디', password='비밀번호', db='데이터베이스', charset='utf8')
    self.codes={}
    self.get_comp_info()
  
  def __del__(self):
    self.conn.close()

  def get_comp_info(self):
    sql=f"SELECT * from company_info"
    krx=pd.read_sql(sql, self.conn)
    for idx in range(len(krx)):
      self.codes[krx['code'].values[idx]]=krx['company'].values[idx]

  def get_daily_price(self, code, start_date=None, end_date=None):
    if start_date is None:
      one_year_age=datetime.today()-timedelta(days=365)
      start_date =one_year_age.strftime('%Y-%m-%d')
      print("start_date is initialized to '{}'".format(start_ate))
    else:
      start_lst=re.split('\D+', start_date)
      if (start_lst[0]==''):
        start_lst=start_lst[1:]
      start_year=int(start_lst[0])
      start_month=int(start_lst[1])
      start_day=int(start_lst[2])
      if start_year<1900 or start_year>2200:
        print(f"ValueError: start_year({start_year:d}) is wrong.")
        return
      if start_month<1 or start_month>12:
        print(f"ValueError: start_month({start_year:d}) is wrong.")
        return
      if start_day<1 or start_day>31:
        print(f"ValueError: start_day({start_year:d}) is wrong.")
        return
      start_date=f"{start_year:04d}-{start_month:02d}-{start_day:02d}"

      if (end_date is None):
        end_date =datetime.today().strftime('%Y-%m-%d')
        print("end_date is initialized to '{}'".format(end_date))
      else:
        end_lst=re.split('\D+', end_date)
        if (end_lst[0]==''):
          end_lst=end_lst[1:]
        end_year=int(end_lst[0])
        end_month=int(end_lst[1])
        end_day=int(end_lst[2])
        if end_year<1800 or end_year>2200:
          print(f"ValueError: end_year({end_year:d}) is wrong.")
          return
        if end_month<1 or end_month>12:
         print(f"ValueError: end_month({end_year:d}) is wrong.")
         return
        if end_day<1 or end_day>31:
          print(f"ValueError: end_day({end_year:d}) is wrong.")
          return
        end_date=f"{end_year:04d}-{end_month:02d}-{end_day:02d}"

        codes_keys=list(self.codes.keys())
        codes_values=list(self.codes.values())
        if code in codes_keys:
         pass
        elif code in codes_values:
          idx=codes_values.index(code)
          code=codes_keys[idx]
        else:
          print("ValueError: Code({}) dosen't exist." .format(code))
      
        sql=f"select * from daily_price where code='{code}' and date >= '{start_date}' and date<='{end_date}'"
        df=pd.read_sql(sql, self.conn)
        df.index=df['date']
        return df

if __name__== '__main__':
  mk=MarketDB()
  print(mk.get_daily_price('찾을 회사','2019-11-05', '2020-11-06'))
  mk.codes['018260']
