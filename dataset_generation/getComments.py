# -*- coding: utf-8 -*-
""" Open a file, find all hashtag comments in the file and get the corresponding code"""

from os.path import basename, splitext
import sys
import util
from const import DELIMITER, COMMENT_LIST, COMMENT_EXCEPTIONS


def generate_pairs(source, codeFile, commentFile, maxBucket):
    """ Loop through the source code and get comments and
        their correspondig code.

        Args:
            source: Opened file (file object) with source code.
            codeFile: Output file (file object) with code fragments.
            commentFile: Output file (file object) with corresponding comments.
            maxBucket: .

        Returns:
            Tuple (normalCommentsCount, inlineCommentsCount, rejectedCommentsCount)
    """

    source = source.read().splitlines()

    commentsCnt = {False: 0, True: 0}
    inlineComments = 0
    i = 0

    # check each line for comments
    while i < len(source):
        line = source[i]
        # check if the line starts with an comment, if so
        # get the comment and code, and skip to the correct line after
        # the comment
        if line.strip()[:2] in COMMENT_LIST:
            (i, success) = filterComment(source, i, codeFile, commentFile, maxBucket)
            commentsCnt[success] += 1
            continue
        # check if we have an inline comment
        elif "# " in line.strip():
            parts = line.split("# ")
            if len(parts) != 2:
                break
            code = parts[0].strip()
            comment = parts[1].strip()
            if code and comment:
                inlineComments += 1
                with open(commentFile, "a") as commentF, open(codeFile, "a") as codeF:
                    codeF.write(code + "\n" + DELIMITER)
                    commentF.write(comment + "\n" + DELIMITER)
        # move to next line
        i += 1

    return (commentsCnt[True], inlineComments, commentsCnt[False])


def filterComment(source, startLine, codeFile, commentFile, maxBucket):
    """ Find the comment at line i in the list source. When found,
        check for a multiline comment and get the corresponding code.

        Args:
            source: List of strings of source code file.
            startLine: Number of processing string.
            codeFile: Output file (file object) with code fragments.
            commentFile: Output file (file object) with corresponding comments.
            maxBucket: .

        Returns:
            Tuple (number of line from which continue search, flag)
    """

    indentation = None
    curIndent = -1
    globalI = len(source) + 10

    curLine = int(startLine)
    comment = ""
    # at first, we should get entire comment (which could be multiline)
    while curLine < len(source):
        line = source[curLine]
        curIndent = len(line) - len(line.lstrip())
        if not indentation:
            indentation = curIndent
        if line.strip()[:2] not in COMMENT_LIST or indentation > curIndent:
            break
        comment += line.strip()[2:] + " "
        curLine += 1

    # check if comment is empty
    if not comment.strip():
        return (curLine, False)

    code = []
    while curLine < len(source):
        line = source[curLine]
        curIndent = len(line) - len(line.lstrip())
        # if we have some elements in code and get an empty line, finish
        if not line.strip() and code:
            break
        # if indentation changed or line have an inline comment, finish
        if indentation > curIndent or (any(c in line for c in COMMENT_LIST)):
            break
        code.append(line)
        curLine += 1

    if not code:
        return (curLine, False)

    if util.tokenize(" ".join(code)) >= maxBucket[0] or util.tokenize(comment) >= maxBucket[1] \
        or (any(exc in comment.lower() for exc in COMMENT_EXCEPTIONS)):
        return (curLine, False)

    with open(commentFile, "a") as commentF, open(codeFile, "a") as codeF:
        # write to file
        codeF.write("\n".join(code))
        codeF.write(DELIMITER)
        commentF.write(comment + "\n" + DELIMITER)
    return (curLine, True)

if __name__ == '__main__':
    pass
