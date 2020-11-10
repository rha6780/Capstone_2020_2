﻿import pymysql
import pandas as pd
import urllib, pymysql, calendar, time, json
from urllib.request import urlopen
from datetime import datetime
from threading import Timer
from bs4 import BeautifulSoup


class DBupdater:
  def __init__(self):
    self.conn = pymysql.connect('호스트주소','아이디',passwd='비밀번호',db='데이터베이스', charset='utf8')
    with self.conn.cursor() as curs:
       sql="""
       CREATE TABLE IF NOT EXISTS company_info(
         code VARCHAR(20),
         company VARCHAR(40),
         last_update VARCHAR(200),
         PRIMARY KEY(code)
       ) 
       """
       curs.execute(sql)
       sql="""
       CREATE TABLE IF NOT EXISTS daily_price(
        code VARCHAR(20),
        date VARCHAR(200),
        open BIGINT(20),
        high BIGINT(20),
        low BIGINT(20),
        close BIGINT(20),
        diff BIGINT(20),
        volume BIGINT(20),
        PRIMARY KEY (code, date)
       )
       """
       curs.execute(sql)
    self.conn.commit()

    self.codes=dict()
    self.update_comp_info()

  def __del__(self):
    self.conn.close()
    print("DONE!")

  def read_krx_code(self):
    url='http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
    krx=pd.read_html(url, header=0)[0]
    krx=krx[['종목코드','회사명']]
    krx=krx.rename(columns={'종목코드':'code', '회사명':'company'})
    krx.code=krx.code.map('{:06d}'.format)
    return krx

  def update_comp_info(self):
    sql="SELECT * FROM company_info"
    df=pd.read_sql(sql, self.conn)
    for idx in range(len(df)):
      self.codes[df['code'].values[idx]]=df['company'].values[idx]
    with self.conn.cursor() as curs:
      sql="SELECT max(last_update) FROM company_info"
      curs.execute(sql)
      rs=curs.fetchone()
      today=datetime.now().strftime('%Y-%m-%d')

      if rs[0]==None or rs[0]< today :
        krx=self.read_krx_code()
        for idx in range(len(krx)):
          code=krx.code.values[idx]
          company=krx.company.values[idx]
          sql=f"REPLACE INTO company_info (code, company, last_update) VALUES ('{code}','{company}', '{today}')"
          curs.execute(sql)
          self.codes[code]=company
          tmnow=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
          print(f"[{tmnow}]{idx:04d} REPLACE INTO company_info VALUES ({code}, {company}, {today})")
        self.conn.commit()
        print('')
        
  def read_naver(self, code, company, pages_to_fetch):
    try:
      url=f"http://finance.naver.com/item/sise_day.nhn?code={code}"
      with urlopen(url) as doc:
        if doc is None:
          return None
        html=BeautifulSoup(doc, "lxml")
        pgrr=html.find("td", class_="pgRR")
        if pgrr is None:
          return None
        s=str(pgrr.a["href"]).split('=')
        lastpage=s[-1]
      df=pd.DataFrame()
      pages=min(int(lastpage), pages_to_fetch)
      for page in range(1, pages+1):
        pg_url='{}&page={}'.format(url, page)
        df=df.append(pd.read_html(pg_url, header=0)[0])
        tmnow=datetime.now().strftime("%Y-%m-%d %H:%M")
        print('[{}] {} ({}) : {:04d}/{:04d} pages are downloading..!'. format(tmnow, company, code, page, pages), end="\r")
      df=df.rename(columns={'날짜':'date','종가':'close','전일비':'diff','시가':'open','고가':'high','저가':'low','거래량':'volume'})
      df['date']=df['date'].replace('.','-')
      df=df.dropna()
      df[['close','diff','open','high','low','volume']]=df[['close','diff','open','high','low','volume']].astype(int)
      df=df[['date','open','high','low','close','diff','volume']]
    except Exception as e:
      print('Exception ocurred: ', str(e))
      return None
    return df

  def replace_into_db(self, df, num, code, company):
    with self.conn.cursor() as curs:
      for r in df.itertuples():
        sql=f"REPLACE INTO daily_price VALUES ('{code}', '{r.date}', '{r.open}', '{r.high}', '{r.low}', '{r.close}', '{r.diff}', '{r.volume}')"
        curs.execute(sql)
      self.conn.commit()
      print('[{}] #{:04d} {} ({}): {} rows>REPLACE INTO daily_price [OK]'.format(datetime.now().strftime('%Y-%m-%d %H:%M'), num+1, company, code, len(df)))

  def update_daily_price(self, pages_to_fetch):
    for idx, code in enumerate(self.codes):
      df=self.read_naver(code, self.codes[code], pages_to_fetch)
      if df is None:
        continue
      self.replace_into_db(df, idx, code, self.codes[code])
  
  def execute_daily(self):
    self.update_comp_info()
    try:
      with open('/파일경로/config.json', 'r') as in_file:
        config=json.load(in_file)
        pages_to_fetch=config['pages_to_fetch']
    except FileNotFoundError:
      with open('config.json', 'w') as out_file:
        pages_to_fetch=100
        config={'pages_to_fetch':1}
        json.dump(config, coutfile)
    self.update_daily_price(pages_to_fetch)

    tmnow=datetime.now()
    lastday=calendar.monthrange(tmnow.year, tmnow.month)[1]
    if tmnow.month==12 and tmnow.day==lastday:
      tmnext=tmnow.replace(year=tmnow.year+1, month=1, day=1, hour=17, minute=0, second=0)
    elif tmnow.day==lastday:
      tmnext=tmnow.replace(month=tmnow.month+1, day=1, hour=17, minute=0, second=0)
    else:
      tmnext= tmnow.replace(month=tmnow.day+1, hour=17, minute=0, second=0)
    tmdiff=tmnext-tmnow
    secs=tmdiff.seconds

    t=Timer(secs, self.execute_daily)
    print("Waiting for next update ({}) ...".format(tmnext.strftime('%Y-%m-%d %H:%M')))
    t.start()


if __name__== '__main__':
  dbu=DBupdater()
  dbu.execute_daily()
