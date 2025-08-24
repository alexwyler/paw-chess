import sys

from .cli import main

if __name__ == "__main__":
    res_code = main()
    sys.exit(res_code)
