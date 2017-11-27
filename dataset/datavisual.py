""" This module contains class for data visualization
"""

import sqlite3
import argparse
import logging
import matplotlib.pyplot as plt
from collections import defaultdict
from database import CodeCommentDB
from datasource import DataSource
from const import BUCKETS

_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)


class DataVisualizer():

    def __init__(self, dbpath):
        self.db = CodeCommentDB(dbpath)

    def seq_distribution(self, iscode, max_val=100, bins=20):
        codecomments = self.db.get_codecomment_pairs()
        ind = 0 if iscode else 1
        data = [len(p[ind]) for p in codecomments]
        plt.hist(data, bins=bins, range=(0, max_val))
        return

    def words_distribution(self, iscode, max_vocabulary_size=None, max_val=1000, bins=20):
        codecomments = self.db.get_codecomment_pairs()
        ind = 0 if iscode else 1
        data = [p[ind] for p in codecomments]
        _, vocab = DataSource.create_vocabulary(data, max_vocabulary_size)
        freq = list(vocab.values())
        plt.hist(freq, bins=bins, range=(0, max_val if max_val else max(freq)))
        return


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