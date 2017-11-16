"""Utilities for processing of DB with data: tokenizing, vocabularies."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from collections import defaultdict
import codecs
import os
import os.path as op
import re
import logging
import argparse
import sys
from database import CodeCommentDB

_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)

# Special vocabulary symbols - we always put them at the start.
_UNK = "<unk>"
_SOS = "<s>"
_EOS = "</s>"
_START_VOCAB = [_UNK, _SOS, _EOS]

UNK_ID = 0
SOS_ID = 1
EOS_ID = 2

# Regular expressions used to tokenize.
_WORD_SPLIT = re.compile("([`.,!?\"':;)(])")
_DIGIT_RE = re.compile(r"\d")


# def python_tokenizer(sentence):
    # """ Call python tokenizer """

    # sentence = sentence.strip()
    # buf = StringIO.StringIO(sentence)
    # token_list = []
    # for token in tokenize.generate_tokens(buf.readline):
        # token_list.append(token[1])

  #  print (get_structure(token_list))

    # return get_structure(token_list)


# def get_structure(token_list):
    # new_token_list = []

    # for token in token_list:
        # new_token_list.append(token)
        # new_token_list.append(structurer.getType(token))

    # for token in new_token_list
        # new_token_list.append(structurer.getType(token))

    # print (new_token_list)
    # sys.exit(0)

    # return new_token_list


def basic_tokenizer(sentence):
    """Very basic tokenizer: split the sentence into a list of tokens."""
    words = []
    for space_separated_fragment in sentence.strip().split():
        words.extend(re.split(_WORD_SPLIT, space_separated_fragment))
    return [w for w in words if w]


class DataSource():

    def __init__(self, dbpath, output_dir, validation_ratio=0.1):
        if not op.exists(dbpath):
            _logger.error("DB doesn't exists at path {}".format(dbpath))
            raise
        self.db = CodeCommentDB(dbpath)
        self.validation_ratio = validation_ratio if validation_ratio else 0
        self.output_dir = output_dir
        self.codes = []
        self.comments = []
        self.codes_train = []
        self.codes_val = []
        self.comments_train = []
        self.comments_val = []

    def _get_data_db(self, inline=False):
        params = {'inline': inline}
        res = self.db.get_codecomment_pairs(params)
        if not res:
            return
        for r in res:
            code = r[0].replace('\n', ' ').replace('\t', ' ').replace('  ', '').strip()
            comment = r[1].replace('\n', ' ').replace('\t', ' ').replace('  ', '').strip()
            if code and comment:
                self.codes.append(code)
                self.comments.append(comment)

    def _split_data(self):
        if not self.validation_ratio:
            self.codes_train = self.codes
            self.comments_train = self.comments
            return

        split_point = int(len(self.codes) * self.validation_ratio)
        self.codes_train = self.codes[split_point:]
        self.codes_val = self.codes[:split_point]
        self.comments_train = self.comments[split_point:]
        self.comments_val = self.comments[:split_point]

    def save_vocabulary(self, vocab, vocabulary_path):
        if op.exists(vocabulary_path):
            _logger.info('Vocabulary file {} already exists'.format(vocabulary_path))
            return
        with codecs.open(vocabulary_path, 'w', encoding='utf-8') as vocab_file:
            vocab_file.write("\n".join(vocab))
        _logger.info("Vocabulary file {} successfully created".format(vocabulary_path))

    def tokenize_data(self, data, tokenizer=None, normalize_digits=True):
        return [" ".join(tokenizer(sentence)) if tokenizer else " ".join(basic_tokenizer(sentence)) for sentence in data]

    def create_vocabulary(self,
                          data,
                          max_vocabulary_size,
                          tokenizer=None,
                          normalize_digits=True):
        """Create vocabulary file (if it does not exist yet) from data file.

        Data file is assumed to contain one sentence per line. Each sentence is
        tokenized and digits are normalized (if normalize_digits is set).
        Vocabulary contains the most-frequent tokens up to max_vocabulary_size.
        We write it to vocabulary_path in a one-token-per-line format, so that later
        token in the first line gets id=0, second line gets id=1, and so on.

        Args:
          data: list of elements to create vocabulary
          vocabulary_path: path where the vocabulary will be created.
          max_vocabulary_size: limit on the size of the created vocabulary.
          tokenizer: a function to use to tokenize each data sentence;
            if None, basic_tokenizer will be used.
          normalize_digits: Boolean; if true, all digits are replaced by 0s.
        """

        _logger.info("Creating vocabulary")
        vocab = defaultdict(lambda: 0)
        _logger.info("Total sentences count = {}".format(len(data)))
        for i, line in enumerate(data):
            if i % 10000 == 0:
                _logger.info("  processing line %d" % i)
            tokens = tokenizer(line) if tokenizer else basic_tokenizer(line)
            for w in tokens:
                word = re.sub(_DIGIT_RE, "0", w) if normalize_digits else w
                vocab[word] += 1
        vocab_list = _START_VOCAB + sorted(vocab, key=vocab.get, reverse=True)
        if len(vocab_list) > max_vocabulary_size:
            vocab_list = vocab_list[:max_vocabulary_size]
        _logger.info("Vocabulary forming finished")
        return vocab_list, vocab

    def initialize_vocabulary(self, vocabulary_path):
        """Initialize vocabulary from file.

        We assume the vocabulary is stored one-item-per-line, so a file:
          dog
          cat
        will result in a vocabulary {"dog": 0, "cat": 1}, and this function will
        also return the reversed-vocabulary ["dog", "cat"].

        Args:
          vocabulary_path: path to the file containing the vocabulary.

        Returns:
          a pair: the vocabulary (a dictionary mapping string to integers), and
          the reversed vocabulary (a list, which reverses the vocabulary mapping).

        Raises:
          ValueError: if the provided vocabulary_path does not exist.
        """
        if not op.exists(vocabulary_path):
            _logger.error("Vocabulary file {} doesn't exists!".format(vocabulary_path))
            raise ValueError("Vocabulary file %s not found.", vocabulary_path)
        with open(vocabulary_path) as f:
            rev_vocab = [line.strip() for line in f.readlines()]
        vocab = dict([(x, y) for (y, x) in enumerate(rev_vocab)])
        return vocab, rev_vocab

    def sentence_to_token_ids(self,
                              sentence,
                              vocabulary,
                              tokenizer=None,
                              normalize_digits=True):
        """Convert a string to list of integers representing token-ids.

        For example, a sentence "I have a dog" may become tokenized into
        ["I", "have", "a", "dog"] and with vocabulary {"I": 1, "have": 2,
        "a": 4, "dog": 7"} this function will return [1, 2, 4, 7].

        Args:
          sentence: the sentence in bytes format to convert to token-ids.
          vocabulary: a dictionary mapping tokens to integers.
          tokenizer: a function to use to tokenize each sentence;
            if None, basic_tokenizer will be used.
          normalize_digits: Boolean; if true, all digits are replaced by 0s.

        Returns:
          a list of integers, the token-ids for the sentence.
        """
        words = tokenizer(sentence) if tokenizer else basic_tokenizer(sentence)
        if not normalize_digits:
            return [vocabulary.get(w, UNK_ID) for w in words]
        # Normalize digits by 0 before looking words up in the vocabulary.
        return [vocabulary.get(re.sub(_DIGIT_RE, "0", w), UNK_ID) for w in words]

    def data_to_token_ids(self,
                          data,
                          target_path,
                          vocabulary_path,
                          tokenizer=None,
                          normalize_digits=True):
        """Tokenize data file and turn into token-ids using given vocabulary file.

        This function loads data line-by-line from data_path, calls the above
        sentence_to_token_ids, and saves the result to target_path. See comment
        for sentence_to_token_ids on the details of token-ids format.

        Args:
          data_path: path to the data file in one-sentence-per-line format.
          target_path: path where the file with token-ids will be created.
          vocabulary_path: path to the vocabulary file.
          tokenizer: a function to use to tokenize each sentence;
            if None, basic_tokenizer will be used.
          normalize_digits: Boolean; if true, all digits are replaced by 0s.
        """
        if op.exists(target_path):
            _logger.info("File with tokens {} already exists".format(target_path))
            return

        _logger.info("Tokenizing data")
        vocab, _ = self.initialize_vocabulary(vocabulary_path)
        with codecs.open(target_path, 'w', encoding='utf-8') as ofile:
            for i, line in enumerate(data):
                if i % 1000 == 0:
                    _logger.info("  tokenizing line %d" % i)
                token_ids = self.sentence_to_token_ids(line, vocab, tokenizer,
                                                       normalize_digits)
                ofile.write(" ".join([str(tok) for tok in token_ids]) + "\n")

    def save_data(self, data, target_path):
        if op.exists(target_path):
            _logger.info("File with data {} already exists".format(target_path))
            return

        with codecs.open(target_path, 'w', encoding='utf-8') as ofile:
            ofile.write('\n'.join(data))

    def prepare_data(self,
                     code_vocabulary_size,
                     en_vocabulary_size,
                     tokenizer=None):
        """Get WMT data into data_dir, create vocabularies and tokenize data.

        Args:
            data_dir: directory in which the data sets will be stored.
            code_vocabulary_size: max size of the code vocabulary to create and use.
            en_vocabulary_size: max size of the English vocabulary to create and use.
            tokenizer: a function to use to tokenize each data sentence;
              if None, basic_tokenizer will be used.

        Returns:
        A tuple of 6 elements:
          (1) path to the token-ids for Code training data-set,
          (2) path to the token-ids for English training data-set,
          (3) path to the token-ids for Code development (eval) data-set,
          (4) path to the token-ids for English development (eval) data-set,
          (5) path to the Code vocabulary file,
          (6) path to the English vocabulary file.
        """

        # Create vocabularies of the appropriate sizes.
        if not op.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self._get_data_db()
        self._split_data()

        # Save text files with training and validation data
        en_train_path = self.output_dir + "/train{}.en".format(en_vocabulary_size)
        code_train_path = self.output_dir + "/train{}.code".format(code_vocabulary_size)
        #self.save_data(self.comments_train, en_train_path)
        #self.save_data(self.codes_train, code_train_path)

        self.tokenized_comments_train = self.tokenize_data(self.comments_train)
        self.tokenized_codes_train = self.tokenize_data(self.codes_train)

        self.save_data(self.tokenized_comments_train, en_train_path)
        self.save_data(self.tokenized_codes_train, code_train_path)

        en_val_path = self.output_dir + "/val{}.en".format(en_vocabulary_size)
        code_val_path = self.output_dir + "/val{}.code".format(code_vocabulary_size)
        #self.save_data(self.comments_val, en_val_path)
        #self.save_data(self.codes_val, code_val_path)

        self.tokenized_comments_val = self.tokenize_data(self.comments_val)
        self.tokenized_codes_val = self.tokenize_data(self.codes_val)

        self.save_data(self.tokenized_comments_val, en_val_path)
        self.save_data(self.tokenized_codes_val, code_val_path)

        # Create and save vocabularies
        self.comments_vocab_path = op.join(self.output_dir, "vocab%d.en" % en_vocabulary_size)
        self.code_vocab_path = op.join(self.output_dir, "vocab%d.code" % code_vocabulary_size)

        self.comments_vocab_list, self.comments_vocab = self.create_vocabulary(self.comments, en_vocabulary_size, tokenizer)
        self.save_vocabulary(self.comments_vocab_list, self.comments_vocab_path)
        self.code_vocab_list, self.code_vocab = self.create_vocabulary(self.codes, code_vocabulary_size, tokenizer)
        self.save_vocabulary(self.code_vocab_list, self.code_vocab_path)

        # Create token ids for the training data.
        en_train_ids_path = self.output_dir + ("/train.ids%d.en" % en_vocabulary_size)
        code_train_ids_path = self.output_dir + ("/train.ids%d.code" % code_vocabulary_size)
        self.data_to_token_ids(self.comments_train, en_train_ids_path, self.comments_vocab_path, tokenizer)
        self.data_to_token_ids(self.codes_train, code_train_ids_path, self.code_vocab_path, tokenizer)

        # Create token ids for the validation data.
        en_val_ids_path = self.output_dir + ("/val.ids%d.en" % en_vocabulary_size)
        code_val_ids_path = self.output_dir + ("/val.ids%d.code" % code_vocabulary_size)
        self.data_to_token_ids(self.comments_val, en_val_ids_path, self.comments_vocab_path, tokenizer)
        self.data_to_token_ids(self.codes_val, code_val_ids_path, self.code_vocab_path, tokenizer)

        return (code_train_ids_path, en_train_ids_path,
                code_val_ids_path, en_val_ids_path,
                self.code_vocab_path, self.comments_vocab_path)


def main(dbpath, outputpath, vocab_size):
    datasrc = DataSource(dbpath, outputpath)
    datasrc.prepare_data(vocab_size, vocab_size)


def parse_args():
    parser = argparse.ArgumentParser('dataset')

    parser.add_argument('-d', '--db_path', type=str, default=None, help='base path to sqlite DB')
    parser.add_argument('-o', '--output_path', type=str, default=None, help='base path to output folder')
    parser.add_argument('-v', '--vocab_size', type=int, default=None, help='size of vocabulary both for input and output sequences')

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()

    if not args.db_path or not args.output_path or not args.vocab_size:
        _logger.error("USAGE: python datasource.py -d <path to sqlite DB> -o <path to output folder> -v 5000")
        sys.exit(0)

    main(args.db_path, args.output_path, args.vocab_size)
