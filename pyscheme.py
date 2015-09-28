# encoding: utf-8


def tokenize(text):
    """
        pyScheme 只有括号，空格，数字，变量名
        故此，先把括号使用空格分离，然后直接 split
        就可以得到括号、数字和变量名
    """
    return text.replace('(', ' ( ').replace(')', ' ) ').split()


def wrap_str(left, text, right):
    return left + text + right


def prettify(lexes):
    """
        display lexes in a readable format
    """
    return wrap_str('[', ", ".join(map(lambda x: wrap_str("'", x, "'"), lexes)), ']')


class SExpression(object):
    children = []

    def __init__(self, value, children, parent):
        self.value = value
        self.children = children
        self.parent = parent

    # 递归
    def tostr(self):
        # 看到，连右括号也会打印出来，说明右括号不会作为 value
        if self.value == '(':
            return wrap_str('(', " ".join([c.tostr() for c in self.children]), ')')
        else:
            return self.value

    # 静态方法
    @staticmethod
    def parse(code):
        """
            把一段代码解析为一个 SExpression 树结构
        """
        root = SExpression("", [], None)
        cur = root
        for lex in tokenize(code):
            # 遇到左括号，创建新节点为下一层子节点，然后当前节点指向新节点
            if lex == '(':
                node = SExpression('(', [], cur)
                cur.children.append(node)
                cur = node
            # 遇到右括号，回到上一层父节点，注意，并不生成新节点
            elif lex == ')':
                cur = cur.parent
            # 其他的，创建 cur 的子节点，但是当前节点保持不变，仍在当前括号一层
            else:
                cur.children.append(SExpression(lex, [], cur))
        # 返回 root 的第一个子节点，也就是第一层的括号
        return root.children[0]


class SScope(object):
    # 每个作用域就是含有一个父作用域的一套标志字典
    def __init__(self, parent, vt):
        self.parent = parent
        self.variable_table = vt

    # 从当前作用域开始查找，没找到则到父作用域查找
    # 显然，当前域优先
    def find(self, name):
        cur = self
        while cur:
            if name in cur.variable_table:
                return cur.variable_table[name]
            cur = self.parent
        raise Exception("Name: %s is not defined" % name)

    def define(self, name, value):
        self.variable_table[name] = value
        return value


""" 以下为类型系统 """


class SObject(object):
    def tostr(self):
        return str(self)


class SInt(int, SObject):
    """
        这里使用 __new__ 而不是 __init__
        用来实现 implicit convertion, like below:
        i = SNumber(5)
        i = 3
        i + 5
    """
    def __new__(cls, value=0):
        assert isinstance(value, int)
        i = int.__new__(cls, value)
        return i

"""
class SBool(bool, SObject):
    def __new__(cls, value):
        assert isinstance(value, bool)
        i = bool.__new__(cls, value)
        return i
"""


class SList(list, SObject):
    def __new__(cls, value=[]):
        assert isinstance(value, list)
        i = list.__new__(cls, value)
        return i


class SFunc(SObject):
    def __init__(self, body, parameters, scope):
        self.body = body
        self.parameters = parameters
        self.scope = scope




if __name__ == '__main__':
    print prettify(tokenize("a"))
    print prettify(tokenize("(def a 3)"))
    print prettify(tokenize("(begin (def a 3) (* a a))"))

    sexp = SExpression.parse("(def a 3)")
    print sexp.tostr()
    sexp = SExpression.parse("(begin (def a 3) (* a a))")
    print sexp.tostr()

    i = SInt()
    print i.tostr()
    print i + 5   # 此处不能调用 tostr()，仅仅能 implicitly 把 i convert 为 int 而已

    l = SList([1, 2, 3])
    l.append(4)
    print l.tostr()
