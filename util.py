import ast
import itertools
import logging

def fullname(o):
    klass = o.__class__
    module = klass.__module__
    if module == 'builtins':
        return klass.__qualname__ # avoid outputs like 'builtins.str'
    return module + '.' + klass.__qualname__

def cs_constant_repr(constant):
    if isinstance(constant, bool):
        return "true" if constant else "false"
    elif isinstance(constant, str):
        escaped = constant.replace("\\", "\\\\")
        return f"\"{escaped}\""
    elif isinstance(constant, int):
        return str(constant)
    elif constant is None:
        return "null"

    logging.warn(f"unhandled repr for type {fullname(constant)}")

    return repr(constant)

def find_keyword(keywords: list[ast.keyword], name):
    for keyword in keywords:
        if keyword.arg == name:
            return keyword

    return None

def get_class_namespace(decorators: list[ast.expr]):
    for decorator in decorators:
        if not isinstance(decorator, ast.Call):
            continue

        if decorator.func.id != "namespace":
            continue

        return decorator.args[0].value

    return None

def statement(func):
    def helper(*args, **kwargs):
        self = args[0]
        self.cswriter.write_indents()
        func(*args, **kwargs)
        self.cswriter.write(";")
        

    return helper

def namespacable(func):
    def helper(*args, **kwargs):
        self, node = args
        
        namespace = get_class_namespace(node.decorator_list)
        if namespace:
            self.cswriter.write_indented(f"namespace {namespace}")
            with self.cswriter.block():
                func(*args, **kwargs)
        else:
            func(*args, **kwargs)
        

    return helper

def indented(func):
    def helper(*args, **kwargs):
        self = args[0]
        self.cswriter.write_indents()
        func(*args, **kwargs)
        

    return helper

def flatten(l):
    return list(itertools.chain.from_iterable(l))