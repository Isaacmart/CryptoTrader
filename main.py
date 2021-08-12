from flask import Flask, request, abort, render_template, redirect, url_for
from open_position import OpenPosition
from order import Order
from capital import Capital
from cbpro import AuthenticatedClient
from cbpro import PublicClient
from indicators import Indicator
from indicators import MACD
from indicators import BB
from indicators import RSI
from indicators import VolSMA
from indicators import EMA
from app_methods import get_time
from app_methods import get_ticker
from app_methods import last_instance
from app_methods import get_size
from strategies import Strategy
import time
import Data

app = Flask(__name__)

#This is the debug mode of the actual application that will execute trades automatically, hence why it is printing
#to stdio. It does it so that way the print statements can be accessed in the error log
#The actual application will store all the logs errors


@app.route("/", methods=['GET', 'POST'])
def application():

    if request.method == 'POST':

        new_request = request.get_json(force=True)

        new_ticker: str

        if "ticker" in new_request:

            # ticker converted into a Coinbase product id
            new_ticker = get_ticker('ticker', new_request)

        else:
            new_ticker = ""

        client = AuthenticatedClient(Data.API_Public_Key, Data.API_Secret_Key, Data.Passphrase)

        new_order = Order(client)
        new_order.get_id()
        new_order.set_details()

        position = OpenPosition(new_order)
        position.set_position()

        funds = Capital(client)
        funds.set_capital()

        p_client = PublicClient()
        indicator = Indicator()
        indicator.initiate_client(p_client)

        macd_5m = MACD()
        volume_5m = VolSMA(timeperiod=20)
        bands_2dev = BB()
        bands_1dev = BB(ndbevup=1, nbdevdn=1)
        rsi_5m = RSI()
        ema_12p = EMA()

        if position.get_position() and last_instance():

            try:
                indicator.set_candles(product=new_order.get_key("product_id"), callback=get_time(27976), begin=get_time(0), granularity=300)

            except ValueError:
                print(new_ticker)
                print(indicator.candles)
                #wait to make another request
                pass

            writer = open(Data.Time, "w")
            writer.write(str(time.time()))
            writer.close()

        elif "hist" in new_request:

            try:
                indicator.set_candles(product=new_ticker, callback=get_time(27976), begin=get_time(0), granularity=300)

            except ValueError:
                print(new_ticker)
                print(indicator.candles)
                #wait to make another request
                pass

        else:
            #get candles for previous tickers
            pass

        if len(indicator.candles) > 0:

            try:
                indicator.get_data_set()
                indicator.reverse_data()
                indicator.get_np_array()
            except Exception:
                print("indicators failed for: " + new_ticker)
                print(indicator.candles)

            try:
                macd_5m.np_array = indicator.np_array
                macd_5m.get_MACD()
            except Exception:
                print("macd failed for: " + new_ticker)
                print(indicator.candles)

            try:
                bands_2dev.np_array = indicator.np_array
                bands_2dev.get_BB()
            except Exception:
                print("bands_2dev failed for: " + new_ticker)
                print(indicator.candles)

            try:
                bands_1dev.np_array = indicator.np_array
                bands_1dev.get_BB()
            except Exception:
                print("bands_1dev failed for: " + new_ticker)
                print(indicator.candles)

            try:
                rsi_5m.np_array = indicator.np_array
                rsi_5m.get_RSI()
            except Exception:
                print("rsi failed for: " + new_ticker)
                print(indicator.candles)

            try:
                ema_12p.np_array = indicator.np_array
                ema_12p.get_EMA()
            except Exception:
                print("ema_12 failed for: " + new_ticker)
                print(indicator.candles)

            try:
                volume_5m.candles = indicator.candles
                volume_5m.get_data_set()
                volume_5m.reverse_data()
                volume_5m.get_np_array()
                volume_5m.get_volume()
            except Exception:
                print("volume_ema failed for: " + new_ticker)
                print(indicator.candles)

        else:
            #try setting candles again
            pass

        if len(volume_5m.real) > 0:

            strategy_5m = Strategy(indicator, macd_5m, bands_1dev, bands_2dev, volume_5m, rsi_5m, ema_12p, new_order)
            strategy_5m.strategy(-1)

        else:
            # Means that the indicators could not be measured
            pass

        # If there is no a position opened it will trigger a buy order
        if position.get_position() is False:

            # Rules to make ready_to_trade True
            if new_order.get_bottom() and not new_order.get_top() and not new_order.get_fall():

                new_trade = client.place_market_order(product_id=new_ticker, side="buy", funds=funds.get_capital())

                if "id" in new_trade:

                    writer = open(Data.Path, "w")
                    writer.write(new_trade['id'])
                    writer.close()
                    new_order.get_id()

                    if new_order.set_details():

                        position.set_position()

                        writer = open(Data.Time, "w")
                        writer.write(str(time.time()))
                        writer.close()

                        print("order sent: ", new_order.details)

                    else:
                        print("opening position details: ", new_trade)

                else:
                    print(new_ticker + " " + str(new_trade))
                    pass

            else:
                print(new_ticker + ": " + str(strategy_5m.order.is_bottom) + ", " + str(strategy_5m.order.is_raising) + ", " + str(strategy_5m.order.is_top) + ", " + str(strategy_5m.order.is_falling))
                # Does nothing if both statements are False
                pass

        # If the Post request ticker is the same as the order's it will trigger a sell order
        elif position.get_position():

            #rules for when the request ticker is other than the position's:
            #rules for when the request ticker is the same as the position's
            #if (new_ticker == new_order.get_key("product_id")) and (float(new_request['hist']) < 0.0):
                #ready_to_trade = True

            ready_to_trade: bool

            if new_order.get_top() and not new_order.get_bottom() and not new_order.get_rise():
                ready_to_trade = True

            else:
                ready_to_trade = False

            #Triggers a sell order if a rule is met:
            if ready_to_trade:

                new_trade = client.place_market_order(product_id=new_order.get_key("product_id"), side='sell', size=get_size(new_order.get_key("product_id"), new_order.get_key('filled_size')))

                if "id" in new_trade:
                    writer = open(Data.Path, "w")
                    writer.write(new_trade['id'])
                    writer.close()
                    new_order.get_id()

                    if new_order.set_details():
                        print("order sent " + new_order.get_key('product_id'))
                        funds.capital = float(new_order.get_key('executed_value'))
                        position.set_position()

                    else:
                        pass

                else:
                    print("order details", new_trade)

            #Not rules were true
            else:
                print(new_ticker + ": " + str(strategy_5m.order.is_bottom) + ", " + str(strategy_5m.order.is_raising) + ", " + str(strategy_5m.order.is_top) + ", " + str(strategy_5m.order.is_falling))
                pass

        # If there is a long position but the ticker is not the same as the order's
        # the program will just ignore it
        else:
            pass

        return 'success', 200

    elif request.method == 'GET':
        return redirect('http://3.218.228.129/login')

    else:
        abort(400)


@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            return render_template('index.html')
    return render_template('login.html', error=error)
