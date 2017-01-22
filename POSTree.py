from operator import itemgetter

DEBUG = False

class POSTree(object):
    """Penn Treebank style tree."""

    class Node(object):
        def __init__(self, token):
            self.token = token
            self.first_child = None
            self.next_sibling = None

        def __repr__(self):
            return '<%s>' % (self.token,)

    def __init__(self, text):
        """Create a Penn Treebacnk style tree from plaint text.

        Using child-sibling representation.

        text: the output from stanford parser.
        """
        
        self.raw_text = text
        self.text = text.replace('\n', '')
        self.text_length = len(self.text)
        self.text_pointer = 0
        self.words = []
        self.root = self.__create_tree()
        self.question = ' '.join(self.__gather_word(self.root))
        self.VB_TAG = ('VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'MD')
        self.VB_WORD = ('do', 'does', 'can', 'could', 'would', 'should', 
                'might', 'has', 'have', "'ve", 'is', "'s", 'are', "'re", 'was', 'were')

    def __create_tree(self):
        parent = None
        token = self.__next_token()
        if token == '(':
            token = self.__next_token()
            parent = self.Node(token)
            parent.first_child = self.__create_tree()
            child = parent.first_child
            if child != None:
                while True:
                    child.next_sibling = self.__create_tree()
                    child = child.next_sibling
                    if child == None:
                        break
        elif token != ')':
            parent = self.Node(token.lower())
            self.words.append(token.lower())

        return parent

    def __next_token(self):
        end = self.text_pointer
        while end < self.text_length and self.text[end] == ' ':
            end += 1

        if end == self.text_length:
            return None

        if self.text[end] in ('(', ')'):
            token = self.text[end]
            end += 1
        else:
            start = end
            end += 1
            while end < self.text_length and self.text[end] not in ('(', ')', ' '):
                end += 1
            token = self.text[start:end]
        self.text_pointer = end
        return token

    def first_order_traverse(self):
        self.__first_order_traverse(self.root)
    def __first_order_traverse(self, tree):
        if tree != None:
            print(tree.token)
            self.__first_order_traverse(tree.first_child)
            if tree.first_child != None:
                child = tree.first_child.next_sibling
                while child != None:
                    self.__first_order_traverse(child)
                    child = child.next_sibling

    def __delete_period(self):
        child = self.root.first_child.first_child
        assert(child.token != '.')
        while child.next_sibling.token != '.':
            child = child.next_sibling
        child.next_sibling = None

    def __check_PP(self, prenode, node):
        while node != None and node.token in ('PP', ',', 'SBAR'):
            prenode = node
            node = node.next_sibling
        return prenode, node

    def adjust_order(self):
        try:
            child = self.root.first_child
            if child.token == 'FRAG' and ' '.join(self.words[:2]) == 'how many':
                words = ['there', 'are', '**blank**'] + self.words[2:-1]
                return ' '.join(words)

            self.__delete_period()
            assert(child.next_sibling == None)
            if child.token == 'SQ':
                self.__adjust_SQ_question(child)
            elif child.token == 'SBARQ':
                prefirst = child
                first = child.first_child
                second = first.next_sibling
                if first.token == 'SQ' and second == None:
                    self.__adjust_SQ_question(first)
                elif (first.token in ('WHADJP', 'WHNP', 'WHADVP', 'WHPP')
                        and second.token == 'SQ'):
                    WH = self.__delete_tree(prefirst, first)
                    self.__adjust_SBARQ_question(WH, second)
                else:
                    raise ValueError('Unknown question structure!')
            elif child.token == 'SBAR':
                if (child.first_child.token == 'WHADJP'
                        and child.first_child.next_sibling.token == 'S'
                        and ' '.join(self.words[:2]) == 'how many'):
                    SQ = child.first_child.next_sibling
                    WH = self.__delete_tree(child, child.first_child)
                    self.__adjust_SBARQ_question(WH, SQ)
                else:
                    raise ValueError('Unknown question structure!')
            else:
                raise ValueError('Unknown question structure!')
            words = self.__gather_word(self.root)
            words = filter(lambda w: w != '', words)
            statement = ' '.join(words)
        except Exception as e:
            if DEBUG:
                print(self.question)
                print(self.raw_text)
            raise e
        return statement

    def __create_answer_node(self, before_text='', after_text=''):
        node = self.Node('A')
        answer = '**blank**'
        if before_text != '':
            answer = '%s %s' % (before_text, answer)
        if after_text != '':
            answer = '%s %s' % (answer, after_text)
        node.first_child = self.Node(answer)
        return node

    def __check_VB(self, node):
        if node.token in self.VB_TAG:
            return True
        if node.first_child.token in self.VB_WORD:
            node.token = 'VB'
            return True
        return False

    def __adjust_SQ_question(self, SQ):
        VB = SQ.first_child
        assert(self.__check_VB(VB))
        auxiliary = VB.first_child.token
        if auxiliary not in ('do', 'did', 'does'):
            answer = self.__create_answer_node(before_text=auxiliary)
        else:
            answer = self.__create_answer_node()

        # move answer after first NP
        NP = VB.next_sibling
        while NP.token != 'NP':
            NP = NP.next_sibling
        self.__insert_after(answer, NP)
        self.__delete_tree(SQ, VB)
        return SQ

    def __gather_word(self, tree):
        words = []
        def recursor(t):
            if t == None:
                return
            if t.first_child == None:
                words.append(t.token)
            else:
                recursor(t.first_child)
                sibling = t.first_child.next_sibling
                while sibling != None:
                    recursor(sibling)
                    sibling = sibling.next_sibling
        recursor(tree)
        return words

    def __tree_to_text(self, tree):
        words = []
        def recursor(t):
            if t == None:
                return
            if t.first_child == None:
                words.append(' '+t.token)
            else:
                words.append('('+t.token)
                recursor(t.first_child)
                sibling = t.first_child.next_sibling
                while sibling != None:
                    recursor(sibling)
                    sibling = sibling.next_sibling
                words.append(')')
        recursor(tree)
        return ''.join(words)

    def __convert_WH_to_answer(self, WH):
        words = self.__gather_word(WH)
        WH_text = ' '.join(words)
        if WH_text == 'how old':
            WH.first_child = self.__create_answer_node(after_text='years old')
        elif WH_text == 'why':
            WH.first_child = self.__create_answer_node(before_text='because')
        elif WH.token in ('WHADJP', 'WHADVP'):
            WH.first_child = self.__create_answer_node()
        elif WH.token == 'WHNP' or WH.token == 'WHPP' and WH.first_child.next_sibling.token == 'WHNP':
            parent = WH if WH.token == 'WHNP' else WH.first_child.next_sibling
            first = WH.first_child
            while first.token == 'WHNP':
                parent = first
                first = first.first_child
            if first.token == 'WHADJP':
                first.first_child = self.__create_answer_node()
            elif self.__tree_to_text(parent).startswith('(WHNP(WDT what)(NN color)(NN'):
                after_text = ' '.join(self.__gather_word(parent)).replace('what color ', '', 1)
                parent.first_child = self.__create_answer_node(after_text=after_text)
            else:
                parent.first_child = self.__create_answer_node()
        else:
            raise ValueError('Unknown WH structure!')
        return WH

    def __check_ADVP(self, prenode, node):
        while node != None and node.token == 'ADVP':
            prenode = node
            node = node.next_sibling
        return prenode, node

    def __delete_tree(self, prenode, node):
        if node == None:
            return node
        if prenode.first_child == node:
            prenode.first_child = node.next_sibling
        else:
            prenode.next_sibling = node.next_sibling
        node.next_sibling = None
        return node

    def __delete_node(self, prenode, node):
        if node == None:
            return node
        if prenode.first_child == node:
            if node.first_child == None:
                prenode.first_child = node.next_sibling
            else:
                prenode.first_child = node.first_child
                lc = node.first_child
                while lc.next_sibling != None:
                    lc = lc.next_sibling
                lc.next_sibling = node.next_sibling
                node.first_child = None
        else:
            if node.first_child == None:
                prenode.next_sibling = node.next_sibling
            else:
                prenode.next_sibling = node.first_child
                lc = node.first_child
                while lc.next_sibling != None:
                    lc = lc.next_sibling
                lc.next_sibling = node.next_sibling
                node.first_child = None
        node.next_sibling = None
        return node

    def __insert_after(self, srcnode, dstnode):
        assert(srcnode != None and dstnode != None)
        srcnode.next_sibling = dstnode.next_sibling
        dstnode.next_sibling = srcnode
        return srcnode

    def __insert_as_first_child(self, srcnode, dstnode):
        assert(srcnode != None and dstnode != None)
        srcnode.next_sibling = dstnode.first_child
        dstnode.first_child = srcnode
        return srcnode

    def __insert_as_last_child(self, srcnode, dstnode):
        assert(srcnode != None and dstnode != None)
        lc = dstnode.first_child
        if lc == None:
            self.__insert_as_first_child(srcnode, dstnode)
        else:
            while lc.next_sibling != None:
                lc = lc.next_sibling
            self.__insert_after(srcnode, lc)
        return srcnode

    def __adjust_SQ_in_SBARQ(self, SQ, WH):
        prefirst, first = self.__check_ADVP(SQ, SQ.first_child)
        
        # SQ = VP
        if first.token == 'VP':
            return SQ

        # SQ = NP + VP
        if (first.token == 'NP' and first.next_sibling != None 
                and first.next_sibling.token == 'VP' and first.next_sibling.next_sibling == None):
            return SQ

        if not self.__check_VB(first):
            raise ValueError('First child of SQ in SBARQ is not VB*/MD')

        # process 's 're 've
        if first.first_child.token == "'s":
            first.first_child.token = 'is'
        elif first.first_child.token == "'re":
            first.first_child.token = 'are'
        elif first.first_child.token == "'ve":
            first.first_child.token = 'have'

        presecond, second = self.__check_ADVP(first, first.next_sibling)

        # SQ = VB* + [ADVP]
        if second == None:
            return SQ

        # process RB(not) and auxiliary do/does/did
        if second.token == 'RB' and second.first_child.token in ("n't", "not"):
            if first.first_child.token == 'ca':
                first.first_child.token = 'can not'
            else:
                first.first_child.token += ' not'
            self.__delete_tree(presecond, second)
            presecond, second = self.__check_ADVP(first, first.next_sibling)
        else:
            if first.first_child.token in ('do', 'does', 'did'):
                first.first_child.token = ''

        # SQ = VB*+PP/ADJP/VP
        if second.next_sibling == None and second.token in ('PP', 'ADJP', 'VP'):
            return SQ
        
        # SQ = VB* + NP
        #      |     |
        #     first second
        if second.token == 'NP' and second.next_sibling == None:
            fc = second.first_child

            # second = NP + ?
            #          |    |
            #          fc   sc
            if (fc.token == 'NP' and fc.next_sibling != None
                    and fc.next_sibling.next_sibling == None):
                sc = fc.next_sibling
                if ((sc.token == 'PP' and WH.token == 'WHADVP')
                        or (sc.token == 'PP' and sc.first_child.token == 'IN' 
                            and sc.first_child.next_sibling == None)
                        or (sc.token == 'NP' and ' '.join(self.__gather_word(fc)) == 'there')
                        or (sc.token == 'ADJP')
                        or (sc.token == 'SBAR' and sc.first_child.token == 'WHADVP')):
                    self.__delete_node(presecond, second)
                    VB = self.__delete_tree(prefirst, first)
                    self.__insert_after(VB, fc)
                    return SQ
            VB = self.__delete_tree(prefirst, first)
            self.__insert_after(VB, second)
            return SQ

        # SQ = VB* + NP + ? 
        #      |     |    |
        #    first second third
        if second.token == 'NP' and second.next_sibling != None:
            prethird, third = self.__check_ADVP(second, second.next_sibling)
            # SQ = VB* + NP + ADVP
            if third == None:
                VB = self.__delete_tree(prefirst, first)
                self.__insert_after(VB, second)
                return SQ

            if third.next_sibling == None:
                if ((third.token in ('ADJP', 'PP', 'NP', 'VP'))
                        or (third.token == 'S' 
                            and self.__tree_to_text(third).startswith('(S(VP(TO to)(VP(VB'))):
                    VB = self.__delete_tree(prefirst, first)
                    self.__insert_after(VB, second)
                    return SQ

        raise ValueError('Unknown SQ structure in SBARQ!')

    def __prefix_by_to_WH(self, WH):
        BY = self.Node('BY')
        BY.first_child = self.Node('by')
        self.__insert_as_first_child(BY, WH)
        return WH

    def __insert_WH_into_SQ(self, WH, SQ):
        if self.words[0] == 'why':
            self.__insert_as_last_child(WH, SQ)
            return SQ

        prefirst, first = self.__check_ADVP(SQ, SQ.first_child)

        if first.next_sibling == None:
            # SQ = VP
            if first.token == 'VP':
                self.__insert_as_first_child(WH, SQ)
                return SQ

            # SQ = NP
            if first.token == 'NP':
                self.__insert_after(WH, first)
                return SQ

            # SQ = VB*
            if self.__check_VB(first):
                self.__insert_as_first_child(WH, SQ)
                return SQ

            raise ValueError('Unknown SQ structure!')

        presecond, second = self.__check_ADVP(first, first.next_sibling)

        # SQ = VB* + ADVP
        if self.__check_VB(first) and second == None:
            self.__insert_as_first_child(WH, SQ)
            return SQ

        # SQ = VB* + VP/PP/ADJP
        #      |     |
        #    first  second
        if (self.__check_VB(first) and second.next_sibling == None 
                and second.token in ('VP', 'PP', 'ADJP')):
            self.__insert_as_first_child(WH, SQ)
            return SQ

        prethird, third = self.__check_ADVP(second, second.next_sibling)

        # SQ = NP + VB* + [ADVP]
        #      |    |      
        #    first second 
        if (first.token == 'NP' and self.__check_VB(second) and 
                (second.next_sibling == None or third == None)):
            self.__insert_after(WH, second)
            return SQ

        # SQ = NP + VP
        #      |    |
        #    first second
        if (first.token == 'NP' and second.token == 'VP' 
                and second.next_sibling == None):
            if WH.token in ('WHNP', 'WHADJP'):
                self.__insert_as_first_child(WH, SQ)
                return SQ
            if WH.token  == 'WHPP':
                self.__insert_after(WH, second)
                return SQ

        if third == None:
            raise ValueError('Unknown SQ structure!')

        # SQ = NP + VB* + ?
        #      |    |     |
        #   first second third
        if first.token == 'NP' and self.__check_VB(second) and third.next_sibling == None:

            # SQ = NP + VB* + VP
            if third.token == 'VP':
                VB = second
                VP = third
                while (self.__check_VB(VP.first_child) and VP.first_child.next_sibling != None
                        and VP.first_child.next_sibling.token == 'VP'):
                    VB = VP.first_child
                    VP = VB.next_sibling
                # VP = VBN + [...]
                #      |
                #      fc
                _, fc = self.__check_ADVP(VP, VP.first_child)
                if ((VB.first_child.token != '' 
                        and VB.first_child.token.split()[0] in ('is', 'are', 'was', 'were'))
                        and fc.token == 'VBN'):
                    if WH.token == 'WHADVP' and self.words[0] == 'how':
                        WH = self.__prefix_by_to_WH(WH)
                        self.__insert_after(WH, VP)
                        return SQ
                    if WH.token == 'WHADVP' and self.words[0] in ('why', 'where'):
                        self.__insert_after(WH, VP)
                        return SQ
                # VP = VB*
                #      |
                #      fc
                if self.__check_VB(fc) and fc.next_sibling == None:
                    self.__insert_after(WH, VP)
                    return SQ
                # VP = VB* + ?
                #      |     |
                #      fc    sc
                if (self.__check_VB(fc) and fc.next_sibling != None
                        and fc.next_sibling.next_sibling == None):
                    sc = fc.next_sibling
                    # VP = VB* + PRT
                    if sc.token == 'PRT':
                        self.__insert_after(WH, VP)
                        return SQ
                    # VP = VB* + PP
                    if sc.token == 'PP':
                        ffc = sc.first_child
                        if ffc.token == 'IN' and ffc.next_sibling == None:
                            self.__insert_after(WH, VP)
                            return SQ
                        if (ffc.token == 'IN' and ffc.next_sibling != None
                                and ffc.next_sibling.next_sibling == None):
                            ssc = ffc.next_sibling
                            if ssc.token in ('NP', 'ADJP'):
                                self.__insert_after(WH, fc)
                                return SQ
                    # VP = VB* + SBAR
                    if sc.token == 'SBAR':
                        if fc.first_child.token in ('know', 'think'):
                            if WH.token == 'WHADVP' and self.words[0] == 'how':
                                WH = self.__prefix_by_to_WH(WH)
                                self.__insert_after(WH, VP)
                                return SQ
                            self.__insert_after(WH, VP)
                            return SQ
                        self.__insert_after(WH, fc)
                        return SQ
                    # VP = VB* + S
                    if sc.token == 'S' and self.__tree_to_text(sc).startswith('(S(VP(TO to)(VP(VB'):
                        VB_S = sc.first_child.first_child.next_sibling.first_child
                        if VB_S.next_sibling == None:
                            self.__insert_after(WH, VP)
                            return SQ
                        if (VB_S.next_sibling.token == 'SBAR' 
                                and VB_S.next_sibling.first_child.token == 'WHADVP'):
                            self.__insert_after(WH, VB_S)
                            return SQ
                        self.__insert_after(WH, fc)
                        return SQ
                    # VP = VB* + ADVP
                    if sc.token == 'ADVP':
                        self.__insert_after(WH, fc)
                        return SQ

                if WH.token == 'WHADVP' and self.words[0] == 'how':
                    WH = self.__prefix_by_to_WH(WH)
                    self.__insert_after(WH, VP)
                    return SQ
                self.__insert_after(WH, VP)
                return SQ

            # SQ = NP + VB* + NP
            if third.token == 'NP':
                self.__insert_after(WH, third)
                return SQ
            # SQ = NP + VB* + S
            if third.token == 'S' and self.__tree_to_text(third).startswith('(S(VP(TO to)(VP(VB'):
                VB_S = third.first_child.first_child.next_sibling.first_child
                if VB_S.next_sibling == None and WH.token == 'WHNP':
                    self.__insert_after(WH, VB_S)
                    return SQ
                self.__insert_after(WH, second)
                return SQ
            # SQ = NP + VB* + SBAR
            if third.token == 'SBAR' and third.first_child.token == 'WHADVP':
                self.__insert_after(WH, second)
                return SQ
            # SQ = NP + VB* + PP
            if third.token == 'PP':
                self.__insert_after(WH, third)
                return SQ
            # SQ = NP + VB* + ADJP
            if third.token == 'ADJP':
                if WH.token == 'WHADVP' and self.words[0] == 'how':
                    WH = self.__prefix_by_to_WH(WH)
                    self.__insert_after(WH, third)
                    return SQ
                self.__insert_after(WH, third)
                return SQ

        raise ValueError('Unknown SQ structure!')

    def __adjust_SBARQ_question(self, WH, SQ):
        """Adjust word order of SBARQ question.

        Pipeline:
          1. __convert_WH_to_answer();
          2. __adjust_SQ_in_SBARQ();
          3. __insert_WH_into_SQ().
        """
        #WH = self.root.first_child.first_child
        #SQ = WH.next_sibling

        WH = self.__convert_WH_to_answer(WH)
        SQ = self.__adjust_SQ_in_SBARQ(SQ, WH)
        SQ = self.__insert_WH_into_SQ(WH, SQ)

        self.root.first_child.first_child = SQ
