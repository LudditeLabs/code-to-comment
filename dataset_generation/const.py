DELIMITER = "!@#$%!@#$%!@#$%!@#$%!@#$%"

#COMMENT_LIST = ["# ", "#!"]
#COMMENT_EXCEPTIONS = ["todo", "to do"]

COMMENT_LIST = ["# "]
STR_LITERALS = ["\"\"\"", "\'\'\'"]
COMMENT_EXCEPTIONS = ["todo", "to do"]
INLINE_COMMENT_EXCEPTIONS = ["pylint"] + COMMENT_EXCEPTIONS

CLEAN_CHAR = ["#"]

# no need to get code-commet pairs larger than the max bucket
MAX_BUCKET = [40, 50]
