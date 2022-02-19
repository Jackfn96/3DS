"""
Class enabling printing/saving logs
"""

class Logs():
    def __init__(self, debug=False):
        self.debug = debug
    
    def print(self, message):
        """
        Prints log only if debugging is enabled
        """
        if self.debug:
            print(message)