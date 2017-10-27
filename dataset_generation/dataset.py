# Find filepaths to files containing a string, such as: "# "
# grep -r -l --include \*.py "# "
# grep -r -l --include \*.py '"""'

import argparse
import logging
import subprocess
import os
import os.path as op
import re
import sys


_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)

DELIMITER = "!@#$%!@#$%!@#$%!@#$%!@#$%"
COMMENT_LIST = ["# "]
COMMENT_EXCEPTIONS = ["todo", "to do"]
INLINE_COMMENT_EXCEPTIONS = ["pylint"]

CLEAN_CHAR = ["#"]


# tokenize a sentence by splitting at punctuation marks
def _tokenize(sentence):
    _WORD_SPLIT = re.compile("([.,!?\"':;)(])")
    words = []

    for space_separated_fragment in sentence.strip().split():
        words.extend(re.split(_WORD_SPLIT, space_separated_fragment))

    return len([w for w in words if w])


def _check_create(path):
    """ Check directory path, create if needed

    Args:
        path: Path to be checked.
    """
    if not op.exists(path):
        os.makedirs(path)
        _logger.info("Created directory {}".format(path))


def _get_file_list(directory):
    """ Recursively search directory for all source code files
        (by file extension) containing comments or docstrings

        Args:
            directory: Search root.

        Returns:
            Tuple of two lists with files with comments and files with docstrings.
    """
    file_comments = subprocess.check_output(["grep -r -l --include \*.py '# ' " + directory], shell=True)
    file_comments = file_comments.splitlines()
    _logger.info("Found {} files with comments".format(len(file_comments)))
    doc_strings = subprocess.check_output(["grep -r -l --include \*.py '\"\"\"' " + directory], shell=True)
    file_dstrings = doc_strings.splitlines()
    doc_strings = subprocess.check_output(["grep -r -l --include \*.py '\'\'\' " + directory], shell=True)
    file_dstrings += doc_strings.splitlines()
    _logger.info("Found {} files with doc strings".format(len(file_dstrings)))
    return file_comments, file_dstrings


def _clean_str(inpstr):
    res = inpstr
    for c in CLEAN_CHAR:
        res = res.replace(c, "")
    return res


class CodeCommentDataset():

    _BUCKETS = [(10, 10), (20, 20), (30, 30), (40, 40)]

    def __init__(self, buckets=None, blockcomment=True, inlinecomment=True):
        if buckets:
            self._BUCKETS = buckets
        self.blockcomment = blockcomment
        self.inlinecomment = inlinecomment

    def _get_block_comment(self, source, linenum):
        """ Check for a multiline comment and get the corresponding code.

            Args:
                source: List of strings of source code file.
                linenum: Number of processing string.

            Returns:
                Tuple (number of line from which continue search, flag, (code, comment))
        """
        maxbucket = self._BUCKETS[-1]

        indentation = None
        curindentation = -1

        curline = int(linenum)
        comment = ""
        # at first, we should get entire comment (which could be multiline)
        while curline < len(source):
            line = source[curline]
            curindentation = len(line) - len(line.lstrip())

            if not indentation:
                indentation = curindentation

            if line.strip()[:2] not in COMMENT_LIST or indentation > curindentation:
                break
            comment += line.strip()[2:] + " "
            curline += 1

        # check if comment is empty
        if not comment.strip():
            return (curline, False, (None, None))

        code = []
        while curline < len(source):
            line = source[curline]
            curindentation = len(line) - len(line.lstrip())
            # if we have some elements in code and get an empty line, finish
            if not line.strip() and code:
                break
            # if indentation changed or line have an inline comment (???), finish
            #if indentation > curindentation or (any(c in line for c in COMMENT_LIST)):
            if indentation > curindentation:
                break
            code.append(line)
            curline += 1

        if not code:
            return (curline, False, (None, None))

        if _tokenize(" ".join(code)) >= maxbucket[0] or _tokenize(comment) >= maxbucket[1] \
            or (any(exc in comment.lower() for exc in COMMENT_EXCEPTIONS)):
            return (curline, False, (None, None))

        return (curline, True, (code, comment))

    def _get_pairs(self, filepath):
        """ Extract all code-comment pairs from selected file

            Args:
                filepath: Path to file.

            Returns:
                Tuple (success block comments count, inline comments count, declined block comments count, founded_pairs)
        """
        _logger.info("Started processing of file {}".format(filepath))
        with open(filepath) as f:
            sources = f.readlines()

        comments_cnt = {False: 0, True: 0}  # False - rejected comments, True - accepted comments
        comments_inline = 0
        founded_pairs = []

        curline = 0

        while curline < len(sources):
            line = sources[curline]
            # check if line is begining of block comment
            if self.blockcomment and line.strip()[:2] in COMMENT_LIST:
                (curline, success, pair) = self._get_block_comment(sources, curline)
                if success:
                    founded_pairs.append(pair)
                comments_cnt[success] += 1
                continue

            if self.inlinecomment and "# " in line.strip() and not any(e in line for e in INLINE_COMMENT_EXCEPTIONS):
                parts = line.split("# ", 2)
                if len(parts) != 2:
                    break
                code = _clean_str(parts[0].strip())
                comment = _clean_str(parts[1].strip())
                if code and comment:
                    founded_pairs.append((code, comment))
                    comments_inline += 1
            curline += 1

        return (comments_cnt[True], comments_inline, comments_cnt[False], founded_pairs)

    def _get_comments(self, fileslist, outputfile):
        """ Extract code-comment pairs from all files

            Args:
                fileslist: List with all files for processing.

            Returns:
        """
        founded_pairs = []
        normalcomments = 0
        inlinecomments = 0
        rejectedcomments = 0
        for i, file in enumerate(fileslist):
            if i % 100 == 0:
                _logger.info("Processed {} files of {}".format(i, len(fileslist)))
            (x, y, z, pairs) = self._get_pairs(file)
            founded_pairs.extend(pairs)
            normalcomments += x
            inlinecomments += y
            rejectedcomments += z

        _logger.info("Total comments found: {}".format(normalcomments + inlinecomments + rejectedcomments))
        _logger.info("Normal comments: {}".format(normalcomments))
        _logger.info("Inline comments: {}".format(inlinecomments))
        _logger.info("Rejected comments: {}".format(rejectedcomments))

        output_code = outputfile + ".code"
        output_comment = outputfile + ".comment"

        with open(output_code, 'a') as ocode, open(output_comment, 'a') as ocomment:
            for code, comment in founded_pairs:
                ocode.write(code + "\n" + DELIMITER)
                ocomment.write(comment + "\n" + DELIMITER)

    def _get_dstrings(self, fileslist):
        pass

    def prepare_data_dir(self, srcpath, dstpath):
        """ Extract code/comment pairs from all files in directory recursively

            Args:
                srcpath: Path to directory
                dstpath: Path to output files

            Returns
        """
        self.file_comments, self.file_dstrings = _get_file_list(srcpath)
        self._get_comments(self.file_comments, dstpath)

    def parse_directories(self, dirs, outputpath):
        """ Extract code/comment pairs from all directories in list

            Args:
                dirs: List with directories to parse
                outputpath: Path to output files

            Returns
        """
        for d in dirs:
            _logger.info("Parsing directory {}".format(d))
            self.prepare_data_dir(d, outputpath)


def main(datapath, outputpath):
    dataset = CodeCommentDataset(blockcomment=False)
    dataset.prepare_data_dir(datapath, outputpath)


def parse_args():
    parser = argparse.ArgumentParser('dataset')

    parser.add_argument('-d', '--data_path', type=str, default=None, help='base path to data folder')
    parser.add_argument('-o', '--output_path', type=str, default=None, help='base path to data folder')

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()

    if not args.data_path or not args.output_path:
        _logger.error("USAGE: python dataset.py -d <path to directory with source code> -o <path to output file>")
        sys.exit(0)

    main(args.data_path, args.output_path)
