import os
import logging
import subprocess
import os.path as op
from collections import defaultdict


_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)


def _get_subfolders(rootdir):
    return [d for d in os.listdir(rootdir) if op.isdir(op.join(rootdir, d))]


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


def _get_file_list(path):
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
    doc_strings = subprocess.check_output(["grep -r -l --include \*.py '\"\"\"' " + path], shell=True)
    file_dstrings = doc_strings.splitlines()
    doc_strings = subprocess.check_output(["grep -r -l --include \*.py '\'\'\' " + path], shell=True)
    file_dstrings += doc_strings.splitlines()
    _logger.info("Found {} files with doc strings".format(len(file_dstrings)))
    return file_comments, file_dstrings


class DataExtractor():

    def __init__(self):
        self.repos = []
        self.sources = defaultdict(list)
        self.pairs = defaultdict(list)

    def _check_start_block_comment(self, line):
        pass

    def _exclude_multiline_string_literal(self, linenum, sources):
        line = sources[linenum].strip()
        # check if line is a start of multiline string literal
        literal = None
        literal_index = 1000000000
        for sl in STR_LITERALS:
            if sl in line and line.index(sl) < literal_index:
        if any(sl in line and line.count(sl) % 2 for sl in STR_LITERALS):


    def _get_comments(self, filepath):
        """ Extract all code-comment pairs from selected file

            Args:
                filepath: Path to file.

            Returns:
                Tuple (success block comments count, inline comments count, declined block comments count, founded_pairs)
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
            line = sources[curline]
            # check if line is begining of str literal
            if any(line.strip().startswith(e) and line.count(e) % 2 for e in STR_LITERALS):
                literal = line.strip()[:3]
                curline += 1
                while curline < len(sources) and sources[curline].count(literal) == 0:
                    curline += 1
                curline += 1
                continue

            # check if line is begining of block comment
            if self.blockcomment and line.strip()[:2] in COMMENT_LIST:
                (curline, success, pair) = self._get_block_comment(sources, curline)
                if success:
                    founded_pairs.append({'pair': pair, 'is_inline': False, 'linenum': curline})
                comments_cnt[success] += 1
                continue

            if self.inlinecomment and "# " in line.strip() and not any(e in line.lower() for e in INLINE_COMMENT_EXCEPTIONS):
                parts = line.split("# ", 2)
                if len(parts) != 2:
                    break
                code = _clean_str(parts[0].strip())
                comment = _clean_str(parts[1].strip())
                if code and comment:
                    founded_pairs.append({'pair': (code, comment), 'is_inline': True, 'linenum': curline})
                    comments_inline += 1
            curline += 1

        return (comments_cnt[True], comments_inline, comments_cnt[False], founded_pairs)

    def _get_dstrings(self, filepath):
        pass

    def process_file(self, filepath):
        _logger.info("Processing file {:d}".format(filepath))
        fcs = self._get_comments(filepath)
        fds = self._get_dstrings(filepath)
        return fcs, fds

    def process_repo(self, repodir):
        _logger.info("Processing repository {:d}".format(repodir))
        repo = op.dirname(repodir)
        repo_files = _get_file_list(repo)
        for i, rp in enumerate(repo_files):
            _show_progress("Processing {} file of {}", i, len(repo_files))
            self.process_file(rp)

    def process_folder(self, rootdir):
        _logger.info("Data extraction started for root folder {:d}".format(rootdir))
        self.repos = _get_subfolders(rootdir)
        for i, r in enumerate(self.repos):
            _show_progress("Processing {} folder of {}", i, len(self.repos), step=10)
            self.process_repo(op.join(rootdir, r))

    def save_to_db(self, dbpath):
        pass


    def _get_comments(self, fileslist):
        """ Extract code-comment pairs from all files

            Args:
                fileslist: List with all files for processing.

            Returns:
        """
        founded_pairs = {}
        normalcomments = 0
        inlinecomments = 0
        rejectedcomments = 0
        for i, file in enumerate(fileslist):
            if i % 100 == 0:
                _logger.info("Processed {} files of {}".format(i, len(fileslist)))
            (x, y, z, pairs) = self._get_pairs(file)
            founded_pairs[file] = pairs
            normalcomments += x
            inlinecomments += y
            rejectedcomments += z

        _logger.info("Total comments found: {}".format(normalcomments + inlinecomments + rejectedcomments))
        _logger.info("Normal comments: {}".format(normalcomments))
        _logger.info("Inline comments: {}".format(inlinecomments))
        _logger.info("Rejected comments: {}".format(rejectedcomments))

        self._save_result_db(fileslist, founded_pairs)