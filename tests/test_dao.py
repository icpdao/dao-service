import os
import pytest

TESTS_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

class TestJWT():
    def test_dao(self):
        assert 1 == 1
