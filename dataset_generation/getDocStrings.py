from os.path import basename, splitext
import sys
import util
from const import DELIMITER, COMMENT_LIST, COMMENT_EXCEPTIONS

dsList = ["'''", '"""']


def generate_pairs(source, codeFile, commentFile, maxBucket, module='<string>'):
    """ Loop through the source code and get docstring and
        their correspondig code.

        Args:
            source: Opened file (file object) with source code.
            codeFile: Output file (file object) with code fragments.
            commentFile: Output file (file object) with corresponding comments.
            maxBucket: .
            module: .

        Returns:
            Tuple (normalDocstringsCount, rejectedDocstringsCount)
    """

    filename = getattr(source, 'name', module)
    module = splitext(basename(filename))[0]
    source = source.read().splitlines()

    normalDocStrings = 0
    rejectedDocStrings = 0
    i = 0
    count = 0

    # check each line for comments
    while i < len(source):
        line = source[i]

        if '"""' in line:
            (i, success) = filterDocString(source, i, codeFile, commentFile, maxBucket)

            # Throw an 'error' in case we are looping
            if i == count:
                print "Error, looping at line ", i, " in getDocStrings in file:", filename
                sys.exit(0)

            count = i

            # only increment the count if there was no error
            if success:
                normalDocStrings += 1
            else:
                rejectedDocStrings += 1
            continue

        # increment by one
        i += 1

    return (normalDocStrings, rejectedDocStrings)


def filterDocString(source, startLine, codeFile, commentFile, maxBucket):
    """ Find the docstring at line i in the list source. When found,
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
    inComment = True
    comment = ""
    indentation = -1
    currIndent = -1
    code = []

    # add the first line to the comment and check for single line docstrings
    count = (source[startLine].count('"""'))
    if count == 2:
        comment = source[startLine].strip().replace('"""', "") + " "
        inComment = False
    else:
        comment = source[startLine].strip().split('"""')[1]
    startLine += 1

    # print ">>Inside comment loop, added firstline:" , comment

    # loop through all the lines in the source, get the comment
    # and the corresponding code
    with open(commentFile, "a") as commentF, open(codeFile, "a") as codeF:
        for i in xrange(startLine, len(source)):
            # print "i in comment loop is:" , i
            globalI = i
            # print "I is:", i, " startline is:" , startLine
            line = source[i]

            # skip empty lines
            if line.strip() == "":
                continue

            # If it is the first line of code, set our indentation level
            if indentation == -1:
                indentation = currIndent

            # check if there is an block comment inside the docstring annotated code
            if any(comment in line for comment in COMMENT_LIST):
                # print ">>Found block comment, return error"
                return (i, False)

            currIndent = len(line) - len(line.lstrip())
            # print ">>Current indent" , currIndent , " current line:" , line

            if "'''" in line:
                return (i, False)

            # check if we have encountered an doc string
            if '"""' in line:

                # print ">>Found triple quote"

                # first if we are at another indentation level, we found an deeper
                # docstring, thus exit
                if currIndent != indentation or not inComment:
                    # print ">>>It is a new comment, return error"
                    return(i, False)

                # otherwise end the comment
                else:
                    # print ">>>Closed comment"
                    comment += source[i].strip().replace('"""', "").replace("#", "") + " "
                    inComment = False
                    continue

            # add text to the comment if it hasn't closed yet
            if inComment:
                comment += line.strip().replace("#", "") + " "
                continue

            # if we are still here, we have closed the comment and are collecting code

            # return true if we found the end of the annotated code
            if indentation > currIndent:
                code = util.cleanCode(code)
                # only return true if we are in a function def,
                # also no need to save code-comment pairs larger than maxBucket size
                if not isDef(source, startLine, i) or \
                   not (util.tokenize("".join(code)) < maxBucket[0] and util.tokenize(comment) < maxBucket[1]) or \
                   (any(exc in comment.lower() for exc in COMMENT_EXCEPTIONS)):

                    return (i, False)

                # write to file
                for j in xrange(len(code)):
                    codeF.write(code[j] + "\n")
                codeF.write(DELIMITER)
                commentF.write(util.cleanComment(comment) + "\n" + DELIMITER)

                return(i, True)

            # if we are still here, add the current line to the code
            code.append(line.strip())

        # print ">>Got to the end with i:" , globalI
        if comment != "" and code != []:
            code = util.cleanCode(code)

            # only return true if we are in a function def
            # also no need to save code-comment pairs larger than maxBucket size
            if not isDef(source, startLine, i) or \
               not (util.tokenize("".join(code)) < maxBucket[0] and util.tokenize(comment) < maxBucket[1]) or \
               (any(exc in comment.lower() for exc in COMMENT_EXCEPTIONS)):
                return (globalI+1, False)

            # write to file
            for j in xrange(len(code)):
                codeF.write(code[j] + "\n")
            codeF.write(DELIMITER)
            commentF.write(util.cleanComment(comment) + "\n" + DELIMITER)
            # codeF.write(" ".join([x.strip() for x in code]) + "\n")

            # print "Comment:" , comment
            # print "Code:" , code, "\n"
            return (globalI+1, True)
        else:
            return (globalI+1, False)


# check if we are in a function definition
def isDef(source, startLine, i):
    # check the previous line
    containsDef = "def" in source[startLine - 1]

    # if we are not sure, check the rest of the source
    if not containsDef:
        for i in xrange(startLine, len(source)):
            if "def" in source[i]:
                containsDef = True

    # print "Contains Def:" , containsDef

    return containsDef

if __name__ == '__main__':
    pass
