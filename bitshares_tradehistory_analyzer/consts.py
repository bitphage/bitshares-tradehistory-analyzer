LINE_DICT_TEMPLATE = {
    'kind': '',
    'buy_cur': '',
    'buy_amount': 0,
    'sell_cur': '',
    'sell_amount': 0,
    'fee_cur': '',
    'fee_amount': 0,
    'exchange': 'Bitshares',
    'mark': -1,
    'comment': '',
    'order_id': '',
}

# CSV format is ccGains generic format
HEADER = 'Kind,Date,Buy currency,Buy amount,Sell currency,Sell amount,Fee currency,Fee amount,Exchange,Mark,Comment\n'

LINE_TEMPLATE = (
    '{kind},{date},{buy_cur},{buy_amount},{sell_cur},{sell_amount},{fee_cur},{fee_amount},{exchange},'
    '{mark},{comment}\n'
)
