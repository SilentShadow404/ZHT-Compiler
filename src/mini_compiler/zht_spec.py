"""Language specification for ZHT (a C-like teaching language)."""

LANGUAGE_NAME = "ZHT"

TYPE_WHOLE = "whole"
TYPE_REAL = "real"
TYPE_FLAG = "flag"
TYPE_EMPTY = "empty"

TYPE_KEYWORDS = {TYPE_WHOLE, TYPE_REAL, TYPE_FLAG, TYPE_EMPTY}

KEYWORD_WHEN = "when"
KEYWORD_OTHERWISE = "otherwise"
KEYWORD_LOOP = "loop"
KEYWORD_RANGE = "range"
KEYWORD_GIVE = "give"
KEYWORD_SCAN = "scan"
KEYWORD_SHOW = "show"

BOOL_TRUE = "yes"
BOOL_FALSE = "no"

KEYWORDS = {
    KEYWORD_WHEN,
    KEYWORD_OTHERWISE,
    KEYWORD_LOOP,
    KEYWORD_RANGE,
    KEYWORD_GIVE,
    KEYWORD_SCAN,
    KEYWORD_SHOW,
    BOOL_TRUE,
    BOOL_FALSE,
}
