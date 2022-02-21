"""
Class enabling printing/saving logs
"""

class Logs():
    def __init__(self, debug=False):
        self.debug = debug
    
    def print(self, message, debug=False):
        """
        Prints logs
        """
        # if message type is set to debug (debug=True) but overall debugging is disabled
        if debug and not self.debug:
            return
        
        print(message)
        