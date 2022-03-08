"""
Utility class to standardize response

Author: Alberto Moio <email Alberto>, Nunzio Mauro <mnunzio90@gmail.com>
Date:   2017-08-21
"""
import json


class Response:
    """Representation of http response in a standard form already used by handlers"""

    __attrs__ = [
        'content', 'status_code', 'headers', 'url'
    ]

    def __init__(self):
        self.status_code = None
        self.headers = None
        self.url = None
        self.content = None

    @property
    def text(self):
        """Textual representation of response content"""

        return self.content.decode('utf-8')

    def json(self):
        """JSON representation of response content"""

        return json.loads(self.text)
