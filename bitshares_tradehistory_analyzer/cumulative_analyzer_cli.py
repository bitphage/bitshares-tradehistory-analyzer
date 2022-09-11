#!/usr/bin/env python

import click
import pandas as pd

from bitshares_tradehistory_analyzer.cumulative_trade_analyzer import CumulativeAnalyzer


@click.command()
@click.argument("csv_file", nargs=-1)
@click.option("--start", help="Start analysis data, in pandas format e.g. '2021-06-01 12:00'")
@click.option("--end", help="End analysis data, in pandas format e.g. '2021-06-01 12:00'")
def main(csv_file, start, end):
    """Script to analyze transfers and trades to produce a summary.

    Useful for those who wants to get summary overview of what happened to their asset, what sold and bought,
    deposited/withdrawn.

    To use this script, first you must export transfer and trade history from an exchange, by using
     `download_history.py` script.
    """
    if len(csv_file) < 1:
        raise click.BadParameter(message="At least one csv file expected")
    analyzer = CumulativeAnalyzer()
    for single_file in csv_file:
        analyzer.append_csv(single_file)

    analyzer.run_analysis(
        start=pd.Timestamp(start, tz="UTC") if start else None, end=pd.Timestamp(end, tz="UTC") if end else None
    )

    click.echo("Asset transfer stats:")
    click.echo(analyzer.transfer_results.to_string())
    click.echo("Trading stats:")
    click.echo(analyzer.trade_results.to_string())


if __name__ == '__main__':
    main()
