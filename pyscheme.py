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
                # 最后，每个字符都会成为 SExpression
                cur.children.append(SExpression(lex, [], cur))
        # 返回 root 的第一个子节点，也就是第一层的括号
        return root.children[0]

    def evaluate(self, scope):
        # 如果无子节点，那么要么是数字，要么是变量
        # 其实还可以是操作符，但是操作符在下面有子节点的部分优先处理
        if len(self.children) == 0:
            # No.1 处理整数
            if self.value.isdigit():
                return int(self.value)
            # No.2 处理无子节点的变量，从 scope 中查找
            else:
                return scope.find(self.value)
        else:
            first = self.children[0]
            # No.3 处理 if, like (if (< a 3) 3 a)
            if first.value == 'if':
                return self.children[2].evaluate(scope) if self.children[1].evaluate(scope) else self.children[3].evaluate(scope)
            # No.4 处理 def， like (def pi 3.14)
            elif first.value == 'def':
                return scope.define(self.children[1].value, self.children[2].evaluate(scope))
            # No.5 处理 begin, like (begin (def a 3) (* a a))
            elif first.value == 'begin':
                for statement in self.children[1:]:
                    result = statement.evaluate(scope)
                return result
            # No.6 处理函数 func, like (func (x) (* x x))，生成一个 SFunc 对象，不做 evaluate
            # 更重要的是，func 中会构建子 scope
            elif first.value == 'func':
                # body, parameter string, sub scope
                return SFunc(self.children[2], [exp.value for exp in self.children[1].children], SScope(scope))
            # No.7 处理内置操作符
            elif first.value in top_scope.buildin_funcs:
                return top_scope.buildin_funcs[first.value](self.children[1:], scope)
            # No.8 处理自定义函数的调用， like ((func (x) (* x x)) 3)，暂时只实现单参数函数
            elif first.value == '(':
                func = first.evaluate(scope)
                argment = self.children[1].evaluate(scope)
                return func.update([argment]).evaluate()
        # 都不是，那么异常
        raise Exception("This is not invalid syntax.")


class SScope(object):
    # 每个作用域就是含有一个父作用域的一套标志字典和一套函数字典
    def __init__(self, parent, vt={}):
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

    # 函数中，只能操作函数作用域中定义的参数，能访问全局变量，但全局变量不能做参数
    def filled_parameters(self):
        return filter(lambda p: self.scope.find_in_top(p), self.parameters)

    # 给了部分参数，但是没给全部参数，这样就叫做 partial
    def is_partial(self):
        given_cnt = len(self.filled_parameters())
        return given_cnt >= 1 and given_cnt < len(self.parameters)

    # 函数生成时，还未有参数被赋值
    # 一旦有参数被赋值，那么更新作用域中的变量表，实际实现上是重新创建了一个作用域
    def update(self, argments):
        i = 0
        for p in self.parameters:
            # 前面的参数已经被赋值过
            if self.scope.find_in_top(p):
                continue
            # 后面的参数都是未赋值的
            self.scope.define(p, argments[i])
            i += 1
        return self

    def evaluate(self):
        given_cnt = len(self.filled_parameters())
        # 如果没给参数或 partial，那么仍然是个 SFunc
        if given_cnt < len(self.parameters):
            return self
        # 参数给全了，就可以估值了
        else:
            # 这里 evaluate 时可以访问全局变量
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

def compare_list(l, oper):
    assert len(l) == 2
    opers = {
        '=': lambda s1, s2: s1 == s2,
        '<': lambda s1, s2: s1 < s2,
        '>': lambda s1, s2: s1 > s2,
        '<=': lambda s1, s2: s1 <= s2,
        '>=': lambda s1, s2: s1 >= s2,
    }
    return opers[oper](l[0], l[1])


# 顶级域，父为None
top_scope = SScope(None)
# 顶级域加入 buildin 函数
top_scope.buildin('+', lambda args, scope: sum(evaluated_args(args, scope))).buildin(
                  '-', lambda args, scope: subtract_list(evaluated_args(args, scope))).buildin(
                  '*', lambda args, scope: reduce(lambda x, y: x * y, evaluated_args(args, scope))).buildin(
                  '/', lambda args, scope: divide_list(evaluated_args(args, scope))).buildin(
                  '%', lambda args, scope: rest_list(evaluated_args(args, scope))).buildin(
                  '=', lambda args, scope: compare_list(evaluated_args(args, scope), '=')).buildin(
                  '<', lambda args, scope: compare_list(evaluated_args(args, scope), '<')).buildin(
                  '>', lambda args, scope: compare_list(evaluated_args(args, scope), '>')).buildin(
                  '<=', lambda args, scope: compare_list(evaluated_args(args, scope), '<=')).buildin(
                  '>=', lambda args, scope: compare_list(evaluated_args(args, scope), '>=')).buildin(
                  'and', lambda args, scope: all(evaluated_args(args, scope))).buildin(
                  'or', lambda args, scope: any(evaluated_args(args, scope))).buildin(
                  'not', lambda args, scope: len(evaluated_args(args, scope)) == 1 and not evaluated_args(args, scope))


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
    for expression in ['(* 2 (- (+ 3 4) 5)', '(if (< 3 5) 5 3)', '(if (not (< 3 5)) 5 3)', '(if (and (< 3 5) (> 1 2)) 5 3)',
                       '(if (or (< 3 5) (> 1 2)) 5 3)', '(begin (def a 3) (* a a))', '((func (x) (* x x)) 3)']:
        exp = SExpression.parse(expression)
        print exp.tostr()
        res = exp.evaluate(top_scope)
        print res
        print ''
