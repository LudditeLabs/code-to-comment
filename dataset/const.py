#COMMENT_LIST = ["# ", "#!"]
#COMMENT_EXCEPTIONS = ["todo", "to do"]

COMMENT_LIST = ["#"]
STR_LITERALS = ["\"\"\"", "\'\'\'"]
COMMENT_EXCEPTIONS = ["todo", "to do", "#!", "pylint", "-*-"]

CLEAN_CHAR = ["#"]

# no need to get code-commet pairs larger than the max bucket
MAX_BUCKET = [40, 40]

# default buckets with dummy first bucket (for data visualization subroutines)
BUCKETS = ((0, 0), (10, 10), (20, 20), (30, 30), (40, 40))