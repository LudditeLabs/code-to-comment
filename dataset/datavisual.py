""" This module contains class for data visualization
"""

import sqlite3
import argparse
import logging
import matplotlib.pyplot as plt
from database import CodeCommentDB
from const import BUCKETS

_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)


class DataVisualizer():

    def __init__(self, dbpath):
        self.db = CodeCommentDB(dbpath)

    def sort_by_buckets(self, data, buckets=None):
        """ Sort code comment pairs by buckets

            Args:
                data: could be list(tuple) of ints or list of tuples (place in buckets together)
        """
        if not buckets:
            buckets = BUCKETS
        # last bucket for all outliers

        code = [p[0] for p in codecomments]
        comments = [p[1] for p in codecomments]

        buckets_cnt = [len(filter(lambda x: x > buckets[i-1] and x < buckets[i], data)) for i in range(1, len(buckets))]
        return buckets_cnt

    def form_hist(self, **kwargs):
        """ Form a distribution histogram among buckets
        """
        codecomments = self.db.get_codecomment_pairs()


        return buckets_cnt


def main():
    c = DataVisualizer('codecomment.db')
    r = c.form_hist()


if __name__ == '__main__':
    main()