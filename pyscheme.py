# encoding: utf-8
import operator


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
                # 最后，每个字符都会成为 SExpression
                cur.children.append(SExpression(lex, [], cur))
        # 返回 root 的第一个子节点，也就是第一层的括号
        return root.children[0]

    def evaluate(self, scope):
        if len(self.children) == 0:
            # 处理整数
            if self.value.isdigit():
                return int(self.value)
            # 处理无子节点的变量，从 scope 中查找
            else:
                return scope.find(self.value)
        else:
            first = self.children[0]
            if top_scope.buildin_funcs.has_key(first.value):
                return top_scope.buildin_funcs[first.value](self.children[1:], scope)
        raise Exception("This is not invalid syntax.")


class SScope(object):
    # 每个作用域就是含有一个父作用域的一套标志字典和一套函数字典
    def __init__(self, parent, vt):
        self.parent = parent
        self.variable_table = vt
        self.buildin_funcs = {}

    # 从当前作用域开始查找，没找到则到父作用域查找
    # 显然，当前域优先
    def find(self, name):
        cur = self
        while cur:
            if name in cur.variable_table:
                return cur.variable_table[name]
            cur = self.parent
        raise Exception("Name: %s is not defined" % name)

    def find_in_top(self, name):
        if name in self.variable_table:
            return self.variable_table[name]
        else:
            return None

    def define(self, name, value):
        self.variable_table[name] = value
        return value

    def buildin(self, name, func):
        self.buildin_funcs[name] = func
        # 为了链式操作
        return self


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
        # 这里会出错
        i = bool.__new__(cls, value)
        return i
"""


class SList(list, SObject):
    def __new__(cls, value=[]):
        assert isinstance(value, list)
        i = list.__new__(cls, value)
        return i


class SFunc(SObject):
    """
        SFunc == SExpression + parameters + SScope
    """
    def __init__(self, body, parameters, scope):
        self.body = body
        self.parameters = parameters
        self.scope = scope

    def filled_parameters(self):
        return filter(lambda p: self.scope.find_in_top(p), self.parameters)

    # 给了部分参数，但是没给全部参数，这样就叫做 partial
    def is_partial(self):
        given_cnt = len(self.filled_parameters())
        return given_cnt >= 1 and given_cnt < len(self.parameters)

    def evaluate(self):
        given_cnt = len(self.filled_parameters())
        # 如果没给参数或 partial，那么仍然是个 SFunc
        if given_cnt < len(self.parameters):
            return self
        # 参数给全了，就可以估值了
        else:
            return self.body.evaluate(self.scope)

    def tostr(self):
        pstr = ' '.join([p + ':' + self.scope.find_in_top(p) if self.scope.find_in_top(p) else p for p in self.parameters])
        return 'func (%s) %s' % (pstr, self.body.tostr())


def evaluated_args(args, scope):
    return [arg.evaluate(scope) for arg in args]

def subtract_list(l):
    assert len(l) > 0
    return (l[0] - sum(l[1:])) if len(l) > 1 else (0 - l[0])

def divide_list(l):
    assert len(l) > 1
    return l[0] / reduce(lambda x, y: x * y, l[1:])

def rest_list(l):
    assert len(l) == 2
    return l[0] % l[1]


# 顶级域，父为None
top_scope = SScope(None, {})
# 顶级域加入 buildin 函数
# TODO: cast to int ??
top_scope.buildin('+', lambda args, scope: sum(evaluated_args(args, scope))).buildin(
                  '-', lambda args, scope: subtract_list(evaluated_args(args, scope))).buildin(
                  '*', lambda args, scope: reduce(lambda x, y: x * y, evaluated_args(args, scope))).buildin(
                  '/', lambda args, scope: divide_list(evaluated_args(args, scope))).buildin(
                  '%', lambda args, scope: rest_list(evaluated_args(args, scope)))


if __name__ == '__main__':
    """
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
    """

    exp = SExpression.parse('(* 2 (- (+ 3 4) 5)')
    print exp.tostr()
    res = exp.evaluate(top_scope)
    print res
