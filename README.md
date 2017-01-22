# Introduction #

This repo provides a Python class `POSTree` which could convert a question into statement. `POSTree` takes the parse tree from [Stanford Parser](http://nlp.stanford.edu/software/lex-parser.shtml) as input and produces a statement as output based on some heuristic rules.

## Usage ##

```python
from POSTree import POSTree

tree = POSTree("(ROOT"
               "  (SQ (VBZ Is)"
               "    (NP (DT the) (NN boy))"
               "    (VP (VBG holding)"
               "      (NP (DT a) (NN toy)))"
               "    (. ?)))")
print(tree.adjust_order())
# the boy is **blank** holding a toy
```

More examples:

```
what is the boy holding ? --> the boy holding is **blank**

who is holding a toy ? --> **blank** is holding a toy

what is on the table ? --> **blank** is on the table
```

There is a [online Stanford Parser](http://nlp.stanford.edu:8080/parser/index.jsp) where you can conveniently abtain the parse tree of a sentence.
