generateSession(clientCode, password, totp)
"""
Authenticate the user and create a trading session.

Args:
    clientCode (str): Angel One client ID.
    password (str): Account password or trading PIN.
    totp (str): Time-based one-time password generated from the user's TOTP authenticator.

Returns:
    dict: Response containing authentication tokens and session data, including:
        - jwtToken (str): Access token used for API requests.
        - refreshToken (str): Token used to generate new access tokens.
        - feedToken (str): Token used for websocket market data feeds.
"""


generateToken(refreshToken)
"""
Generate a new JWT access token using an existing refresh token.

Args:
    refreshToken (str): Refresh token obtained during login.

Returns:
    dict: API response containing a new JWT token and session metadata.
"""


terminateSession(clientCode)
"""
Logout and terminate the current session.

Args:
    clientCode (str): Client ID of the logged-in user.

Returns:
    dict: Response indicating whether the logout was successful.
"""


getProfile(refreshToken)
"""
Retrieve profile information of the logged-in user.

Args:
    refreshToken (str): Refresh token associated with the session.

Returns:
    dict: User profile information including client details, permitted exchanges,
    and account metadata.
"""


placeOrder(orderparams)
"""
Place a trading order.

Args:
    orderparams (dict): Dictionary containing order parameters:
        variety (str): Order variety such as NORMAL, STOPLOSS, AMO.
        tradingsymbol (str): Trading symbol of the instrument.
        symboltoken (str): Unique token identifying the instrument.
        transactiontype (str): BUY or SELL.
        exchange (str): Exchange name such as NSE, BSE, NFO.
        ordertype (str): Order type such as MARKET, LIMIT, STOPLOSS_LIMIT.
        producttype (str): Product type such as INTRADAY, DELIVERY.
        duration (str): Order duration such as DAY or IOC.
        price (float): Order price (required for limit orders).
        squareoff (float): Square-off value for bracket orders (if applicable).
        stoploss (float): Stop-loss value for bracket orders.
        quantity (int): Number of shares or lots.

Returns:
    dict: API response containing order ID and order placement status.
"""


modifyOrder(orderparams)
"""
Modify an existing open order.

Args:
    orderparams (dict): Dictionary containing modification parameters:
        orderid (str): Unique order identifier.
        quantity (int): Updated quantity.
        price (float): Updated price for limit orders.
        ordertype (str): Updated order type if applicable.

Returns:
    dict: API response indicating whether the modification was successful.
"""


cancelOrder(order_id, variety)
"""
Cancel an existing order.

Args:
    order_id (str): Unique order identifier returned during order placement.
    variety (str): Order variety (NORMAL, STOPLOSS, etc.).

Returns:
    dict: Response confirming whether the order cancellation was successful.
"""


orderBook()
"""
Retrieve all orders placed in the trading account.

Returns:
    dict: List of orders with details such as order ID, symbol, price,
    quantity, order status, and timestamps.
"""


tradeBook()
"""
Retrieve executed trades from the account.

Returns:
    dict: List of completed trades including execution price,
    traded quantity, symbol, and trade time.
"""


position()
"""
Fetch all current trading positions.

Returns:
    dict: List of open and closed positions including symbol,
    quantity, average price, and profit/loss information.
"""


holding()
"""
Retrieve stock holdings in the user's demat account.

Returns:
    dict: List of securities currently held in the portfolio,
    including quantity, average purchase price, and exchange details.
"""


convertPosition(positionParams)
"""
Convert a position from one product type to another.

Args:
    positionParams (dict): Dictionary containing conversion parameters:
        exchange (str): Exchange name.
        symboltoken (str): Instrument token.
        quantity (int): Quantity to convert.
        oldproducttype (str): Current product type.
        newproducttype (str): Target product type.

Returns:
    dict: Response confirming whether the position conversion succeeded.
"""


ltpData(exchange, tradingsymbol, symboltoken)
"""
Retrieve the latest traded price (LTP) of a specific instrument.

Args:
    exchange (str): Exchange name such as NSE or BSE.
    tradingsymbol (str): Trading symbol of the instrument.
    symboltoken (str): Unique identifier of the instrument.

Returns:
    dict: Market data response containing the latest traded price
    and related metadata.
"""


getMarketData(mode, exchangeTokens)
"""
Fetch market data for multiple instruments.

Args:
    mode (str): Data mode specifying level of detail:
        LTP  - Latest traded price
        OHLC - Open, High, Low, Close
        FULL - Full quote information
    exchangeTokens (dict): Dictionary mapping exchange names to lists of symbol tokens.

Returns:
    dict: Market data response containing quote information
    for the requested instruments.
"""


getCandleData(historicDataParams)
"""
Retrieve historical candle data for an instrument.

Args:
    historicDataParams (dict): Parameters for fetching historical data:
        exchange (str): Exchange name.
        symboltoken (str): Instrument token.
        interval (str): Candle interval such as ONE_MINUTE, FIVE_MINUTE, DAY.
        fromdate (str): Start date and time for the data range.
        todate (str): End date and time for the data range.

Returns:
    dict: Historical OHLC candle data for the specified instrument and time range.
"""


searchScrip(exchange, searchscrip)
"""
Search for instruments by name or symbol.

Args:
    exchange (str): Exchange to search within.
    searchscrip (str): Symbol or keyword used to find instruments.

Returns:
    dict: List of matching instruments including symbol token,
    trading symbol, and exchange information.
"""


rmsLimit()
"""
Retrieve account risk and margin limits.

Returns:
    dict: Risk management details including available margin,
    utilized margin, exposure limits, and collateral information.
"""