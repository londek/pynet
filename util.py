import ast
import logging

def cs_constant_repr(constant):
    if isinstance(constant, bool):
        return "true" if constant else "false"
    elif isinstance(constant, str):
        escaped = constant.replace("\\", "\\\\")
        return f"\"{escaped}\""
    elif isinstance(constant, int):
        return str(constant)

    logging.warn(f"unhandled repr for type {type(constant).__name__}")

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