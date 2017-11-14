###########################################################################
import logging
Logger = logging.getLogger('LoadPrices')
Logger.debug("Load: Cell")

###########################################################################
import re

ORD_A = ord('A')

class Cell(object):
    """
    Represent a spreadsheet cell coordinate. Create with a zero-based
    numeric pair (column, row) or a name string, equivalently:
    
    Cell(0,2)  #column 0, row 2
    Cell('A3') #ditto, but as written on the spreadsheet

    Ignores $ signs.

    Raises TypeError if:
    - 2 argument form
      - any numerical coordinate is not integer
      - any numerical coordinate < zero
    - 1 argument form:
      - name coordinate is not string
      - name row coordinate < 1

    Methods:

    posn()  returns the 0-based (column, row) coordinate as a tuple;
    name()  returns a named coordinate string.
    """

    def __init__(self, *args):
        if len(args) == 0:
            self._set_by_posn()
            return

        if len(args) == 1:
            self._set_by_name(*args)
            return

        if len(args) == 2:
            self._set_by_posn(*args)
            return

        raise TypeError(
            "Cell() takes 0, 1, 2 arguments ({} supplied)".format(len(*args))
        )

    def posn(self): return (self.col, self.row)

    def name(self): return self._posn2name((self.col, self.row))

    def _set_by_posn(self, col=0, row=0):
        #check type
        if not isinstance(col, int) or not isinstance(row, int):
            raise TypeError("cell positions must be integers")
        #check sign
        if col < 0 or row < 0:
            raise TypeError("cell positions cannot be negative")

        self.col = col
        self.row = row

    def _set_by_name(self, name=''):
        #check type
        if not isinstance(name, str):
            raise TypeError("cell name must be a string")
        #check not a cell range
        if name.find(':') > -1:
            raise TypeError("cell name must not be a range")

        name = str(name).upper().strip()
        name = re.sub('\$', '', name)

        if name == '':
            (self.col, self.row) = (0, 0)
            return

        m = re.search(r'^(?:[A-Z]+)?([0-9]+)$', name)

        #check numeric row part
        if m and int(m.group(1)) < 1:
            raise TypeError("cell name row part must be integer")

        (self.col, self.row) = self._name2posn(name)

    def _name2posn(self, n=''):
        """Convert spreadsheet cell names ('A1', AZ2', etc.) and return a
        pair of 0-based positions as a tuple: (column, row).

        Example usage and return values:

        _name2posn('')     =>  (0,0)
        _name2posn('0')    =>  (0,0)
        _name2posn('A')    =>  (0,0)
        _name2posn('A0')   =>  (0,0)
        _name2posn('A1')   =>  (0,0)

        _name2posn('B')    =>  (1,0)
        _name2posn('B0')   =>  (1,0)
        _name2posn('B1')   =>  (1,0)
        _name2posn('B2')   =>  (1,1)
        _name2posn('Z')    =>  (25,0)
        _name2posn('AA')   =>  (26,0)
        _name2posn('AZ')   =>  (51,0)
        _name2posn('BA')   =>  (52,0)
        _name2posn('ZZ')   =>  (701,0)
        _name2posn('AAA')  =>  (702,0)

        """
        #0-based arithmetic
        c, r = 0, 0
        while len(n) > 0:
            v = ord(n[0])
            if v < ORD_A:
                r = int(n)
                break
            c = 26*c + v-ORD_A+1
            n = n[1:]
        if c > 0: c -= 1
        if r > 0: r -= 1
        return (c, r)

    def _posn2name(self, p=(0,0)):
        """Convert spreadsheet cell positions as a pair (column, row) and
        return a cell name as a string: 'A1'

        Example usage and return values:
     
        _posn2name((0,0))    =>  'A1'
        _posn2name((0,1))    =>  'A2'
        _posn2name((1,0))    =>  'B1'
        _posn2name((1,1))    =>  'B2'

        _posn2name((25,0))   =>  'Z1'
        _posn2name((26,0))   =>  'AA1'
        _posn2name((27,0))   =>  'AB1'

        _posn2name((51,0))   =>  'AZ1'
        _posn2name((52,0))   =>  'BA1'
        _posn2name((53,0))   =>  'BB1'

        _posn2name((701,0))  =>  'ZZ1'
        _posn2name((702,0))  =>  'AAA1'
        _posn2name((703,0))  =>  'AAB1'
        """
        try:
            col,row = p
        except:
            raise TypeError("cell positions must an integer pair")
        col += 1
        name = ""
        while col > 0:
            col, remainder = divmod(col-1, 26)
            name = chr(ORD_A + remainder) + name
        return name + str(row+1)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

###########################################################################