""" This module contains class for data visualization
"""

import sqlite3
import argparse
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
from database import CodeCommentDB
from datasource import DataSource
from const import BUCKETS

_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)


COMMENT_INDEX = 1
CODE_INDEX = 0


class DataVisualizer():

    def __init__(self, dbpath):
        self.db = CodeCommentDB(dbpath)
        self.tokenized_cc = None

    def seq_distribution(self, iscode, max_val=100, bins=20):
        codecomments = self.get_tokenized_data()
        ind = CODE_INDEX if iscode else COMMENT_INDEX
        data = [len(p[ind]) for p in codecomments]
        plt.hist(data, bins=bins, range=(0, max_val))

    def words_distribution(self, iscode, max_vocabulary_size=None, max_val=1000, bins=20):
        codecomments = self.get_tokenized_data()
        ind = CODE_INDEX if iscode else COMMENT_INDEX
        data = [p[ind] for p in codecomments]
        _, vocab = DataSource.create_vocabulary(data, max_vocabulary_size)
        freq = list(vocab.values())
        plt.hist(freq, bins=bins, range=(0, max_val if max_val else max(freq)))

    def sort_by_buckets(self, data, buckets=None):
        """ Sort code comment pairs by buckets

            Args:
                data: could be list(tuple) of ints or list of tuples (place in buckets together)
        """
        if not buckets:
            buckets = BUCKETS
        # last bucket for all outliers

        code = [p[0] for p in data]
        comments = [p[1] for p in data]

        buckets_cnt = [len(filter(lambda x: x > buckets[i-1] and x < buckets[i], data)) for i in range(1, len(buckets))]
        return buckets_cnt

    def seq_lens(self, data, iscode=True):
        ind = COMMENT_INDEX if iscode else CODE_INDEX
        d = [len(p[ind]) for p in data]
        return d

    def get_tokenized_data(self, refresh=False):
        if self.tokenized_cc and not refresh:
            return self.tokenized_cc
        codecomments = self.db.get_codecomment_pairs()
        code = [p[0] for p in codecomments]
        comments = [p[1] for p in codecomments]
        tok = DataSource.tokenize_data
        tokenized_cc = list(zip(tok(code), tok(comments)))
        self.tokenized_cc = tokenized_cc
        return tokenized_cc

    def get_comments_lens(self):
        codecomments = self.get_tokenized_data()
        return self.seq_lens(codecomments, iscode=False)

    def get_codes_lens(self):
        codecomments = self.get_tokenized_data()
        return self.seq_lens(codecomments, iscode=True)

    def form_hist(self, iscode=True, **kwargs):
        """ Form a distribution histogram among buckets
        """
        valid_hist_args = {"bins", "range"}
        hist_args = {k:v for k, v in kwargs.items() if k in valid_hist_args}
        codecomments = self.get_tokenized_data()
        distr = self.seq_lens(codecomments, iscode=iscode)
        plt.hist(distr, **hist_args)

    def form_percentile(self, **kwargs):
        codecomments = self.get_tokenized_data()
        distr = self.seq_lens(codecomments)
        sns.distplot(distr)


def main():
    c = DataVisualizer('./dataset/codebase_new.db')
    c.words_distribution(False, 5000)


if __name__ == '__main__':
    main()