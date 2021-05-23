import requests
import sqlite3
from datetime import datetime
#import boto3
import vars

import logging

logger = logging.getLogger('discord')


class StonkMonitor:
    """Yah the name is weird, but this was suppose to be something else
    before i changed it into being a game.
    """
    _referer_header = f"https://{vars.STOCK_URL}"+"/quote/{0}?p={0}&.tsrc=fin-srch"
    _bs_fields_param = 'fields=extendedMarketChange,extendedMarketChangePercent,extendedMarketPrice,extendedMarketTime'+\
                        ',regularMarketChange,regularMarketChangePercent,regularMarketPrice,regularMarketTime,circulatingSupply,'+\
                        'ask,askSize,bid,bidSize,dayHigh,dayLow,regularMarketDayHigh,regularMarketDayLow,regularMarketVolume,volume'
    
    def __init__(self):
        self._con = sqlite3.connect('stonks.db')
        self._cur = self._con.cursor()
        self._ensure_database()
        
        self.session = requests.Session()
        self.session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": f"https://{vars.STOCK_URL}",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "TE": "Trailers"
        }

    def _get_live_stock_prices(self, symbols: list):
        self.session.headers.update(
            {"Referer": self._referer_header.format(symbols[0]) }
        )
        stock_info = self.session.get(
            f"https://{vars.STOCK_API_URL}?&symbols={','.join(symbols)}&{self._bs_fields_param}"
        ).json()['quoteResponse']['result']
        
        return { stock['symbol']: stock['regularMarketPrice'] for stock in stock_info }
        
    def calculate_profit(self, user_id: str):
        """

            return:
                user_stock_val = {
                    '<SYMBOL>': {
                        'value': Total Money value, based on when stock was bought,
                        'shares': Number of shares bought of this item.
                        'profit': (value - current price of stock) * shares
                    },
                    'total_profit': Profit overall
                }
        """
        symbols = self._cur.execute(f"""
                    SELECT DISTINCT(symbol) FROM portfolios
                    WHERE user_id == '{user_id}'
            """).fetchall()
        symbols = [ symbol[0] for symbol in symbols]
        
        user_money = float(self._cur.execute(f"""
                    SELECT money FROM users
                    WHERE id == '{user_id}'
            """).fetchall()[0][0])
        if not symbols:
            return { 'total_pocket_cash': user_money, "total_profit": "?Unknown, stocks r sold" }
            
        user_stock_val = { symbol:{ 'value':0,'shares':0 } for symbol in symbols }
        
        stock_prices = self._get_live_stock_prices(symbols)
        
        user_inv = self._cur.execute(f"""
                    SELECT symbol,bought_at_price,shares FROM portfolios
                    WHERE user_id == '{user_id}'
            """).fetchall()
        
        for symbol, bought_at_price, shares in user_inv:
            user_stock_val[symbol]['value'] += (bought_at_price * shares)
            user_stock_val[symbol]['shares'] += shares
        
        for stock_symbol in user_stock_val:
            user_stock_val[stock_symbol]['profit'] = round(( stock_prices[stock_symbol] * user_stock_val[stock_symbol]['shares'] ) - user_stock_val[stock_symbol]['value'], 2 )
        
        user_stock_val['total_profit'] = sum([ stock['profit'] for stock in user_stock_val.values() ])
        
        user_stock_val['total_pocket_cash'] = user_money
        
        return user_stock_val

    def calculate_leaderboard(self):
        user_ids = self._cur.execute(f"""
                SELECT id FROM users
        """).fetchall()
        user_ids = [ user_id[0] for user_id in user_ids]
        
        
        user_stats = []
        for user_id in user_ids:
            user_profit = self.calculate_profit(user_id)
            user_stats.append((user_id, user_profit['total_profit'], user_profit['total_pocket_cash']))
        
        return user_stats

    def _ensure_database(self):
        sql_stmts = ["""
            CREATE TABLE IF NOT EXISTS users
            (
                id      TEXT    PRIMARY KEY     NOT NULL, 
                name    TEXT, 
                money   TEXT    NOT NULL
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS portfolios
            (
                id              INTEGER     PRIMARY KEY     AUTOINCREMENT,
                user_id         TEXT        NOT NULL, 
                symbol          TEXT        NOT NULL, 
                bought_at_price REAL        NOT NULL, 
                shares          INTEGER     NOT NULL, 
                bought_at_ts    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
            )
        """
        ]
        for statement in sql_stmts:
            self._cur.execute(statement)
        self._con.commit()

    def add_user(self, userid: str, name: str):
        try:
            self._cur.execute(f"""
                    INSERT INTO users VALUES
                    ('{userid}', '{name}', 20000)
                """)
            self._con.commit()
        except sqlite3.IntegrityError as ex:
            pass

    def add_user_stock(self, user_id: str, stock_request: list):
        """[summary]

        Args:
            user_id ([str]): discord id
            stock_request ([list]): [ [ symbol: str, shares: int],... ]
        """
        stock_prices = self._get_live_stock_prices([ stock[0] for stock in stock_request])
        
        # clean up dumbass requests
        stock_request = [ stock for stock in stock_request if stock[0] in stock_prices]
        if not stock_request:
            logger.info('[%s]\' Requests were not real stonks', user_id)
            return
        
        total_price_req = 0
        for stock, share_amt in stock_request:
            total_price_req += (stock_prices[stock] * share_amt)
        
        user_money = float(self._cur.execute(f"""
                            SELECT money from users
                            WHERE id == '{user_id}'
                        """).fetchall()[0][0])
        
        if user_money < total_price_req:
            logger.info("[%s] trying to buy $[%s], but has [%s]", 
                            user_id, total_price_req, user_money )
            return
        
        # Remove user's money
        self._cur.execute(f"""
                    UPDATE users
                    SET money = {user_money - total_price_req}
                    WHERE id == '{user_id}'
            """)
        
        # Add user's stocks
        for symbol, shares in stock_request:
            self._cur.execute(f"""
                    INSERT INTO portfolios 
                    (user_id,       symbol,         bought_at_price,        shares)
                    VALUES
                    ('{user_id}',   '{symbol}',    {stock_prices[symbol]},    {shares})
                """)

        self._con.commit()

    def sell_user_stock(self, user_id: str, stock_request: list):
        """we mess up real hard with the previous implemtation of adding 
            stocks. So this is going to be mess... TODO FIX

        Args:
            user_id (str):  discord id
            stock_request (list): [ [ symbol, shares],... ]
        """
        stock_prices = self._get_live_stock_prices([ stock[0] for stock in stock_request])
        stock_request = [ stock for stock in stock_request if stock[0] in stock_prices]
        
        for symbol, shares_to_sell in stock_request:
            user_stock_info = self._cur.execute(f"""
                    SELECT id,shares FROM portfolios
                    WHERE 
                            user_id == '{user_id}' 
                        AND
                            symbol == '{symbol}'
            """)
            user_stock_info = { info[0]: info[1]  for info in user_stock_info }
            user_money = float(self._cur.execute(f"""
                    SELECT money from users
                    WHERE id == '{user_id}'
            """).fetchall()[0][0])
            for id, shares in user_stock_info.items():
                if shares_to_sell == 0:
                    break
                
                if shares_to_sell >= shares:
                    user_stock_info = self._cur.execute(f"""
                            DELETE FROM portfolios 
                            WHERE id == {id}
                    """)
                    self._con.commit()
                    
                    self._cur.execute(f"""
                        UPDATE users
                        SET money = {user_money + (stock_prices[symbol] * shares) }
                        WHERE id == '{user_id}'
                    """)
                    # not sure if you gotta commit errtime, but we doing it
                    self._con.commit()
                    
                    shares_to_sell -= shares
                else:
                    self._cur.execute(f"""
                        UPDATE portfolios
                        SET shares = {shares - shares_to_sell}
                        WHERE id == {id}
                    """)
                    self._con.commit()
                    
                    self._cur.execute(f"""
                        UPDATE users
                        SET money = {user_money + (stock_prices[symbol] * (shares - shares_to_sell)) }
                        WHERE id == '{user_id}'
                    """)
                    # not sure if you gotta commit errtime, but we doing it
                    self._con.commit()
                    break
        
    def shutdown(self):
        self._con.close()


if __name__ == "__main__":
    # manual testing stuff
    monitor = StonkMonitor()
    user_id = "coom-000-yeet"
    stock_request = [ 
        ['DOGE-USD', 1000],
        ['TSLA', 3],
        ['asfg', 2]
    ]
    
    monitor.add_user("coom-000-yeet","coomsy")
    monitor.add_user_stock(user_id, stock_request)
    
    
    print(monitor._cur.execute("SELECT * FROM users").fetchall())
    print(monitor._cur.execute("SELECT * FROM portfolios").fetchall())
    print(monitor.calculate_profit("coom-000-yeet") )
    print(monitor.calculate_leaderboard())
    monitor.shutdown()
    
    
    
    
# datetime.datetime.strptime("2021-05-22 15:45:32.618593", "%Y-%m-%d %H:%M:%S.%f")
