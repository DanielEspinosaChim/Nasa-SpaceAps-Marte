"""Atajo: python scripts/fetch_dem.py --region jezero --url <geotiff> | --source <archivo>."""

import sys

from marsmap.terrain.fetch import main

if __name__ == "__main__":
    sys.exit(main())
