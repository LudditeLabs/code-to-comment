###########################################################################################################
# Author: Tjalling Haije
# Project: code-to-comment
# For: Bsc AI, University of Amsterdam
# Date: May, 2016
###########################################################################################################

import os
import os.path as op
import random


base_path = "/home/konstantin/work/ludditelabs/data/"
input_code_file = op.join(base_path, "allCodeCommentOnly/all.code")
input_en_file = op.join(base_path, "allCodeCommentOnly/all.en")
output_dev_en_file = op.join(base_path, "allCodeCommentOnly/dev/10pt.random.en")
output_dev_code_file = op.join(base_path, "allCodeCommentOnly/dev/10pt.random.code")
output_train_code_file = op.join(base_path, "allCodeCommentOnly/train/90pt.random.code")
output_train_en_file = op.join(base_path, "allCodeCommentOnly/train/90pt.random.en")

all_files = [input_code_file, input_en_file, output_dev_en_file, output_dev_code_file,
             output_train_code_file, output_train_en_file]


# this function adds spaces around all punctuation in the specified file, and writes it to the output file
def gen_random_dataset():
    """ Randomly split .code and .en files into training (dev) and test files. Training file
        contains 10% of all data, test file 90%
    """
    with open(input_code_file) as f, open(input_en_file) as g:
        code_file = f.readlines()
        en_file = g.readlines()

    idxs = random.suffle(range(len(code_file)))

    code_file = code_file[idxs]
    en_file = en_file[idxs]

    delim_point = int(round(len(code_file) * 0.1))

    # open the dev files
    with open(output_dev_en_file, 'w') as dev_en_file, open(output_dev_code_file, 'w') as dev_code_file:
        dev_en_file.writelines(en_file[:delim_point])
        dev_code_file.writelines(code_file[:delim_point])

    print ("Dev files created.")

    # open the train files
    with open(output_train_en_file, 'w') as train_en_file, open(output_train_code_file, 'w') as train_code_file:
        # write 90% random lines to the train files
        train_en_file.writelines(en_file[delim_point:])
        train_code_file.writelines(code_file[delim_point:])

    print ("Train files created.")
    print ("Done.")


def main():
    for f in all_files:
        d = op.dirname(f)
        if not op.exists(d):
            os.makedirs(d)
    gen_random_dataset()
    # os.system("python punctuation_police.py")


if __name__ == "__main__":
    main()
