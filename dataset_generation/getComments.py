# -*- coding: utf-8 -*-
""" Open a file, find all hashtag comments in the file and get the corresponding code"""

from os.path import basename, splitext
import sys
import util
from const import DELIMITER, COMMENT_LIST, COMMENT_EXCEPTIONS


def generate_pairs(source, codeFile, commentFile, maxBucket, module='<string>'):
    """ Loop through the source code and get comments and
        their correspondig code.

        Args:
            source: Opened file (file object) with source code.
            codeFile: Output file (file object) with code fragments.
            commentFile: Output file (file object) with corresponding comments.
            maxBucket: .
            module: .

        Returns:
            Tuple (normalCommentsCount, inlineCommentsCount, rejectedCommentsCount)
    """

    filename = getattr(source, 'name', module)
    module = splitext(basename(filename))[0]
    source = source.read().splitlines()

    normalComments = 0
    inlineComments = 0
    rejectedComments = 0

    i = -1
    count = 0

    # check each line for comments
    while i < len(source):
        line = source[i]

        # check if the line starts with an comment, if so
        # get the comment and code, and skip to the correct line after
        # the comment
        if line.strip()[:2] in COMMENT_LIST:
            (i, success) = filterComment(source, i, codeFile, commentFile, maxBucket)

            if count != 0 and i == count:
                sys.exit(0)

            count = i

            # only increment the count if there was no error
            if success:
                normalComments += 1
            else:
                rejectedComments += 1
            continue

        # check if we have an inline comment
        # if "# " in line.strip():
        #     parts = line.split("# ")

        #     if len(parts) != 2:
        #         pass
        #         # print ">Something is not right, skipping comment"
        #     else:
        #         code = parts[0].strip()
        #         comment = parts[1].strip().replace("#")

        #         if comment != "" and code != "":
        #             inlineComments += 1

        #             with open(commentFile, "a") as commentF:
        #                 commentF.write(comment + "\n!@#$%!@#$%!@#$%!@#$%!@#$%")

        #             with open(codeFile, "a") as codeF:
        #                 codeF.write(code.strip() + "\n!@#$%!@#$%!@#$%!@#$%!@#$%")
        #                 # codeF.write(" ".join([x.strip() for x in code]) + "\n")

        #             # print ">Comment:" , comment
        #             # print ">Code: \n" , code

        # increment by one
        i += 1

    return (normalComments, inlineComments, rejectedComments)


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

    comment = ""
    indentation = -1
    currIndent = -1
    code = []
    globalI = len(source) + 10

    # loop through all the lines in the source, get the comment
    # and the corresponding code
    with open(commentFile, "a") as commentF, open(codeFile, "a") as codeF:
        for i in xrange(startLine, len(source)):
            globalI = i
            line = source[i]

            # comments need to be directly above code
            if line.strip() == "" and comment == "":
                return (i, False)

            # Continue if we have an divider row
            if line.replace("#", "").strip() == "" and line.strip() != "":
                continue

            # check if it is an comment, and if so add it to the comment
            if line.strip()[:2] in COMMENT_LIST:
                comment += line.strip().replace("#", "") + " "
                continue

            # lines with docstrings are skipped
            if '"""' in line or "'''" in line:
                return (i, False)

            # if we get here, it means we are not in the comment anymore
            # First get the indentation level of the current line of code
            currIndent = len(line) - len(line.lstrip())

            # If it is the first line of code, set our indentation level
            if indentation == -1:
                indentation = currIndent

            # if we hit an empty line and have no code yet, return with an error
            if line.strip() == "" and code == []:
                return (i, False)

            # if we hit an empty line or go to an parent piece in the code
            # return the gathered code
            if line.strip() == "" or indentation > currIndent or (any(c in line for c in COMMENT_LIST)):
                code = util.cleanCode(code)

                # no need to save code-comment pairs larger than maxBucket size
                if util.tokenize("".join(code)) < maxBucket[0] and util.tokenize(comment) < maxBucket[1] \
                and not (any(exc in comment.lower() for exc in COMMENT_EXCEPTIONS)):
                    # write to file
                    for j in xrange(len(code)):
                        codeF.write(code[j] + "\n")
                    codeF.write(DELIMITER)
                    commentF.write(util.cleanComment(comment) + "\n" + DELIMITER)

                    return (i, True)
                else:
                    return (i, False)

            # add the line to our code if all is well (without any inline comments if any)
            if line.strip() != "":
                code.append(line)

        code = util.cleanCode(code)

        # if we are here check if we have a comment / code not empty and smaller than maxBucket size
        if comment.strip() != "" and code != [] and \
        util.tokenize("".join(code)) < maxBucket[0] and util.tokenize(comment) < maxBucket[1] \
        and not (any(exc in comment.lower() for exc in COMMENT_EXCEPTIONS)):
            # write to file
            for j in xrange(len(code)):
                codeF.write(code[j] + "\n")
            codeF.write(DELIMITER)
            commentF.write(util.cleanComment(comment) + "\n" + DELIMITER)

            return (globalI+1, True)
        else:
            return (globalI+1, False)


if __name__ == '__main__':
    pass
