"""Utilities for processing of DB with data: tokenizing, vocabularies."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from collections import defaultdict
import os.path as op
import re
import logging
import sqlite3

_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)

# Special vocabulary symbols - we always put them at the start.
_PAD = b"_PAD"
_GO = b"_GO"
_EOS = b"_EOS"
_UNK = b"_UNK"
_START_VOCAB = [_PAD, _GO, _EOS, _UNK]

PAD_ID = 0
GO_ID = 1
EOS_ID = 2
UNK_ID = 3

# Regular expressions used to tokenize.
_WORD_SPLIT = re.compile(b"([`.,!?\"':;)(])")
_DIGIT_RE = re.compile(br"\d")


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

    def __init__(self, dbpath, output_dir, validation_ratio=None):
        if not op.exists(dbpath):
            _logger.error("DB doesn't exists at path {}".format(dbpath))
        self.conn = sqlite3.connect(dbpath)
        self.validation_ration = validation_ratio if validation_ratio else 0
        self.output_dir = output_dir

    def create_vocabulary(self,
                          vocabulary_path,
                          data_path,
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
          vocabulary_path: path where the vocabulary will be created.
          data_path: data file that will be used to create vocabulary.
          max_vocabulary_size: limit on the size of the created vocabulary.
          tokenizer: a function to use to tokenize each data sentence;
            if None, basic_tokenizer will be used.
          normalize_digits: Boolean; if true, all digits are replaced by 0s.
        """
        if op.exists(vocabulary_path):
            _logger.info('Vocabulary file {} already exists'.format(vocabulary_path))
            return
        _logger.info("Creating vocabulary %s from data %s" % (vocabulary_path, data_path))
        vocab = defaultdict(0)
        with open(data_path) as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if i % 100000 == 0:
                _logger.info("  processing line %d" % i)
            tokens = tokenizer(line) if tokenizer else basic_tokenizer(line)
            for w in tokens:
                word = re.sub(_DIGIT_RE, b"0", w) if normalize_digits else w
                vocab[word] += 1
        vocab_list = _START_VOCAB + sorted(vocab, key=vocab.get, reverse=True)
        if len(vocab_list) > max_vocabulary_size:
            vocab_list = vocab_list[:max_vocabulary_size]
        with open(vocabulary_path, 'w') as vocab_file:
            vocab_file.write("\n".join(vocab_list))
        _logger.info("Vocabulary file {} successfully created".format(vocabulary_path))

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
        return [vocabulary.get(re.sub(_DIGIT_RE, b"0", w), UNK_ID) for w in words]

    def data_to_token_ids(self,
                          data_path,
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

        _logger.info("Tokenizing data in %s" % data_path)
        vocab, _ = self.initialize_vocabulary(vocabulary_path)
        with open(data_path) as ifile, open(target_path, 'w') as ofile:
            lines = ifile.readlines()
            for i, line in enumerate(lines):
                if i % 1000 == 0:
                    _logger.info("  tokenizing line %d" % i)
                token_ids = self.sentence_to_token_ids(line, vocab, tokenizer,
                                                       normalize_digits)
                ofile.write(" ".join([str(tok) for tok in token_ids]) + "\n")

    def prepare_data(self,
                     data_dir,
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
        en_vocab_path = op.join(self.output_dir, "vocab%d.en" % en_vocabulary_size)
        code_vocab_path = op.join(self.output_dir, "vocab%d.code" % code_vocabulary_size)
        self.create_vocabulary(en_vocab_path, train_path + ".en", en_vocabulary_size, tokenizer)
        # create_vocabulary(code_vocab_path, train_path + ".code", code_vocabulary_size, python_tokenizer)
        self.create_vocabulary(code_vocab_path, train_path + ".code", code_vocabulary_size, tokenizer)

        # Create token ids for the training data.
        en_train_ids_path = train_path + (".ids%d.en" % en_vocabulary_size)
        code_train_ids_path = train_path + (".ids%d.code" % code_vocabulary_size)
        self.data_to_token_ids(train_path + ".en", en_train_ids_path, en_vocab_path, tokenizer)
        # data_to_token_ids(train_path + ".code", code_train_ids_path, code_vocab_path, python_tokenizer)
        self.data_to_token_ids(train_path + ".code", code_train_ids_path, code_vocab_path, tokenizer)

        # Create token ids for the development data.
        en_dev_ids_path = dev_path + (".ids%d.en" % en_vocabulary_size)
        code_dev_ids_path = dev_path + (".ids%d.code" % code_vocabulary_size)
        self.data_to_token_ids(dev_path + ".en", en_dev_ids_path, en_vocab_path, tokenizer)
        # data_to_token_ids(dev_path + ".code", code_dev_ids_path, code_vocab_path, python_tokenizer)
        self.data_to_token_ids(dev_path + ".code", code_dev_ids_path, code_vocab_path, tokenizer)

        return (code_train_ids_path, en_train_ids_path,
                code_dev_ids_path, en_dev_ids_path,
                code_vocab_path, en_vocab_path)
