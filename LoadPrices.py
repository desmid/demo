###########################################################################
import sys
import os
import re

###########################################################################
# LibreOffice/OpenOffice globals
###########################################################################
DOC = XSCRIPTCONTEXT.getDocument()

###########################################################################
# start logging
# https://docs.python.org/3/howto/logging.html#logging-advanced-tutorial
###########################################################################
import logging

LOGFILE = '/home/brown/TRADE/SOFTWARE/LibreOffice/out.log'
LOGFORMAT = '%(asctime)s %(name)s %(levelname)s - %(message)s'
LOGLEVEL = logging.DEBUG

Logger = logging.getLogger('LoadPrices')
Logger.setLevel(LOGLEVEL)

handler = logging.FileHandler(LOGFILE)
handler.setFormatter(logging.Formatter(LOGFORMAT))
Logger.addHandler(handler)
del handler

Logger.debug("Start")

###########################################################################
# embedded pythonpath and imports
###########################################################################
import uno

PYTHONPATH = '/Scripts/python/pythonpath'

pythonpath = uno.fileUrlToSystemPath(DOC.URL) + PYTHONPATH
if pythonpath not in sys.path: sys.path.append(pythonpath)
del pythonpath

Logger.debug("New path: " + str(sys.path))

#embedded imports go here:
#import mymodule

###########################################################################
# the macros
###########################################################################
YAHOO_PRICE = 1
YAHOO_FX    = 2

def get_yahoo_prices(*args):
    yahoo_get(YAHOO_PRICE, 'Sheet1', keys='A2:A200', datacols=['B', 'C'])
    messageBox("Processing finished", "Status")

def get_yahoo_fx(*args):
    yahoo_get(YAHOO_FX, 'Sheet1', keys='G2:G200', datacols=['H'])
    yahoo_get(YAHOO_FX, 'Sheet1', keys='J2:J200', datacols=['I'])
    messageBox("Processing finished", "Status")

###########################################################################
# macro guts
###########################################################################
def yahoo_get(mode, sheetname='Sheet1', keys='A2:A200', datacols=['B']):
    if mode not in (YAHOO_PRICE, YAHOO_FX):
        raise KeyError("yahoo_get: unknown mode '{}'".format(mode))

    sheet = DOC.getSheets().getByName(sheetname)

    keyrange = range2posn(keys)
    datacols = [name2posn(i)[0] for i in datacols]

    symbols = sheet_read_symbols(sheet, keyrange, mode)
    sheet_clear_columns(sheet, keyrange, datacols)

    url = yahoo_build_url(symbols, mode)
    text = get_html(url)
    values = yahoo_parse_json(text)

    sheet_write_columns(sheet, keyrange, datacols, values)

def yahoo_build_url(symbols, mode):
    URL = 'https://query1.finance.yahoo.com/v7/finance/quote?'

    if mode == YAHOO_PRICE:
        return URL + 'symbols=' + ','.join(symbols)

    if mode == YAHOO_FX:
        #convert each symbol EURUSD to EURUSD=X
        sym = [s+'=X' for s in symbols]
        return URL + 'symbols=' + ','.join(sym)

    return ''

#rewrite of LemonFool:SimpleYahooPriceScrape.py:createPriceDict
def yahoo_parse_json(text):
    m = re.search(r'.*?\[(.*?)\].*', text)
    if not m: return {}
    text = m.group(1)

    #data[ticker] = [regularMarketPrice, currency]
    data = { '%formats' : ['%f', '%s'] }

    while text:
        m = re.search(r'.*?{(.*?)\}(.*)', text)
        if not m: break

        symbolData = m.group(1)
        symbol, price, currency = '', '', ''

        for element in symbolData.split(','):
            element = element.replace('"','')
            try:
                key,val = element.split(':', 1)
            except:
                continue

            if 'symbol' == key:
                symbol = val.replace('=X', '')
                continue

            if 'regularMarketPrice' == key:
                price = val
                continue

            if 'currency' == key:
                currency = val.replace('GBp', 'GBX')
                continue

        Logger.debug("ypj: %s,%s,%s", symbol,price,currency)

        data[symbol] = [price, currency]
        text = m.group(2)

    return data

###########################################################################
# spreadsheet utilities
###########################################################################
def name2posn(n=''):
    """Return spreadsheet cell names ('A1', AZ2', etc.) as a tuple of
    0-based positions.

    - Ignores $ signs.
    - Harmlessly allows row 0 (treats as row 1).

    Example usage and return values:

    name2posn('')    =>  (0,0)
    name2posn('0')   =>  (0,0)
    name2posn('A')   =>  (0,0)
    name2posn('A0')  =>  (0,0)
    name2posn('A1')  =>  (0,0)

    name2posn('B')   =>  (1,0)
    name2posn('B0')  =>  (1,0)
    name2posn('B1')  =>  (1,0)
    name2posn('B2')  =>  (1,1)
    name2posn('Z')   =>  (25,0)
    name2posn('AA')  =>  (26,0)
    name2posn('AZ')  =>  (51,0)
    name2posn('BA')  =>  (52,0)
    name2posn('ZZ')  =>  (701,0)
    name2posn('AAA') =>  (702,0)
    """
    if isinstance(n, int):
        if n < 0: n = 0
        return (n,n)
    if not isinstance(n, str): return (0,0)
    n = re.sub('[^A-Z0-9:]', '', str(n).upper())
    #0-based arithmetic
    if n is '': n = '1'
    c,r,ordA = 0,0,ord('A')
    while len(n) > 0:
        v = ord(n[0])
        if v < ordA:
            r = int(n)
            break
        #print(n, v, c, r)
        c = 26*c + v-ordA+1
        #print(n, v, c, r)
        n = n[1:]
    if c > 0: c -= 1
    if r > 0: r -= 1
    return (c,r)

def range2posn(n=''):
    """Return spreadsheet cell name ranges ('A1:A10', B10:G100', etc.) as a
    tuple of pairs of 0-based positions.

    - Ignores $ signs.
    - Harmlessly allows row 0 (treats as row 1).

    Example usage and return values:

    range2posn()          =>  ((0,0), (0,0))
    range2posn('')        =>  ((0,0), (0,0))
    range2posn('A:Z')     =>  ((0,0), (25,0))
    range2posn('A1:A99')  =>  ((0,0), (0,98))
    range2posn('A1:C3')   =>  ((0,0), (2,2))
    """
    if isinstance(n, int): return (name2posn(n), name2posn(n))
    if not isinstance(n, str): return (name2posn(n), name2posn(n))
    try:
        c,r = n.split(':')
    except:
        c = n.split(':')[0]
        r = c
    if c == '': c = '0'
    if r == '': r = '0'
    return (name2posn(c), name2posn(r))

###########################################################################
def sheet_read_symbols(sheet, posn, mode):
    if mode == YAHOO_PRICE:
        p = re.compile(r'[A-Z0-9]+\.[A-Z]')
    elif mode == YAHOO_FX:
        p = re.compile(r'[A-Za-z]')
    else:
        p = re.compile(r'^$')
    return [s for s in sheet_read_column(sheet, posn) if p.match(s)]

def sheet_read_column(sheet, posn):
    ((keycol,rowfirst), (_, rowlast)) = posn
    return [
        sheet.getCellByPosition(keycol, row).getString()
        for row in range(rowfirst, rowlast+1)
    ]

def sheet_clear_columns(sheet, keyrange, datacols, flags=5):
    """
    http://www.openoffice.org/api/docs/common/ref/com/sun/star/sheet/CellFlags.html
    """
    ((keycol,rowfirst), (_, rowlast)) = keyrange
    for row in range(rowfirst, rowlast+1):
        key = sheet.getCellByPosition(keycol, row).getString()
        for col in datacols:
            cell = sheet.getCellByPosition(col, row)
            item = cell.getString()
            #print("clear({},{})={}".format(col, row, item))
            cell.clearContents(flags)
        row += 1

def sheet_write_columns(sheet, keyrange, datacols, datadict):
    if len(datadict) < 1: return
    formats = datadict['%formats']
    ((keycol,rowfirst), (_, rowlast)) = keyrange
    for row in range(rowfirst, rowlast+1):
        key = sheet.getCellByPosition(keycol, row).getString()
        try:
            data = datadict[key]
        except KeyError:
            row += 1
            continue
        for i,col in enumerate(datacols):
            cell = sheet.getCellByPosition(col, row)
            if formats[i] == '%f':
                value = float(data[i])
                #print("write({},{},{})={}".format(col, row, key, value))
                cell.Value = value
            elif formats[i] == '%s':
                value = str(data[i])
                #print("write({},{},{})={}".format(col, row, key, value))
                cell.String = value
            else:
                value = str(data[i])
                #print("write({},{},{})={}".format(col, row, key, value))
                cell.String = value
        row += 1


###########################################################################
# spreadsheet controls
# adapted from LemonFool:SimpleYahooPriceScrape.py
###########################################################################
from com.sun.star.awt.VclWindowPeerAttribute import OK, OK_CANCEL, YES_NO, \
    YES_NO_CANCEL, RETRY_CANCEL, DEF_OK, DEF_CANCEL, DEF_RETRY, DEF_YES, DEF_NO

# Our arbitrary mappings, for use by the caller:
#     OK = 1
#    YES = 2
#     NO = 3
# CANCEL = 4

# Message box test for OO or LO version
# Uses either messageBoxOO4 or messageBoxLO4. Pretty much pot luck which one
# works, depending on which version of OpenOffice or LibreOffice is used
def messageBox(msgText, msgTitle, msgButtons = OK):
    parentWin = DOC.CurrentController.Frame.ContainerWindow
    try:
        msgRet = messageBoxLO4(parentWin, msgText, msgTitle, msgButtons)
    except:
        ctx = XSCRIPTCONTEXT.getComponentContext()
        msgRet = messageBoxOO4(parentWin, ctx, msgText, msgTitle, msgButtons)
    return msgRet

# Following works with OO4 and LO5 but not LO4 or OO Portable 3.2
# Needs numeric msgButtons 1,2,3 etc so translated by buttonDict
def messageBoxOO4(parentWin, ctx, MsgText, MsgTitle, msgButtons):
    buttonDict = {OK: 1, OK_CANCEL: 2, YES_NO: 3, YES_NO_CANCEL: 4}
    msgButtons = buttonDict[msgButtons]
    toolkit = ctx.getServiceManager().createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    msgbox = toolkit.createMessageBox(parentWin, 0, msgButtons, MsgTitle, MsgText)
    msgRet =  msgbox.execute()
    return msgRet

# Show a message box with the UNO based toolkit.
# Works with LO4 and OOP3.2
# Does NOT work with LO 4.2.3.3
def messageBoxLO4(parentWin, MsgText, MsgTitle, msgButtons):
    #describe window properties.
    aDescriptor = WindowDescriptor()
    aDescriptor.Type = 1                       #MODALTOP
    aDescriptor.WindowServiceName = "messbox"
    aDescriptor.ParentIndex = -1
    aDescriptor.Parent = parentWin
    aDescriptor.WindowAttributes = msgButtons
    tk = parentWin.getToolkit()
    msgbox = tk.createWindow(aDescriptor)
    msgbox.setMessageText(MsgText)
    msgbox.setCaptionText(MsgTitle)
    msgRet = msgbox.execute()
    return msgRet

###########################################################################
# general utilities
# adapted from LemonFool:SimpleYahooPriceScrape.py
###########################################################################
import socket
try:
    import urllib.request
except:
    import urllib

WEB_TIMEOUT  = 10  #seconds
WEB_MAXTRIES = 5

def get_html(url, timeout=WEB_TIMEOUT, maxtries=WEB_MAXTRIES):

    if not isinstance(timeout, int): timeout = 1
    if timeout < 1: timeout = 1
    if not isinstance(maxtries, int): maxtries = 1
    if maxtries < 1: maxtries = 1

    hdr = {
        'User-Agent': 'Mozilla/5.0 AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'
    }
    html = 'No Response'

    tries = 1
    while True:
        if tries > maxtries: break
        socket.setdefaulttimeout(timeout)
        try:
            if sys.version[0] == '3':
                req = urllib.request.Request(url=url, headers=hdr)
                response = urllib.request.urlopen(req)
            else:
                #data = urllib.urlencode(values)
                req = urllib2.Request(url, None, hdr)
                response = urllib2.urlopen(req)
            html = response.read()
            html = html.decode('1252', 'ignore')
            break
        except Exception as e:
            tries += 1
            timeout *= 2

    return html

###########################################################################
g_exportedScripts = get_yahoo_prices, get_yahoo_fx,
###########################################################################
