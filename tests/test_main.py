import os
import time
from proxyduck.proxyduck import ProxyDuck


test_dir = os.path.abspath(os.path.join(os.path.abspath("tests")))


def test_without_options():
    ProxyDuck(
        os.path.join(test_dir, "proxy.txt"), os.path.join(test_dir, "output.txt")
    ).start()
    time.sleep(2)
    assert os.path.exists(os.path.join(test_dir, "output.txt")) == True
