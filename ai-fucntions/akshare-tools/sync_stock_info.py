#!/usr/bin/env python3
import sys
from typing import List

def main(argv: List[str]):
    import argparse
    parser = argparse.ArgumentParser(description="Sync A-stock comment daily metrics")
    parser.add_argument("--codes", type=str, default="", help="Comma separated stock codes, e.g. 000001,000002")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for upsert")
    args = parser.parse_args(argv)

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else []
    from sync_index import upsert_a_stock_comment_daily
    upsert_a_stock_comment_daily(codes=codes, batch_size=args.batch_size)

if __name__ == "__main__":
    main(sys.argv[1:])