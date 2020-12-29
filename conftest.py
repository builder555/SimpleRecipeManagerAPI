from unittest.mock import call
class Stub():
    def __init__(self, mocked):
        self.__mock = mocked
    def called_with(self, *a):
        try:
            self.__mock.assert_called_with(*a)
            return True
        except Exception as e:
            print(e)
            return False
    def has_call_with(self, *a):
        for c in self.__mock.mock_calls:
            if c == call(*a):
                return True
        return False
