from flask import Flask, request, abort, render_template
from open_position import OpenPosition
from order import Order
from capital import Capital
from cbpro import AuthenticatedClient
from cbpro import PublicClient
from dict import new_dict
from indicators import *
from app_methods import *
import Data

app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def application():
    if request.method == 'POST':

        new_request = request.get_json(force=True)

        new_ticker = None

        if "ticker" in new_request:

            # ticker converted into a Coinbase product id
            new_ticker = get_ticker('ticker', new_request)

        opening = 0
        close = 0

        if ("hist" in new_request) and (float(new_request['hist']) > 0):

            if "opening_price" in new_request:
                opening = float(new_request["opening_price"])

            if "closing_price" in new_request:
                close = float(new_request['closing_price'])

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

        elif (close > 0 and opening > 0) and (close >= opening):

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

        macd_5m = MACD()
        volume_5m = VolSMA(timeperiod=20)
        bands_2dev = BB()
        bands_1dev = BB(ndbevup=1, nbdevdn=1)
        rsi_5m = RSI()
        ema_12p = EMA()

        if len(indicator.candles) > 0:

            try:
                indicator.get_data_set()
                indicator.reverse_data()
                indicator.get_np_array()

                macd_5m.np_array = indicator.np_array
                macd_5m.get_MACD()

                bands_2dev.np_array = indicator.np_array
                bands_2dev.get_BB()

                bands_1dev.np_array = indicator.np_array
                bands_1dev.get_BB()

                rsi_5m.np_array = indicator.np_array
                rsi_5m.get_RSI()

                ema_12p.np_array = indicator.np_array
                ema_12p.get_EMA()

                volume_5m.candles = indicator.candles
                volume_5m.get_data_set()
                volume_5m.reverse_data()
                volume_5m.get_np_array()
                volume_5m.get_volume()

            except Exception:
                print("indicators failed for: " + new_ticker)
                print(indicator.candles)
                pass

        else:
            #try setting candles again
            pass

        #Asserts stock is at a bottom
        is_bottom = False
        bottom_rule_used = None

        # Assert is a stock is raising
        is_raising = False
        raising_rule = None

        #Assert if a stock is at the top
        is_top = False
        top_rule = None

        #Assert is stock is falling from top
        is_falling = False
        falling_rule = None

        successful_analysis = False

        if len(volume_5m.real) > 0:

            try:

                # Asserts stock is at a bottom
                if (indicator.data_array[-1] < bands_2dev.lowerband[-1]) or (indicator.data_array[-2] < bands_2dev.lowerband[-2]) and (0 > macd_5m.hist[-1] > macd_5m.hist[-2]):
                    is_bottom = False
                    bottom_rule_used = str(indicator.data_array[-1]) + " < " + str(bands_2dev.lowerband[-1]) + " or " + str(indicator.data_array[-2]) + " < " + str(bands_2dev.lowerband[-2]) + " and 0 > " + str(macd_5m.hist[-1]) + " > " + str(macd_5m.hist[-2])

                elif (bands_2dev.lowerband[-1] < indicator.data_array[-1] < bands_1dev.lowerband[-1]) and (macd_5m.hist[-1] > macd_5m.hist[-2]) or (indicator.data_array[-1] > indicator.data_array[-2]):
                    is_bottom = True
                    bottom_rule_used = str(bands_2dev.lowerband[-1]) + " < " + str(indicator.data_array[-1]) + " < " + str(bands_1dev.lowerband[-1]) + " and " +  str(macd_5m.hist[-1]) + " > " + str(macd_5m.hist[-2]) + " or " + str(indicator.data_array[-1]) + " > " + str(indicator.data_array[-2])

                elif (indicator.data_array[-1] < bands_1dev.lowerband[-1]) and (0 < macd_5m.hist[-2] < macd_5m.hist[-1]):
                    is_bottom = True
                    bottom_rule_used = str(indicator.data_array[-1]) + " < " + str(bands_1dev.lowerband[-1]) + " and 0 < " + str(macd_5m.hist[-2]) + " < " + str(macd_5m.hist[-1])

                elif (rsi_5m.real[-1] < 40) and (macd_5m.macd[-1] > macd_5m.macd[-2]) and (indicator.data_array[-1] < ema_12p.real[-1]):
                    is_bottom = True
                    bottom_rule_used = str(rsi_5m.real[-1]) + " < 40  and " + str(macd_5m.macd[-1]) + " > " + str(macd_5m.macd[-2]) + " and " + str(indicator.data_array[-1]) + " < " + str(ema_12p.real[-1])

                elif (indicator.data_array[-2] < bands_1dev.lowerband[2]) and (indicator.data_array[-1] > indicator.data_array) and (macd_5m.hist > 0 > macd_5m.hist[-2]):
                    is_bottom = True
                    bottom_rule_used = str(indicator.data_array[-2]) + " < " + str(bands_1dev.lowerband[2]) + " and " + str(indicator.data_array[-1]) + " > " + str(indicator.data_array) + " and " + str(macd_5m.hist) + " >  0 > " + str(macd_5m.hist[-2])

                elif rsi_5m.real[-1] < 30:
                    is_bottom = True
                    bottom_rule_used = str(rsi_5m.real[-1]) + " < 30"

                else:
                    is_bottom = False
                    bottom_rule_used = "not at bottom "
                    #bottom_rule_used = str(indicator.data_array[-1]) + " " + str(macd_5m.hist[-1]) + " " + str(macd_5m.macd[-1]) + " " + str(bands_2dev.lowerband[-1]) + " " + str(bands_1dev.lowerband[-1]) + " " + str(rsi_5m.real[-1])

            except Exception:
                print(bottom_rule_used)

            try:

                # Assert is a stock is raising
                if (bands_2dev.upperband[-1] > indicator.data_array[-1] > bands_1dev.upperband[-1]) and (macd_5m.hist[-1] > macd_5m.hist[-2]):
                    is_raising = True
                    raising_rule = str(bands_2dev.upperband[-1]) + " > " + str(indicator.data_array[-1]) + " > " + str(bands_1dev.upperband[-1]) + " and " + str(macd_5m.hist[-1]) + " > " + str(macd_5m.hist[-2])

                elif (indicator.data_array[-1] < bands_1dev.lowerband[-1]) and (macd_5m.hist[-1] > macd_5m.hist[-2]) and (rsi_5m.real[-1] > rsi_5m.real[-2]):
                    is_raising = True
                    raising_rule = str(indicator.data_array[-1]) + " < " + str(bands_1dev.lowerband[-1]) + " and " + str(macd_5m.hist[-1]) + " > " + str(macd_5m.hist[-2]) + " and " + str(rsi_5m.real[-1]) + " > " + str(rsi_5m.real[-2])

                else:
                    is_raising = False
                    raising_rule = "no raising"

            except Exception:
                print(raising_rule)

            try:

                # Assert if a stock is at the top
                if (indicator.data_array[-1] > bands_2dev.upperband[-1]) and (rsi_5m.real[-1] > 70):
                    is_top = True
                    top_rule = str(indicator.data_array[-1]) + " > " + str(bands_2dev.upperband[-1]) + " and " + str(rsi_5m.real[-1]) + " > 70"

                else:
                    is_top = False
                    top_rule = "Not at top"

            except Exception:
                print(top_rule)

            try:

                # Assert is stock is falling from top
                if (bands_2dev.upperband[-2] > indicator.data_array[-2] > bands_1dev.upperband[-2]) and (indicator.data_array[-1] < bands_1dev.upperband[-1]):
                    is_falling = True
                    falling_rule = str(bands_2dev.upperband[-2]) + " > " + str(indicator.data_array[-2]) + " > " + str(bands_1dev.upperband[-2]) + " and " + str(indicator.data_array[-1]) + ' < ' + str(bands_1dev.upperband[-1])

                elif (indicator.data_array[-2] > bands_2dev.upperband[-2]) and (indicator.data_array[-1] < indicator.data_array[-2]):
                    is_falling = True
                    falling_rule = str(indicator.data_array[-2]) + " > " + str(bands_2dev.upperband[-2]) + " and " + str(indicator.data_array[-1]) + " < " + str(indicator.data_array[-2])

                elif bands_1dev.upperband[-1] < indicator.data_array[-1] < bands_2dev.upperband[-1] < float(indicator.candles[0][3]):
                    is_falling = True
                    falling_rule = str(bands_1dev.upperband[-1]) + " < " + str(indicator.data_array[-1]) + " < " + str(bands_2dev.upperband[-1]) + " < " + str(float(indicator.candles[0][3]))

                elif (bands_1dev.upperband[-1] > indicator.data_array[-1] > ema_12p.real[-1]) and (indicator.data_array[-2] > bands_1dev.upperband[-2]):
                    is_falling = True
                    falling_rule = str(bands_1dev.upperband[-1]) + " > " + str(indicator.data_array[-1]) + " > " + str(ema_12p.real[-1]) + " and " + str(indicator.data_array[-2]) + " > " + str(bands_1dev.upperband[-2])

                elif (ema_12p.real[-1] < ema_12p.real[-2] < ema_12p.real[-3]) and (0 > macd_5m.macd[-3] > macd_5m.macd[-2] > macd_5m.macd[-2]) and (0 > macd_5m.hist[-1] > macd_5m.hist[-2] > macd_5m.hist[-3]):
                    is_falling = True
                    falling_rule = str(ema_12p.real[-1]) + " < " + str(ema_12p.real[-2]) + " < " + str(ema_12p.real[-3]) + " and " + str(0 > macd_5m.macd[-3]) + " > " + str(macd_5m.macd[-2]) + " > " + str(macd_5m.macd[-2]) + " and 0 >" + str(macd_5m.hist[-1]) + " > " + str(macd_5m.hist[-2]) + " > " + str(macd_5m.hist[-3])

                else:
                    is_falling = False
                    falling_rule = "no falling"

            except Exception:
                print(falling_rule)

            successful_analysis = True

        else:
            # Means that the indicators could not be measured
            pass

        # If there is no a position opened it will trigger a buy order
        if position.get_position() is False:

            if successful_analysis:

                ready_to_trade: bool

                # Rules to make ready_to_trade True
                if (is_bottom or is_raising) and (is_top is False):

                    ready_to_trade = True

                else:
                    ready_to_trade = False

                #Will trigger a buy order if a rule is True
                if ready_to_trade:

                    new_trade = None

                    try:
                        new_trade = client.place_market_order(product_id=new_ticker, side="buy", funds=funds.get_capital())

                    except Exception as e:
                        print(e)

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
                            print("with: ")
                            print(str(top_rule) + ", " + str(bottom_rule_used) + ", " + str(raising_rule) + ", " + str(falling_rule))

                        else:
                            print("opening position details: ", new_trade)

                    else:
                        pass

                else:
                    print(new_ticker + ": " + str(top_rule) + ", " + str(bottom_rule_used) + ", " + str(raising_rule) + ", " + str(falling_rule))
                    # Does nothing if both statements are False
                    pass

            else:
                pass

        # If the Post request ticker is the same as the order's it will trigger a sell order
        elif position.get_position():

            ready_to_trade: bool

            #rules for when the request ticker is other than the position's:
            #rules for when the request ticker is the same as the position's
            #if (new_ticker == new_order.get_key("product_id")) and (float(new_request['hist']) < 0.0):
                #ready_to_trade = True

            if (is_falling or is_top) and ((is_bottom is False) and (is_raising is False)):
                ready_to_trade = True

            else:
                ready_to_trade = False

            #Triggers a sell order if a rule is met:
            if ready_to_trade and (time.time() > (get_unix(new_order.get_key("done_at")) + 3600.0)):

                new_trade = None

                try:
                    new_trade = client.place_market_order(product_id=new_order.get_key("product_id"), side='sell', size=get_size(new_order.get_key("product_id"), new_order.get_key('filled_size')))

                except Exception as e:
                    print(e)

                if "id" in new_trade:
                    writer = open(Data.Path, "w")
                    writer.write(new_trade['id'])
                    writer.close()
                    new_order.get_id()

                    if new_order.set_details():
                        print("order sent " + new_order.get_key('product_id'))
                        print("with: ")
                        print(top_rule + ", " + bottom_rule_used + ", " + raising_rule + ", " + falling_rule)

                        funds.capital = float(new_order.get_key('executed_value'))
                        position.set_position()

                    else:
                        pass

                else:
                    print("order details", new_trade)

            #Not rules were true
            else:
                print(new_ticker + ": " + str(top_rule) + ", " + str(bottom_rule_used) + ", " + str(raising_rule) + ", " + str(falling_rule))
                pass

        # If there is a long position but the ticker is not the same as the order's
        # the program will just ignore it
        else:
            pass

        return 'success', 200

    elif request.method == 'GET':
        return render_template('index.html')

    else:
        abort(400)
