import os
import logging
import subprocess
import os.path as op
import sys
import argparse
from collections import defaultdict
from database import CodeCommentDB
from const import COMMENT_LIST, STR_LITERALS, COMMENT_EXCEPTIONS, INLINE_COMMENT_EXCEPTIONS, CLEAN_CHAR


_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)


def _show_progress(msg, i, totlen, step=1000):
    if i % step == 0:
        _logger.info(msg.format(i, totlen))


def _check_create(path):
    """ Check directory path, create if needed

    Args:
        path: Path to be checked.
    """
    if not op.exists(path):
        os.makedirs(path)
        _logger.info("Created directory {}".format(path))


def _clean_str(inpstr):
    res = inpstr
    for c in CLEAN_CHAR:
        res = res.replace(c, "")
    return res


class DataExtractor():

    def __init__(self, outdb='codecomment.db', blockcomments=True, inlinecomments=True):
        self.repos = []
        self.sources = defaultdict(list)
        self.pairs = defaultdict(list)
        self.blockcomments = blockcomments
        self.inlinecomments = inlinecomments
        self.db = CodeCommentDB(outdb)

    # METHODS FOR SOURCE FILE TEXT PROCESSING

    def _exclude_multiline_string_literal(self, linenum, sources):
        line = sources[linenum].strip()
        # check if line is a start of multiline string literal (and not block comment)
        literal = None
        literal_index = 1000000000
        for sl in STR_LITERALS:
            # we should check all possible quotes types
            if sl in line and line.count(sl) % 2 and line.index(sl) < literal_index:
                literal = sl
                literal_index = line.index(sl)
        if not literal:
            return linenum
        linenum += 1
        while linenum < len(sources) and sources[linenum].count(sl) % 2 != 1:
            linenum += 1
        return linenum + 1

    def _check_inline_comment(self, line):
        return "# " in line and not any(e in line.lower() for e in INLINE_COMMENT_EXCEPTIONS)

    def _get_inline_comment(self, line):
        parts = line.split("# ", 2)
        code = _clean_str(parts[0].strip())
        comment = _clean_str(parts[1].strip())
        return code, comment

    def _check_block_comment(self, line):
        return line[:2] in COMMENT_LIST

    def _get_block_comment(self, linenum, sources):
        """ Check for a multiline comment and get the corresponding code.

            Args:
                linenum: Number of processing string.
                sources: List of strings of source code file.

            Returns:
                Tuple (number of line from which continue search, flag, (code, comment))
        """
        line = sources[linenum]
        indentation = len(line) - len(line.lstrip())
        curindentation = len(line) - len(line.lstrip())

        curline = linenum
        comment = ""
        # at first, we should get entire comment (which could be multiline)
        while curline < len(sources):
            line = sources[curline]
            curindentation = len(line) - len(line.lstrip())
            line = line.strip()
            # TODO - check this conditions
            if line[:2] not in COMMENT_LIST or indentation > curindentation:
                break
            comment += line[2:] + " "
            curline += 1

        # check if comment is empty
        comment = comment.strip()
        if not comment:
            return (curline, False, (None, None))

        code = ""
        while curline < len(sources):
            line = sources[curline]
            curindentation = len(line) - len(line.lstrip())
            line = line.strip()
            # if we have some elements in code and get an empty line, finish
            if not line and code:
                break
            # if indentation changed or line have an inline comment (???), finish
            # if indentation > curindentation or (any(c in line for c in COMMENT_LIST)):
            if indentation > curindentation:
                break
            code += line + " "
            curline += 1

        code = code.strip()
        if not code:
            return (curline, False, (None, None))

        if any(exc in comment.lower() for exc in COMMENT_EXCEPTIONS):
            return (curline, False, (None, None))

        return (curline, True, (code, comment))

    def _get_comments(self, filepath):
        """ Extract all code-comment pairs from selected file

            Args:
                filepath: Path to file.

            Returns:
                Dict {
                    'accepted_block': [...],
                    'rejected_block': [...],
                    'accepted_inline': [...],
                    'rejected_inline': [...]
                }
        """
        _logger.info("Started processing of file {}".format(filepath))
        with open(filepath) as f:
            sources = f.readlines()

        comments = {
            'accepted_block': [],
            'rejected_block': [],
            'accepted_inline': [],
            'rejected_inline': []
        }

        curline = 0
        while curline < len(sources):
            # get current line and strip it from spaces/tabs
            line = sources[curline].strip()

            # 1 - check line is a begining of block comment
            if self._check_block_comment(line):
                newlinenum, res, cc_pair = self._get_block_comment(curline, sources)
                if self.blockcomments:
                    comments['accepted_block' if res else 'rejected_block'].append({
                            'pair': cc_pair,
                            'is_inline': False,
                            'linenum': curline
                    })
                curline = newlinenum
                continue

            # 2 - check line is a begining of string literal
            # probably, string literals (without variables assign)
            # could be interpreted as block comments
            newlinenum = self._exclude_multiline_string_literal(curline, sources)
            if newlinenum != curline:
                curline = newlinenum
                continue

            # 3 - check if line contains inline comment
            if self._check_inline_comment(line):
                code, comment = self._get_inline_comment(line)
                if self.inlinecomments:
                    comments['accepted_inline' if code and comment else 'rejected_block'].append({
                        'pair': (code, comment),
                        'is_inline': True,
                        'linenum': curline
                    })

            curline += 1

        return comments

    def _get_dstrings(self, filepath):
        return None

    # METHODS FOR WORK WITH WHOLE FILES AND REPOS

    def process_file(self, filepath):
        """ Extract all code-comments (in future - docstrings) pairs from selected file

            Args:
                filepath: path to file to extract code-comment pairs

            Returns:
                List of dicts with format
                    Dict {
                        'accepted_block': [...],
                        'rejected_block': [...],
                        'accepted_inline': [...],
                        'rejected_inline': [...]
                    }
        """
        _logger.info("Processing file {:s}".format(filepath))
        fcs = self._get_comments(filepath)
        #  fds = self._get_dstrings(filepath)
        return fcs

    def _get_file_list(self, path):
        """ Recursively search directory for all source code files
            (by file extension) containing comments or docstrings

            Args:
                directory: Search root.

            Returns:
                Tuple of two lists with files with comments and files with docstrings.
        """
        file_comments = subprocess.check_output(["grep -r -l --include \*.py '# ' " + path], shell=True)
        file_comments = file_comments.splitlines()
        _logger.info("Found {} files with comments".format(len(file_comments)))
        """
        doc_strings = subprocess.check_output(["grep -r -l --include \*.py '\"\"\"' " + path], shell=True)
        file_dstrings = doc_strings.splitlines()
        doc_strings = subprocess.check_output(["grep -r -l --include \*.py '\'\'\' " + path], shell=True)
        file_dstrings += doc_strings.splitlines()
        _logger.info("Found {} files with doc strings".format(len(file_dstrings)))
        return file_comments, file_dstrings
        """
        return file_comments

    def process_repo(self, repodir):
        """ Extract all code-comment pairs from one repository

            Args:
                repodir: repository root directory

            Returns:
                List of dicts with following format
                    {
                        'fpath': path to file in repo,
                        'pairs': all founded code pairs
                    }
        """
        _logger.info("Processing repository {:s}".format(repodir))
        repo = op.dirname(repodir)
        repo_files = self._get_file_list(repodir)
        repo_data = {'rpath': repodir, 'files': []}
        for i, fp in enumerate(repo_files):
            _show_progress("Processing {} file of {}", i, len(repo_files))
            fcs = self.process_file(fp)
            repo_data['files'].append({'fpath': fp, 'pairs': fcs})
        self.db.save_repo_data(repo_data)
        return repo_data

    def process_folder(self, rootdir):
        """ Process whole folder. Each subfolder of rootdir interpreted as repository

            Args:
                rootdir: processing folder

            Returns:
                List of dicts with following fomrat
                    {
                        'rpath': path to rootdir subfolder,
                        'files': list of dicts
                    }
                    'files' elements have following format
                        {
                            'fpath': path to file in repo,
                            'pairs': all founded code pairs
                        }
        """
        def _get_subfolders(rootdir):
            return [d for d in os.listdir(rootdir) if op.isdir(op.join(rootdir, d))]
        _logger.info("Data extraction started for root folder {:s}".format(rootdir))
        self.repos = _get_subfolders(rootdir)
        all_data = {'rootdir': rootdir, 'repos': []}
        for i, r in enumerate(self.repos):
            _show_progress("Processing {} folder of {}", i, len(self.repos), step=10)
            repo_data = self.process_repo(op.join(rootdir, r))
            all_data['repos'].append(repo_data)
        return all_data


def main(datapath, outputpath):
    dataset = DataExtractor(outdb=outputpath)
    dataset.process_folder(datapath)


def parse_args():
    parser = argparse.ArgumentParser('dataextractor')

    parser.add_argument('-d', '--data_path', type=str, default=None, help='base path to data folder')
    parser.add_argument('-o', '--output_path', type=str, default=None, help='base path to output sqlite db')

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()

    if not args.data_path or not args.output_path:
        _logger.error("USAGE: python dataextractor.py -d <path to directory with source code> -o <path to output file>")
        sys.exit(0)

    main(args.data_path, args.output_path)
