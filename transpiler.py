import ast
import csast

from pathlib import Path
from cswriter import CSWriter
from util import cs_constant_repr, find_keyword, namespacable


class Transpiler(ast.NodeVisitor):
    cswriter = CSWriter()

    def __init__(self) -> None:
        super().__init__()
    
    def transpile(self, tree):
        self.visit(tree)
        return self.cswriter.build()

    def visit_Import(self, node: ast.Import):
        self.cswriter.write_indented(f"using {node.names[0].name};")

    @namespacable
    def visit_ClassDef(self, node: ast.ClassDef):
        access_modifier = get_access_modifier(node.decorator_list)
        funcs, fields = destructure_class(node)
        static = is_static(node.decorator_list)
        name = node.name
        inheritance = get_class_inheritance(node)

        self.cswriter.write_indented(f"{access_modifier}")
        if static:
            self.cswriter.write(f" static")

        self.cswriter.write(f" class {name}")

        if len(inheritance) > 0:
            self.cswriter.write(f" : {', '.join(inheritance)}")

        with self.cswriter.block():
            self.traverse(fields)
            self.traverse(funcs)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        access_modifier = get_access_modifier(node.decorator_list)
        static = is_static(node.decorator_list)
        overrides = does_method_override(node.decorator_list)
        name = node.name
        return_type = get_function_return_type(node)
        arguments = get_function_arguments(node)
        attributes = get_attributes(node.decorator_list)

        for attribute in attributes:
            self.cswriter.write_indented(attribute)

        self.cswriter.write_indented(f"{access_modifier}")
        if static:
            self.cswriter.write(f" static")
        else:
            if overrides:
                self.cswriter.write(f" override")
            node.body = replace_all_references(node.body, "self", "this")

        self.cswriter.write(f" {return_type} {name}({', '.join(arguments)})")

        with self.cswriter.block():
            self.traverse(node.body)

    def visit_Assign(self, node: ast.Assign):        
        target = node.targets[0]

        if isinstance(target, ast.Attribute):
            self.cswriter.write_indents()
        elif isinstance(target, ast.Name):
            self.cswriter.write_indented("var ")
        else:
            raise TranspilerExcetion("forbidden assignment target")

        self.traverse(node.targets[0])
        self.cswriter.write(" = ")
        self.traverse(node.value)
        self.cswriter.write(";")

    def visit_Attribute(self, node: ast.Attribute):
        self.traverse(node.value)
        self.cswriter.write(f".{node.attr}")

    def visit_Call(self, node: ast.Call):
        generics, args = destructure_args(node.args)

        self.visit(node.func)

        if len(generics) > 0:
            with self.cswriter.delimit_generic():
                self.cswriter.write(", ".join(generics))

        with self.cswriter.delimit_args():
            for arg in self.cswriter.enumerate_join(args, ", "):
                self.visit(arg)

    def visit_Name(self, node: ast.Name):
        self.cswriter.write(node.id)
    
    def visit_Expr(self, node: ast.Expr):
        self.cswriter.write_indents()
        self.traverse(node.value)
        self.cswriter.write(";")

    def visit_Return(self, node: ast.Return):
        self.cswriter.write_indented("return ")
        self.traverse(node.value)
        self.cswriter.write(";")

    def visit_Constant(self, node: ast.Constant):
        self.cswriter.write(cs_constant_repr(node.value))

    def visit_If(self, node: ast.If):
        self.cswriter.write_indented(f"if(")
        self.traverse(node.test)
        self.cswriter.write(")")
        with self.cswriter.block():
            self.traverse(node.body)

        while node.orelse and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            node = node.orelse[0]

            self.cswriter.write_indented(f"else if(")
            self.traverse(node.test)
            self.cswriter.write(")")
            with self.cswriter.block():
                self.traverse(node.body)
        
        if node.orelse:
            self.cswriter.write_indented("else")
            with self.cswriter.block():
                self.traverse(node.orelse)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self.traverse(node.annotation)
        self.cswriter.write(" ")
        self.traverse(node.target)
        self.cswriter.write(" = ")
        self.traverse(node.value)
        self.cswriter.write(";")

    boolops = {"And": "&&", "Or": "||"}

    def visit_BoolOp(self, node: ast.BoolOp):
        op = self.boolops[node.op.__class__.__name__]
        left, right = node.values[0], node.values[1]

        with self.cswriter.delimit_if("(", ")", is_comparer_node(left)):
            self.traverse(left)

        self.cswriter.write(f" {op} ")

        with self.cswriter.delimit_if("(", ")", is_comparer_node(right)):
            self.traverse(right)

    cmpops = {
        "Eq": "==",
        "NotEq": "!=",
        "Lt": "<",
        "LtE": "<=",
        "Gt": ">",
        "GtE": ">=",
        "Is": "is",
        "IsNot": "is not",
        "In": "in",
        "NotIn": "not in",
    }

    def visit_Compare(self, node: ast.Compare):
        op = self.cmpops[node.ops[0].__class__.__name__]
        self.traverse(node.left)
        self.cswriter.write(f" {op} ")
        self.traverse(node.comparators[0])

    def visit_Subscript(self, node: ast.Subscript):
        if isinstance(node.slice, ast.Slice):
            raise TranspilerExcetion("subslices are not supported")

        self.traverse(node.value)
        with self.cswriter.delimit("[", "]"):
            self.traverse(node.slice)

    def visit_For(self, node: ast.For):
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
            self.cswriter.write_indented("for")
            with self.cswriter.delimit_args():
                if node.iter.func.id == "range":
                    range_func = node.iter

                    begin = ast.Constant(value=0)
                    end = ast.Constant(value=0)
                    step = ast.Constant(value=1)

                    match len(range_func.args):
                        case 1:
                            end = range_func.args[0]
                        case 2:
                            begin = range_func.args[0]
                            end = range_func.args[1]
                        case 3:
                            begin = range_func[0]
                            end = range_func[1]
                            step = range_func[2]
                        case _:
                            raise TranspilerExcetion("unknown args for range in for loop")

                    # we have to assume type is int since there 
                    # are no type annotations for loops in Python
                    self.cswriter.write("var ") 
                    self.traverse(node.target)
                    self.cswriter.write(" = ")
                    self.traverse(begin)
                    self.cswriter.write("; ")
                    self.traverse(node.target)
                    self.cswriter.write(" < ")
                    self.traverse(end)
                    self.cswriter.write("; ")
                    self.traverse(node.target)
                    self.cswriter.write(" += ")
                    self.traverse(step)
        else:
            self.cswriter.write_indented("foreach")
            with self.cswriter.delimit_args():
                self.cswriter.write("var ")
                self.traverse(node.target)
                self.cswriter.write(" in ")
                self.traverse(node.iter)


        with self.cswriter.block():
            self.traverse(node.body)

    # CS SPECIFIC VISITORS
    def visit_CsFieldDef(self, node: csast.FieldDef):
        self.cswriter.write_indented(f"{node.visibility} ")

        if node.static:
            self.cswriter.write("static ")

        self.cswriter.write(f"{node.type.id} ")
        self.cswriter.write(f"{node.target.id}")

        if node.value is not None:
            self.cswriter.write(" = ")
            self.traverse(node.value)

        self.cswriter.write(";")

    def cs_visit(self, node: csast.AST):
        method = 'visit_Cs' + node.__class__.__name__
        visitor = getattr(self, method)
        return visitor(node)

    def traverse(self, node):
        if isinstance(node, list):
            for item in node:
                self.traverse(item)
        else:
            if isinstance(node, csast.AST):
                self.cs_visit(node)
            else:
                super().visit(node)

def is_static(decorators: list[ast.expr]): 
    for decorator in decorators:
        if not isinstance(decorator, ast.Name):
            continue

        if decorator.id == "static":
            return True
    
    return False

def is_comparer_node(node: ast.AST):
    return isinstance(node, ast.Compare) or isinstance(node, ast.BoolOp)

def get_access_modifier(decorators: list[ast.expr]): 
    ALLOWED_MODIFIERS = [ "public", "protected", "internal", "private" ]
    EXCEPTIONS = {
        "protected_internal": "protected internal",
        "private_protected": "private protected"
    }

    for decorator in decorators:
        # Access modifiers are non-call decorators only
        if not isinstance(decorator, ast.Name):
            continue

        if decorator.id in ALLOWED_MODIFIERS:
            return decorator.id
        elif decorator.id in EXCEPTIONS:
            return EXCEPTIONS[decorator.id]

    return "internal"

def get_class_inheritance(class_node: ast.ClassDef):
    inheritance = []

    decorators = class_node.decorator_list

    base = get_class_base(class_node)
    if base:
        inheritance.append(base)

    implementations = get_class_implementations(decorators)
    inheritance.extend(implementations)

    return inheritance

def get_class_base(class_node: ast.ClassDef):
    bases = class_node.bases
    if len(bases) == 0:
        return None

    return bases[0].id

def get_class_implementations(decorators: list[ast.expr]):
    implementations = []

    for decorator in decorators:
        if not isinstance(decorator, ast.Call):
            continue

        if decorator.func.id != "implements":
            continue

        implementations.append(decorator.args[0].id)

    return implementations

def get_class_fields(node: ast.ClassDef):
    fields = []

    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue

        if decorator.func.id != "field":
            continue

        access_modifier = "internal"
        field_type = None
        field_name = None

        if len(decorator.args) > 2:
            access_modifier = decorator.args[0].value
            field_type = decorator.args[1]
            field_name = decorator.args[2].value
        else:
            field_type = decorator.args[0]
            field_name = decorator.args[1].value

        value_keyword = find_keyword(decorator.keywords, "value")
        value = (value_keyword or None) and value_keyword.value # TODO: add support for literals

        static_keyword = find_keyword(decorator.keywords, "static")
        static = (static_keyword or False) and static_keyword.value.value

        field_def = csast.FieldDef(
            target=ast.Name(id=field_name),
            static=static,
            visibility=access_modifier,
            value=value,
            type=field_type
            
        )

        fields.append(field_def)

    for node in node.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        
        field_def = csast.FieldDef(
            target=node.target,
            type=node.annotation,
            visibility="public",
            static=False,
            value=node.value
        )

        fields.append(field_def)

    return fields

def get_attributes(decorators: list[ast.expr]):
    attributes = []

    for decorator in decorators:
        if not isinstance(decorator, ast.Call):
            continue

        if decorator.func.id != "attribute":
            continue

        # Python syntax should be alright for most implementations
        attributes.append(f"[{ast.unparse(decorator.args[0])}]")

    return attributes

def get_function_return_type(function_node: ast.FunctionDef):
    if not function_node.returns:
        return "void"

    return function_node.returns.id

def get_function_arguments(function_node: ast.FunctionDef):
    static = is_static(function_node.decorator_list)

    args = []

    start_index = 0 if static else 1

    for arg in function_node.args.args[start_index:]:
        if not arg.annotation:
            raise TranspilerExcetion(f"No type annotation for argument {arg.arg}")

        args.append(f"{arg.annotation.id} {arg.arg}")

    return args

def destructure_args(nodes: list[ast.expr]):
    generics = []
    args = []

    for node in nodes:
        if isinstance(node, ast.Call):
            if node.func.id == "generic":
                generics.append(node.args[0].id)
                continue

        args.append(node)

    return generics, args

def does_method_override(decorators: list[ast.expr]): 
    for decorator in decorators:
        if not isinstance(decorator, ast.Name):
            continue

        if decorator.id == "override":
            return True
    
    return False

def get_class_funcs(node: ast.ClassDef):
    return list(filter(lambda node: isinstance(node, ast.FunctionDef), node.body))

def destructure_class(node: ast.ClassDef):
    return get_class_funcs(node), get_class_fields(node)


class ReferenceReplacer(ast.NodeTransformer):
    def __init__(self, old, new):
        self.old = old
        self.new = new

    def visit_Name(self, node: ast.Name):
        if node.id == self.old:
            return ast.Name(id=self.new)
        return node

def replace_all_references(node, old, new):
    if isinstance(node, list):
        return [replace_all_references(item, old, new) for item in node]
    else:
        return ReferenceReplacer(old, new).visit(node)
        
class TranspilerExcetion(Exception):
    pass