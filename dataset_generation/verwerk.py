
# Find filepaths to files containing a string, such as: "# "
# grep -r -l --include \*.py "# "
# grep -r -l --include \*.py '"""'

import subprocess
import sys
import getDocStrings
import getComments
import os.path as op
from const import DELIMITER, MAX_BUCKET


directories = ["edx-platform-master", "django-master", "pandas-master",
               "pylearn2-master", "salt-develop", "scikit-learn-master"]
originalPath = "original/"
processedPath = "processed/raw/"
trainingFile = "processed/trainingFormat/"
readableFile = "processed/readableFormat/"

commentCodeExt = ".commentCode"
commentExt = ".comment"
docstringCodeExt = ".dsCode"
docstringExt = ".ds"


def getFileList(directory):
    """ Recursively search directory for all source code files
        (by file extension) containing comments or docstrings

        Args:
            directory: Search root.

        Returns:
            Two lists with files with comments and files with docstrings.
    """
    try:
        # get lists of all files with comments in the directory
        comments = subprocess.check_output(["grep -r -l --include \*.py '# ' " + directory], shell=True)
        files_w_comments = comments.splitlines()
        print "Found %d files with comments" % len(files_w_comments)

        # get a list of all files with doc strings
        doc_strings = subprocess.check_output(["grep -r -l --include \*.py '\"\"\"' " + directory], shell=True)
        files_w_doc_strings = doc_strings.splitlines()
        print "Found %d files with doc strings" % len(files_w_doc_strings)
    except:
        print "Unexpected error, most likely no doc strings or comments found. Does the directory exist? \n The error:", sys.exc_info()[0]
        sys.exit(0)

    return (files_w_comments, files_w_doc_strings)


def getCommentPairs(files_w_comments, directory):
    """ Extract code-comment pairs from all files

        Args:
            files_w_comments: List with all files for processing.
            directory: Repository root dir.

        Returns:
    """

    codeFile = op.join(processedPath, directory, commentCodeExt)  # output file with code fragments
    commentFile = op.join(processedPath, directory, commentExt)  # output file with comments

    # loop through all files with block comments
    print "\nBlock comments:"
    normalComments = 0
    inlineComments = 0
    rejectedComments = 0
    for i, file in enumerate(files_w_comments):
        if i % 100 == 0:
            print("Processed {} files of {}".format(i, len(files_w_comments)))
        with open(file) as fp:
            (x, y, z) = getComments.generate_pairs(fp, codeFile, commentFile, MAX_BUCKET)
            normalComments += x
            inlineComments += y
            rejectedComments += z

    print "Total comments found: {}".format(normalComments + inlineComments + rejectedComments)
    print "Normal comments: {}".format(normalComments)
    print "Inline comments: {}".format(inlineComments)
    print "Rejected comments: {}".format(rejectedComments)


def getDocStringPairs(files_w_doc_strings, directory):
    """ Extract code-docsting pairs from all files

        Args:
            files_w_doc_strings: List with all files for processing.
            directory: Repository root dir.

        Returns:
    """
    codeFile = op.join(processedPath, directory, docstringCodeExt)  # output file with code fragments
    commentFile = op.join(processedPath, directory, docstringExt)  # output file with comments

    # loop through all files with docstrings
    print "\nDocstrings:"
    normalDocStrings = 0
    rejectedDocStrings = 0
    for i, file in enumerate(files_w_doc_strings):
        if i % 100 == 0:
            print("Processed {} files of {}".format(i, len(files_w_doc_strings)))
        with open(file) as fp:
            (x, y) = getDocStrings.generate_pairs(fp, codeFile, commentFile, MAX_BUCKET)
            normalDocStrings += x
            rejectedDocStrings += y

    print "Total docstrings found: {}".format(normalDocStrings + rejectedDocStrings)
    print "Normal docstrings: {}".format(normalDocStrings)
    print "Rejected docstrings: {}".format(rejectedDocStrings)


def createCCPair():
    """ Loop through the directory list and extract all comment-code
        (and docstring-code) pairs
    """
    for directory in directories:
        print "\n"
        print "-" * 50
        print "Directory: {}".format(directory)
        print "-" * 50

        # get file list
        (files_w_comments, files_w_doc_strings) = getFileList(op.join(originalPath, directory))

        # extract code-comment pairs
        getCommentPairs(files_w_comments, directory)
        getDocStringPairs(files_w_doc_strings, directory)


def createReadableFormat(file, codeF, commentF, counter):
    """ Convert the raw newline seperated data into a readable format.

        Args:
            file: Path to output file to save readable format.
            codeF: File (filename) with code fragments.
            commentF: File (filename) with corresponding comments.

        Returns:
    """

    with open(file, "a") as file:
        for directory in directories:
            codeFile = op.join(processedPath, directory, codeF)
            commentFile = op.join(processedPath, directory, commentF)

            # read the lines and do some string / list conversion stuff
            codeLines = open(codeFile, "r").readlines()
            codeLines = "".join(codeLines)
            codeLines = codeLines.split(DELIMITER)
            commentLines = open(commentFile, "r").readlines()
            commentLines = "".join(commentLines)
            commentLines = commentLines.split(DELIMITER)

            # loop through the lines
            for i in xrange(len(codeLines)):
                if "Parameters ----------" in commentLines[i]:
                    commentLines[i] = commentLines[i].split("Parameters ----------")[0].strip()

                if codeLines[i].strip() != '' and commentLines[i].strip() != '':
                    file.write("Pair : " + str(counter) + "\n")
                    file.write("Comment:" + commentLines[i].strip() + "\n")
                    file.write("Code:\n" + codeLines[i].rstrip() + "\n\n")
                    counter += 1

    return counter


def createTrainingFile(eFile, cFile, codeFileExtension, commentFileExtension, directory):
    """ Convert the raw newline seperated data into training files

        Args:
            eFile: Path to .en file.
            cFile: Path to .code file.
            codeFileExtension: Extension of file with code fragments.
            commentFileExtension: Extension of file with comment.
            directory: Root repository directory.

        Returns:
    """
    with open(eFile, "a") as enFile, open(cFile, "a") as codeFile:
        # get the processed files in raw format
        codeFileName = op.join(processedPath, directory, codeFileExtension)
        commentFileName = op.join(processedPath, directory, commentFileExtension)

        # read the lines and remove annoying spaces / enters and stuff
        codeLines = open(codeFileName, "r").readlines()
        codeLines = "".join(codeLines)
        codeLines = " ".join(codeLines.split())
        codeLines = "".join(codeLines)
        codeLines = codeLines.split(DELIMITER)
        commentLines = open(commentFileName, "r").readlines()
        commentLines = "".join(commentLines)
        commentLines = commentLines.split(DELIMITER)

        # loop through the lines
        for i in xrange(len(codeLines)):
            if "Parameters ----------" in commentLines[i]:
                commentLines[i] = commentLines[i].split("Parameters ----------")[0].strip()
            if codeLines[i].strip() != '' and commentLines[i].strip() != '':
                codeFile.write(codeLines[i].strip().replace("\n", "") + "\n")
                enFile.write(commentLines[i].strip().replace("\n", "") + "\n")


def createSeperateTrainingFiles():
    """ Concatenate all files .comment/.ds and .commentCode/.dsCode from
        each repository into single .en and .code files
    """
    for directory in directories:
        enFile = op.join(trainingFile, directory, ".en")
        codeFile = op.join(trainingFile, directory, ".code")

        # convert the docstring-code pairs and comment-code pairs into two large files
        createTrainingFile(enFile, codeFile, commentCodeExt, commentExt, directory)
        createTrainingFile(enFile, codeFile, docstringCodeExt, docstringExt, directory)


def concatenateTrainingFiles():
    """ Concatenate files .en and .code from each repository
        into single large file
    """

    enFileAll = op.join(trainingFile, "all.en")
    codeFileAll = op.join(trainingFile, "all.code")

    # Conctatenate all seperate trainingsfile into a single file
    with open(enFileAll, 'w') as enFileAll, open(codeFileAll, 'w') as codeFileAll:
        for directory in directories:
            # get seperate training files of this directory
            enFile = op.join(trainingFile, directory, ".en")
            codeFile = op.join(trainingFile, directory, ".code")

            # write the comments to the comment file
            with open(enFile) as enFile:
                for line in enFile:
                    enFileAll.write(line)

            # write the code to the code file
            with open(codeFile) as codeFile:
                for line in codeFile:
                    codeFileAll.write(line)


if __name__ == '__main__':
    print "Creating Code-Comment pairs.."
    createCCPair()
    print "-" * 50

    print "Converting into readable format.."
    # empty file
    file = op.join(readableFile, "readable.txt")
    counter = createReadableFormat(file, commentCodeExt, commentExt, 0)
    createReadableFormat(file, docstringCodeExt, docstringExt, counter)

    print "Converting into seperate training files.."
    createSeperateTrainingFiles()

    print "Converting into single training file.."
    concatenateTrainingFiles()
