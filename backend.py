import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any, Dict, List, Optional


KEYWORDS = {
    "function",
    "let",
    "var",
    "return",
    "while",
    "for",
    "if",
    "else",
    "break",
    "continue",
    "true",
    "false",
}

TYPE_KEYWORDS = {"int", "float", "string", "bool", "void"}


@dataclass
class Diagnostic:
    """Reporte unificado de diagnóstico del compilador por etapa y posición."""

    stage: str
    type: str
    message: str
    line: int
    column: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "type": self.type,
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    column: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "lexeme": self.lexeme,
            "line": self.line,
            "column": self.column,
        }


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.diagnostics: List[Diagnostic] = []

    def _peek(self) -> str:
        if self.index >= len(self.source):
            return "\0"
        return self.source[self.index]

    def _peek_next(self) -> str:
        nxt = self.index + 1
        if nxt >= len(self.source):
            return "\0"
        return self.source[nxt]

    def _advance(self) -> str:
        ch = self.source[self.index]
        self.index += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _add_token(self, token_type: str, lexeme: str, line: int, column: int):
        self.tokens.append(Token(token_type, lexeme, line, column))

    def tokenize(self) -> List[Token]:
        while self.index < len(self.source):
            ch = self._peek()
            start_line, start_col = self.line, self.column

            if ch in " \r\t":
                self._advance()
                continue
            if ch == "\n":
                self._advance()
                continue

            if ch == "/" and self._peek_next() == "/":
                while self._peek() not in {"\n", "\0"}:
                    self._advance()
                continue

            if ch.isalpha() or ch == "_":
                ident = []
                while self._peek().isalnum() or self._peek() == "_":
                    ident.append(self._advance())
                text = "".join(ident)
                if text in KEYWORDS:
                    self._add_token("KEYWORD", text, start_line, start_col)
                elif text in TYPE_KEYWORDS:
                    self._add_token("TYPE", text, start_line, start_col)
                else:
                    self._add_token("IDENTIFIER", text, start_line, start_col)
                continue

            if ch.isdigit():
                num = []
                seen_dot = False
                while True:
                    current = self._peek()
                    if current.isdigit():
                        num.append(self._advance())
                        continue
                    if current == "." and not seen_dot and self._peek_next().isdigit():
                        seen_dot = True
                        num.append(self._advance())
                        continue
                    break
                text = "".join(num)
                self._add_token("NUMBER", text, start_line, start_col)
                continue

            if ch == '"':
                self._advance()
                chars = []
                escaped = False
                while self._peek() != "\0":
                    current = self._advance()
                    if escaped:
                        chars.append(current)
                        escaped = False
                        continue
                    if current == "\\":
                        escaped = True
                        continue
                    if current == '"':
                        break
                    chars.append(current)
                if self.source[self.index - 1] != '"':
                    self.diagnostics.append(
                        Diagnostic(
                            stage="lexical",
                            type="LexicalError",
                            message="Cadena sin cerrar",
                            line=start_line,
                            column=start_col,
                        )
                    )
                else:
                    self._add_token("STRING", "".join(chars), start_line, start_col)
                continue

            two_char_ops = {"==", "!=", "<=", ">="}
            pair = ch + self._peek_next()
            if pair in two_char_ops:
                self._advance()
                self._advance()
                self._add_token("OPERATOR", pair, start_line, start_col)
                continue

            if ch in "+-*/=<>(){};,:!.":
                self._advance()
                token_type = "OPERATOR" if ch in "+-*/=<>!" else "PUNCTUATION"
                self._add_token(token_type, ch, start_line, start_col)
                continue

            self.diagnostics.append(
                Diagnostic(
                    stage="lexical",
                    type="LexicalError",
                    message=f"Carácter inválido: {ch}",
                    line=start_line,
                    column=start_col,
                )
            )
            self._advance()

        self.tokens.append(Token("EOF", "", self.line, self.column))
        return self.tokens


@dataclass
class Node:
    kind: str
    line: int
    column: int
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {"kind": self.kind, "line": self.line, "column": self.column}
        for k, v in self.data.items():
            result[k] = self._value_to_dict(v)
        return result

    def _value_to_dict(self, value: Any) -> Any:
        if isinstance(value, Node):
            return value.to_dict()
        if isinstance(value, list):
            return [self._value_to_dict(item) for item in value]
        return value


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.index = 0
        self.diagnostics: List[Diagnostic] = []

    def _current(self) -> Token:
        return self.tokens[self.index]

    def _previous(self) -> Token:
        return self.tokens[self.index - 1]

    def _is_at_end(self) -> bool:
        return self._current().type == "EOF"

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.index += 1
        return self._previous()

    def _check(self, token_type: str, lexeme: Optional[str] = None) -> bool:
        token = self._current()
        if token.type != token_type:
            return False
        return lexeme is None or token.lexeme == lexeme

    def _match(self, token_type: str, lexeme: Optional[str] = None) -> bool:
        if self._check(token_type, lexeme):
            self._advance()
            return True
        return False

    def _consume(self, token_type: str, message: str, lexeme: Optional[str] = None) -> Token:
        if self._check(token_type, lexeme):
            return self._advance()
        token = self._current()
        self.diagnostics.append(
            Diagnostic(
                stage="syntax",
                type="SyntaxError",
                message=message,
                line=token.line,
                column=token.column,
            )
        )
        return token

    def _synchronize(self):
        while not self._is_at_end():
            if self._previous().lexeme == ";":
                return
            if self._current().lexeme in {"function", "let", "var", "return", "while", "for", "if", "else", "break", "continue"}:
                return
            self._advance()

    def parse(self) -> Node:
        functions = []
        global_statements = []

        while not self._is_at_end():
            if self._check("KEYWORD", "function"):
                node = self._function_declaration()
                if node:
                    functions.append(node)
                continue
            stmt = self._statement()
            if stmt:
                global_statements.append(stmt)

        return Node(
            kind="Program",
            line=1,
            column=1,
            data={
                "functions": functions,
                "globalBlock": Node(
                    kind="GlobalProgramBlock",
                    line=1,
                    column=1,
                    data={"statements": global_statements},
                ),
            },
        )

    def _function_declaration(self) -> Optional[Node]:
        fn_token = self._consume("KEYWORD", "Se esperaba 'function'", "function")
        name = self._consume("IDENTIFIER", "Se esperaba nombre de función")
        self._consume("PUNCTUATION", "Se esperaba '('", "(")
        params = []
        if not self._check("PUNCTUATION", ")"):
            while True:
                param_name = self._consume("IDENTIFIER", "Se esperaba nombre de parámetro")
                param_type = None
                if self._match("PUNCTUATION", ":"):
                    param_type = self._consume("TYPE", "Se esperaba tipo de parámetro")
                params.append(
                    {
                        "name": param_name.lexeme,
                        "type": param_type.lexeme if param_type else "any",
                        "line": param_name.line,
                        "column": param_name.column,
                    }
                )
                if not self._match("PUNCTUATION", ","):
                    break
        self._consume("PUNCTUATION", "Se esperaba ')'", ")")

        return_type = "any"
        if self._match("PUNCTUATION", ":"):
            token = self._consume("TYPE", "Se esperaba tipo de retorno")
            return_type = token.lexeme

        body = self._block_statement()
        if not body:
            return None
        return Node(
            kind="FunctionDeclaration",
            line=fn_token.line,
            column=fn_token.column,
            data={
                "name": name.lexeme,
                "params": params,
                "returnType": return_type,
                "body": body,
            },
        )

    def _block_statement(self) -> Optional[Node]:
        token = self._consume("PUNCTUATION", "Se esperaba '{' para iniciar bloque", "{")
        start_line, start_col = token.line, token.column

        statements = []
        while not self._is_at_end() and not self._check("PUNCTUATION", "}"):
            stmt = self._statement()
            if stmt:
                statements.append(stmt)
        self._consume("PUNCTUATION", "Se esperaba '}' para cerrar bloque", "}")
        return Node(kind="BlockStatement", line=start_line, column=start_col, data={"statements": statements})

    def _statement(self) -> Optional[Node]:
        try:
            if self._match("KEYWORD", "let") or self._match("KEYWORD", "var"):
                return self._variable_declaration()
            if self._match("KEYWORD", "return"):
                return self._return_statement()
            if self._match("KEYWORD", "while"):
                return self._while_statement()
            if self._match("KEYWORD", "for"):
                return self._for_statement()
            if self._match("KEYWORD", "if"):
                return self._if_statement()
            if self._match("KEYWORD", "break"):
                token = self._previous()
                self._consume("PUNCTUATION", "Se esperaba ';' después de break", ";")
                return Node(kind="BreakStatement", line=token.line, column=token.column)
            if self._match("KEYWORD", "continue"):
                token = self._previous()
                self._consume("PUNCTUATION", "Se esperaba ';' después de continue", ";")
                return Node(kind="ContinueStatement", line=token.line, column=token.column)
            if self._match("PUNCTUATION", "{"):
                self.index -= 1
                return self._block_statement()
            return self._expression_or_assignment_statement()
        except Exception:
            self._synchronize()
            return None

    def _variable_declaration(self) -> Node:
        let_token = self._previous()
        name = self._consume("IDENTIFIER", "Se esperaba identificador")
        type_token = None
        if self._match("PUNCTUATION", ":"):
            type_token = self._consume("TYPE", "Se esperaba tipo en declaración")
        initializer = None
        if self._match("OPERATOR", "="):
            initializer = self._expression()
        self._consume("PUNCTUATION", "Se esperaba ';' al final de declaración", ";")
        return Node(
            kind="VariableDeclaration",
            line=let_token.line,
            column=let_token.column,
            data={"name": name.lexeme, "varType": type_token.lexeme if type_token else None, "initializer": initializer},
        )

    def _return_statement(self) -> Node:
        token = self._previous()
        value = None
        if not self._check("PUNCTUATION", ";"):
            value = self._expression()
        self._consume("PUNCTUATION", "Se esperaba ';' después de return", ";")
        return Node(kind="ReturnStatement", line=token.line, column=token.column, data={"value": value})

    def _while_statement(self) -> Node:
        token = self._previous()
        self._consume("PUNCTUATION", "Se esperaba '(' después de while", "(")
        condition = self._expression()
        self._consume("PUNCTUATION", "Se esperaba ')' después de condición while", ")")
        body = self._statement()
        return Node(kind="WhileStatement", line=token.line, column=token.column, data={"condition": condition, "body": body})

    def _for_statement(self) -> Node:
        token = self._previous()
        self._consume("PUNCTUATION", "Se esperaba '(' después de for", "(")

        initializer = None
        if self._match("KEYWORD", "let") or self._match("KEYWORD", "var"):
            initializer = self._variable_declaration_for()
        elif not self._check("PUNCTUATION", ";"):
            initializer = self._assignment_or_expression()
            self._consume("PUNCTUATION", "Se esperaba ';' en for", ";")
        else:
            self._consume("PUNCTUATION", "Se esperaba ';' en for", ";")

        condition = None
        if not self._check("PUNCTUATION", ";"):
            condition = self._expression()
        self._consume("PUNCTUATION", "Se esperaba ';' en for", ";")

        update = None
        if not self._check("PUNCTUATION", ")"):
            update = self._assignment_or_expression()
        self._consume("PUNCTUATION", "Se esperaba ')' en for", ")")

        body = self._statement()
        return Node(
            kind="ForStatement",
            line=token.line,
            column=token.column,
            data={"initializer": initializer, "condition": condition, "update": update, "body": body},
        )

    def _if_statement(self) -> Node:
        token = self._previous()
        self._consume("PUNCTUATION", "Se esperaba '(' después de if", "(")
        condition = self._expression()
        self._consume("PUNCTUATION", "Se esperaba ')' después de condición if", ")")
        then_branch = self._statement()
        else_branch = None
        if self._match("KEYWORD", "else"):
            else_branch = self._statement()
        return Node(
            kind="IfStatement",
            line=token.line,
            column=token.column,
            data={"condition": condition, "thenBranch": then_branch, "elseBranch": else_branch},
        )

    def _variable_declaration_for(self) -> Node:
        let_token = self._previous()
        name = self._consume("IDENTIFIER", "Se esperaba identificador")
        type_token = None
        if self._match("PUNCTUATION", ":"):
            type_token = self._consume("TYPE", "Se esperaba tipo en declaración")
        initializer = None
        if self._match("OPERATOR", "="):
            initializer = self._expression()
        self._consume("PUNCTUATION", "Se esperaba ';' en inicializador de for", ";")
        return Node(
            kind="VariableDeclaration",
            line=let_token.line,
            column=let_token.column,
            data={"name": name.lexeme, "varType": type_token.lexeme if type_token else None, "initializer": initializer},
        )

    def _expression_or_assignment_statement(self) -> Node:
        expr = self._assignment_or_expression()
        self._consume("PUNCTUATION", "Se esperaba ';' al final de sentencia", ";")
        return Node(kind="ExpressionStatement", line=expr.line, column=expr.column, data={"expression": expr})

    def _assignment_or_expression(self) -> Node:
        if self._check("IDENTIFIER") and self.index + 1 < len(self.tokens):
            next_token = self.tokens[self.index + 1]
            if next_token.type == "OPERATOR" and next_token.lexeme == "=":
                name = self._advance()
                equals = self._advance()
                value = self._expression()
                return Node(
                    kind="AssignmentExpression",
                    line=equals.line,
                    column=equals.column,
                    data={"name": name.lexeme, "value": value},
                )
        return self._expression()

    def _expression(self) -> Node:
        return self._equality()

    def _equality(self) -> Node:
        expr = self._comparison()
        while self._match("OPERATOR", "==") or self._match("OPERATOR", "!="):
            operator = self._previous()
            right = self._comparison()
            expr = Node(
                kind="BinaryExpression",
                line=operator.line,
                column=operator.column,
                data={"operator": operator.lexeme, "left": expr, "right": right},
            )
        return expr

    def _comparison(self) -> Node:
        expr = self._term()
        while (
            self._match("OPERATOR", "<")
            or self._match("OPERATOR", ">")
            or self._match("OPERATOR", "<=")
            or self._match("OPERATOR", ">=")
        ):
            operator = self._previous()
            right = self._term()
            expr = Node(
                kind="BinaryExpression",
                line=operator.line,
                column=operator.column,
                data={"operator": operator.lexeme, "left": expr, "right": right},
            )
        return expr

    def _term(self) -> Node:
        expr = self._factor()
        while self._match("OPERATOR", "+") or self._match("OPERATOR", "-"):
            operator = self._previous()
            right = self._factor()
            expr = Node(
                kind="BinaryExpression",
                line=operator.line,
                column=operator.column,
                data={"operator": operator.lexeme, "left": expr, "right": right},
            )
        return expr

    def _factor(self) -> Node:
        expr = self._unary()
        while self._match("OPERATOR", "*") or self._match("OPERATOR", "/"):
            operator = self._previous()
            right = self._unary()
            expr = Node(
                kind="BinaryExpression",
                line=operator.line,
                column=operator.column,
                data={"operator": operator.lexeme, "left": expr, "right": right},
            )
        return expr

    def _unary(self) -> Node:
        if self._match("OPERATOR", "-"):
            operator = self._previous()
            right = self._unary()
            return Node(kind="UnaryExpression", line=operator.line, column=operator.column, data={"operator": "-", "right": right})
        return self._primary()

    def _primary(self) -> Node:
        if self._match("NUMBER"):
            token = self._previous()
            value_type = "float" if "." in token.lexeme else "int"
            return Node(kind="Literal", line=token.line, column=token.column, data={"value": token.lexeme, "valueType": value_type})
        if self._match("STRING"):
            token = self._previous()
            return Node(kind="Literal", line=token.line, column=token.column, data={"value": token.lexeme, "valueType": "string"})
        if self._match("KEYWORD", "true"):
            token = self._previous()
            return Node(kind="Literal", line=token.line, column=token.column, data={"value": True, "valueType": "bool"})
        if self._match("KEYWORD", "false"):
            token = self._previous()
            return Node(kind="Literal", line=token.line, column=token.column, data={"value": False, "valueType": "bool"})

        if self._match("IDENTIFIER"):
            ident = self._previous()
            qualified_name = ident.lexeme
            while self._match("PUNCTUATION", "."):
                member = self._consume("IDENTIFIER", "Se esperaba identificador después de '.'")
                qualified_name = f"{qualified_name}.{member.lexeme}"
            if self._match("PUNCTUATION", "("):
                args = []
                if not self._check("PUNCTUATION", ")"):
                    while True:
                        args.append(self._expression())
                        if not self._match("PUNCTUATION", ","):
                            break
                self._consume("PUNCTUATION", "Se esperaba ')' en llamada", ")")
                return Node(kind="FunctionCall", line=ident.line, column=ident.column, data={"name": qualified_name, "arguments": args})
            return Node(kind="Identifier", line=ident.line, column=ident.column, data={"name": qualified_name})

        if self._match("PUNCTUATION", "("):
            expr = self._expression()
            self._consume("PUNCTUATION", "Se esperaba ')'", ")")
            return expr

        token = self._current()
        self.diagnostics.append(
            Diagnostic(
                stage="syntax",
                type="SyntaxError",
                message=f"Token inesperado: {token.lexeme or token.type}",
                line=token.line,
                column=token.column,
            )
        )
        self._advance()
        return Node(kind="Literal", line=token.line, column=token.column, data={"value": 0, "valueType": "int"})


class Scope:
    def __init__(self, parent: Optional["Scope"] = None):
        self.parent = parent
        self.symbols: Dict[str, str] = {}

    def define(self, name: str, typ: str) -> bool:
        if name in self.symbols:
            return False
        self.symbols[name] = typ
        return True

    def resolve(self, name: str) -> Optional[str]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None

    def assign(self, name: str, typ: str) -> bool:
        if name in self.symbols:
            self.symbols[name] = typ
            return True
        if self.parent:
            return self.parent.assign(name, typ)
        return False


class SemanticAnalyzer:
    def __init__(self):
        self.diagnostics: List[Diagnostic] = []
        self.functions: Dict[str, Dict[str, Any]] = {}

    def analyze(self, program: Node) -> List[Diagnostic]:
        functions = program.data["functions"]
        for fn in functions:
            name = fn.data["name"]
            if name in self.functions:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", f"Función redeclarada: {name}", fn.line, fn.column)
                )
                continue
            self.functions[name] = {
                "params": [p["type"] for p in fn.data["params"]],
                "returnType": fn.data["returnType"],
                "node": fn,
            }

        global_scope = Scope()
        self._analyze_block(program.data["globalBlock"], global_scope, current_fn=None, loop_depth=0)

        for fn in functions:
            fn_scope = Scope(global_scope)
            for p in fn.data["params"]:
                if not fn_scope.define(p["name"], p["type"]):
                    self.diagnostics.append(
                        Diagnostic("semantic", "SemanticError", f"Parámetro redeclarado: {p['name']}", p["line"], p["column"])
                    )
            has_return = self._analyze_block(fn.data["body"], fn_scope, current_fn=fn, loop_depth=0)
            if fn.data["returnType"] not in {"void", "any"} and not has_return:
                self.diagnostics.append(
                    Diagnostic(
                        "semantic",
                        "SemanticError",
                        f"La función '{fn.data['name']}' debe retornar '{fn.data['returnType']}'",
                        fn.line,
                        fn.column,
                    )
                )

        return self.diagnostics

    def _analyze_block(self, block: Node, scope: Scope, current_fn: Optional[Node], loop_depth: int) -> bool:
        local_scope = Scope(scope)
        has_return = False
        for stmt in block.data["statements"]:
            stmt_return = self._analyze_statement(stmt, local_scope, current_fn, loop_depth)
            has_return = has_return or stmt_return
        return has_return

    def _analyze_statement(self, stmt: Node, scope: Scope, current_fn: Optional[Node], loop_depth: int) -> bool:
        kind = stmt.kind
        if kind == "VariableDeclaration":
            declared_type = stmt.data.get("varType")
            initializer = stmt.data.get("initializer")
            inferred_type = self._infer_expr_type(initializer, scope) if initializer else None
            final_type = declared_type or inferred_type or "any"
            if not scope.define(stmt.data["name"], final_type):
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", f"Variable redeclarada: {stmt.data['name']}", stmt.line, stmt.column)
                )
            if initializer and declared_type and declared_type != "any":
                expr_type = inferred_type
                if expr_type and expr_type != declared_type:
                    self.diagnostics.append(
                        Diagnostic(
                            "semantic",
                            "SemanticError",
                            (
                                f"Tipo incompatible: se esperaba {declared_type} y se recibió {expr_type}. "
                                f"Sugerencia: declara '{stmt.data['name']}: {expr_type}' o cambia el valor a tipo {declared_type}."
                            ),
                            stmt.line,
                            stmt.column,
                        )
                    )
            return False

        if kind == "ExpressionStatement":
            self._infer_expr_type(stmt.data["expression"], scope)
            return False

        if kind == "ReturnStatement":
            if not current_fn:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", "'return' fuera de función", stmt.line, stmt.column)
                )
                return True
            fn_return = current_fn.data["returnType"]
            value = stmt.data.get("value")
            if fn_return == "void" and value is not None:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", "Una función void no debe retornar valor", stmt.line, stmt.column)
                )
                self._infer_expr_type(value, scope)
            elif fn_return == "any" and value is not None:
                self._infer_expr_type(value, scope)
            elif fn_return not in {"void", "any"}:
                if value is None:
                    self.diagnostics.append(
                        Diagnostic("semantic", "SemanticError", f"Se esperaba retorno de tipo {fn_return}", stmt.line, stmt.column)
                    )
                else:
                    value_type = self._infer_expr_type(value, scope)
                    if value_type and value_type != fn_return:
                        self.diagnostics.append(
                            Diagnostic(
                                "semantic",
                                "SemanticError",
                                f"Tipo de retorno inválido: {value_type}, se esperaba {fn_return}",
                                stmt.line,
                                stmt.column,
                            )
                        )
            return True

        if kind == "BlockStatement":
            return self._analyze_block(stmt, scope, current_fn, loop_depth)

        if kind == "WhileStatement":
            cond_type = self._infer_expr_type(stmt.data["condition"], scope)
            if cond_type and cond_type != "bool":
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", "La condición de while debe ser bool", stmt.line, stmt.column)
                )
            return self._analyze_statement(stmt.data["body"], scope, current_fn, loop_depth + 1)

        if kind == "ForStatement":
            for_scope = Scope(scope)
            initializer = stmt.data.get("initializer")
            if initializer:
                if initializer.kind == "VariableDeclaration":
                    self._analyze_statement(initializer, for_scope, current_fn, loop_depth + 1)
                else:
                    self._infer_expr_type(initializer, for_scope)
            condition = stmt.data.get("condition")
            if condition:
                cond_type = self._infer_expr_type(condition, for_scope)
                if cond_type and cond_type != "bool":
                    self.diagnostics.append(
                        Diagnostic("semantic", "SemanticError", "La condición de for debe ser bool", stmt.line, stmt.column)
                    )
            update = stmt.data.get("update")
            if update:
                self._infer_expr_type(update, for_scope)
            return self._analyze_statement(stmt.data["body"], for_scope, current_fn, loop_depth + 1)

        if kind == "IfStatement":
            cond_type = self._infer_expr_type(stmt.data["condition"], scope)
            if cond_type and cond_type != "bool":
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", "La condición de if debe ser bool", stmt.line, stmt.column)
                )
            self._analyze_statement(stmt.data["thenBranch"], scope, current_fn, loop_depth)
            if stmt.data.get("elseBranch"):
                self._analyze_statement(stmt.data["elseBranch"], scope, current_fn, loop_depth)
            return False

        if kind == "BreakStatement":
            if loop_depth <= 0:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", "'break' fuera de un bucle", stmt.line, stmt.column)
                )
            return False

        if kind == "ContinueStatement":
            if loop_depth <= 0:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", "'continue' fuera de un bucle", stmt.line, stmt.column)
                )
            return False

        return False

    def _infer_expr_type(self, expr: Node, scope: Scope) -> Optional[str]:
        if expr.kind == "Literal":
            return expr.data["valueType"]
        if expr.kind == "Identifier":
            typ = scope.resolve(expr.data["name"])
            if not typ:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", f"Variable no declarada: {expr.data['name']}", expr.line, expr.column)
                )
            return typ
        if expr.kind == "AssignmentExpression":
            target_type = scope.resolve(expr.data["name"])
            if not target_type:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", f"Variable no declarada: {expr.data['name']}", expr.line, expr.column)
                )
                return None
            value_type = self._infer_expr_type(expr.data["value"], scope)
            if target_type == "any" and value_type:
                scope.assign(expr.data["name"], value_type)
                return value_type
            if value_type and target_type != "any" and value_type != target_type:
                self.diagnostics.append(
                    Diagnostic(
                        "semantic",
                        "SemanticError",
                        (
                            f"Asignación incompatible para '{expr.data['name']}': {value_type} -> {target_type}. "
                            f"Sugerencia: convierte '{value_type}' a '{target_type}' o cambia el tipo de '{expr.data['name']}'."
                        ),
                        expr.line,
                        expr.column,
                    )
                )
            return target_type
        if expr.kind == "UnaryExpression":
            right = self._infer_expr_type(expr.data["right"], scope)
            if right not in {"int", "float"}:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", "Operador '-' requiere número", expr.line, expr.column)
                )
            return right
        if expr.kind == "BinaryExpression":
            left = self._infer_expr_type(expr.data["left"], scope)
            right = self._infer_expr_type(expr.data["right"], scope)
            op = expr.data["operator"]
            if op in {"+", "-", "*", "/"}:
                if left == "any" or right == "any":
                    return "any"
                if left not in {"int", "float"} or right not in {"int", "float"}:
                    self.diagnostics.append(
                        Diagnostic("semantic", "SemanticError", f"Operación '{op}' requiere operandos numéricos", expr.line, expr.column)
                    )
                    return None
                if left == "float" or right == "float":
                    return "float"
                return "int"
            if op in {"==", "!=", "<", ">", "<=", ">="}:
                if left != right:
                    self.diagnostics.append(
                        Diagnostic("semantic", "SemanticError", "Comparación entre tipos incompatibles", expr.line, expr.column)
                    )
                return "bool"
        if expr.kind == "FunctionCall":
            if expr.data["name"] == "console.log":
                for arg in expr.data["arguments"]:
                    self._infer_expr_type(arg, scope)
                return "void"
            signature = self.functions.get(expr.data["name"])
            if not signature:
                self.diagnostics.append(
                    Diagnostic("semantic", "SemanticError", f"Función no declarada: {expr.data['name']}", expr.line, expr.column)
                )
                return None
            expected = signature["params"]
            actual = expr.data["arguments"]
            if len(expected) != len(actual):
                self.diagnostics.append(
                    Diagnostic(
                        "semantic",
                        "SemanticError",
                        (
                            f"La función '{expr.data['name']}' esperaba {len(expected)} argumentos y recibió {len(actual)}. "
                            f"Firma esperada: {expr.data['name']}({', '.join(expected)})."
                        ),
                        expr.line,
                        expr.column,
                    )
                )
            for idx, arg in enumerate(actual):
                arg_type = self._infer_expr_type(arg, scope)
                if idx < len(expected) and arg_type and expected[idx] != "any" and arg_type != expected[idx]:
                    self.diagnostics.append(
                        Diagnostic(
                            "semantic",
                            "SemanticError",
                            f"Argumento {idx + 1} de '{expr.data['name']}' debe ser {expected[idx]} y recibió {arg_type}",
                            arg.line,
                            arg.column,
                        )
                    )
            return signature["returnType"]
        return None


class NasmCodeGenerator:
    def __init__(self):
        self.lines: List[str] = []
        self.data_lines: List[str] = []
        self.bss_lines: List[str] = []
        self.label_counter = 0
        self.var_labels: Dict[str, str] = {}
        self.break_stack: List[str] = []
        self.continue_stack: List[str] = []

    def _new_label(self, prefix: str) -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def generate(self, program: Node) -> str:
        self.lines = ["section .text", "global _start", ""]
        self.data_lines = ["section .data"]
        self.bss_lines = ["section .bss"]

        self.lines.append("_start:")
        self.lines.append("  ; Regla de prioridad: ejecutar primero bloque global implícito y luego main() explícito si existe")
        self._emit_block(program.data["globalBlock"], scope_name="global")

        has_main = any(fn.data["name"] == "main" for fn in program.data["functions"])
        if has_main:
            self.lines.append("  call fn_main")

        self.lines.extend(
            [
                "  mov eax, 1",
                "  xor ebx, ebx",
                "  int 0x80",
                "",
            ]
        )

        for fn in program.data["functions"]:
            self.lines.append(f"fn_{fn.data['name']}:")
            self._emit_block(fn.data["body"], scope_name=f"fn_{fn.data['name']}")
            if fn.data["returnType"] == "void":
                self.lines.append("  xor eax, eax")
            self.lines.append("  ret")
            self.lines.append("")

        output = []
        if len(self.data_lines) > 1:
            output.extend(self.data_lines)
            output.append("")
        if len(self.bss_lines) > 1:
            output.extend(self.bss_lines)
            output.append("")
        output.extend(self.lines)
        return "\n".join(output)

    def _get_var_label(self, scope_name: str, var_name: str) -> str:
        key = f"{scope_name}:{var_name}"
        if key not in self.var_labels:
            label = f"var_{scope_name.replace(':', '_')}_{var_name}"
            self.var_labels[key] = label
            self.bss_lines.append(f"{label}: resd 1")
        return self.var_labels[key]

    def _find_var_label(self, var_name: str) -> Optional[str]:
        for key, label in reversed(list(self.var_labels.items())):
            if key.split(":", 1)[1] == var_name:
                return label
        return None

    def _emit_block(self, block: Node, scope_name: str):
        for stmt in block.data["statements"]:
            self._emit_statement(stmt, scope_name)

    def _emit_statement(self, stmt: Node, scope_name: str):
        kind = stmt.kind
        if kind == "VariableDeclaration":
            label = self._get_var_label(scope_name, stmt.data["name"])
            if stmt.data.get("initializer"):
                self._emit_expression(stmt.data["initializer"], scope_name)
                self.lines.append(f"  mov [{label}], eax")
            else:
                self.lines.append(f"  mov dword [{label}], 0")
            return

        if kind == "ExpressionStatement":
            self._emit_expression(stmt.data["expression"], scope_name)
            return

        if kind == "ReturnStatement":
            if stmt.data.get("value"):
                self._emit_expression(stmt.data["value"], scope_name)
            self.lines.append("  ret")
            return

        if kind == "BlockStatement":
            self._emit_block(stmt, scope_name)
            return

        if kind == "WhileStatement":
            start = self._new_label("while_start")
            end = self._new_label("while_end")
            self.break_stack.append(end)
            self.continue_stack.append(start)
            self.lines.append(f"{start}:")
            self._emit_expression(stmt.data["condition"], scope_name)
            self.lines.append("  cmp eax, 0")
            self.lines.append(f"  je {end}")
            self._emit_statement(stmt.data["body"], scope_name)
            self.lines.append(f"  jmp {start}")
            self.lines.append(f"{end}:")
            self.break_stack.pop()
            self.continue_stack.pop()
            return

        if kind == "IfStatement":
            else_label = self._new_label("if_else")
            end_label = self._new_label("if_end")
            self._emit_expression(stmt.data["condition"], scope_name)
            self.lines.append("  cmp eax, 0")
            self.lines.append(f"  je {else_label}")
            self._emit_statement(stmt.data["thenBranch"], scope_name)
            self.lines.append(f"  jmp {end_label}")
            self.lines.append(f"{else_label}:")
            if stmt.data.get("elseBranch"):
                self._emit_statement(stmt.data["elseBranch"], scope_name)
            self.lines.append(f"{end_label}:")
            return

        if kind == "ForStatement":
            start = self._new_label("for_start")
            end = self._new_label("for_end")
            update_label = self._new_label("for_update")
            self.break_stack.append(end)
            self.continue_stack.append(update_label)

            if stmt.data.get("initializer"):
                if stmt.data["initializer"].kind == "VariableDeclaration":
                    self._emit_statement(stmt.data["initializer"], scope_name)
                else:
                    self._emit_expression(stmt.data["initializer"], scope_name)

            self.lines.append(f"{start}:")
            if stmt.data.get("condition"):
                self._emit_expression(stmt.data["condition"], scope_name)
                self.lines.append("  cmp eax, 0")
                self.lines.append(f"  je {end}")
            self._emit_statement(stmt.data["body"], scope_name)
            self.lines.append(f"{update_label}:")
            if stmt.data.get("update"):
                self._emit_expression(stmt.data["update"], scope_name)
            self.lines.append(f"  jmp {start}")
            self.lines.append(f"{end}:")

            self.break_stack.pop()
            self.continue_stack.pop()
            return

        if kind == "BreakStatement":
            if self.break_stack:
                self.lines.append(f"  jmp {self.break_stack[-1]}")
            return

        if kind == "ContinueStatement":
            if self.continue_stack:
                self.lines.append(f"  jmp {self.continue_stack[-1]}")
            return

    def _emit_expression(self, expr: Node, scope_name: str):
        if expr.kind == "Literal":
            value = expr.data["value"]
            if isinstance(value, bool):
                value = 1 if value else 0
            if isinstance(value, str) and expr.data["valueType"] == "string":
                label = self._new_label("str")
                encoded = value.replace('"', '\\"')
                self.data_lines.append(f'{label}: db "{encoded}", 0')
                self.lines.append(f"  mov eax, {label}")
            else:
                self.lines.append(f"  mov eax, {value}")
            return

        if expr.kind == "Identifier":
            label = self._find_var_label(expr.data["name"])
            if label:
                self.lines.append(f"  mov eax, [{label}]")
            else:
                self.lines.append("  xor eax, eax")
            return

        if expr.kind == "AssignmentExpression":
            self._emit_expression(expr.data["value"], scope_name)
            label = self._find_var_label(expr.data["name"])
            if label:
                self.lines.append(f"  mov [{label}], eax")
            return

        if expr.kind == "UnaryExpression":
            self._emit_expression(expr.data["right"], scope_name)
            self.lines.append("  neg eax")
            return

        if expr.kind == "BinaryExpression":
            self._emit_expression(expr.data["left"], scope_name)
            self.lines.append("  push eax")
            self._emit_expression(expr.data["right"], scope_name)
            self.lines.append("  mov ebx, eax")
            self.lines.append("  pop eax")
            op = expr.data["operator"]
            if op == "+":
                self.lines.append("  add eax, ebx")
            elif op == "-":
                self.lines.append("  sub eax, ebx")
            elif op == "*":
                self.lines.append("  imul eax, ebx")
            elif op == "/":
                self.lines.append("  cdq")
                self.lines.append("  idiv ebx")
            else:
                self.lines.append("  cmp eax, ebx")
                if op == "==":
                    self.lines.append("  sete al")
                elif op == "!=":
                    self.lines.append("  setne al")
                elif op == "<":
                    self.lines.append("  setl al")
                elif op == ">":
                    self.lines.append("  setg al")
                elif op == "<=":
                    self.lines.append("  setle al")
                elif op == ">=":
                    self.lines.append("  setge al")
                self.lines.append("  movzx eax, al")
            return

        if expr.kind == "FunctionCall":
            if expr.data["name"] == "console.log":
                if expr.data["arguments"]:
                    self._emit_expression(expr.data["arguments"][-1], scope_name)
                else:
                    self.lines.append("  xor eax, eax")
                self.lines.append("  ; console.log manejado en ejecución del compilador")
                return
            for arg in expr.data["arguments"]:
                self._emit_expression(arg, scope_name)
            self.lines.append(f"  call fn_{expr.data['name']}")
            return


class RuntimeScope:
    def __init__(self, parent: Optional["RuntimeScope"] = None):
        self.parent = parent
        self.values: Dict[str, Any] = {}

    def define(self, name: str, value: Any):
        self.values[name] = value

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.get(name)
        raise RuntimeError(f"Variable no declarada: {name}")

    def assign(self, name: str, value: Any):
        if name in self.values:
            self.values[name] = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        raise RuntimeError(f"Variable no declarada: {name}")


class RuntimeControl(Exception):
    pass


class RuntimeReturn(RuntimeControl):
    def __init__(self, value: Any):
        self.value = value


class RuntimeBreak(RuntimeControl):
    pass


class RuntimeContinue(RuntimeControl):
    pass


class ExecutionEngine:
    def __init__(self):
        self.outputs: List[str] = []
        self.functions: Dict[str, Node] = {}

    def execute(self, program: Node) -> List[str]:
        self.outputs = []
        self.functions = {fn.data["name"]: fn for fn in program.data["functions"]}
        global_scope = RuntimeScope()
        self._exec_block(program.data["globalBlock"], global_scope)
        if "main" in self.functions:
            self._call_function("main", [], global_scope)
        return self.outputs

    def _exec_block(self, block: Node, scope: RuntimeScope):
        block_scope = RuntimeScope(scope)
        for stmt in block.data["statements"]:
            self._exec_statement(stmt, block_scope)

    def _exec_statement(self, stmt: Node, scope: RuntimeScope):
        kind = stmt.kind
        if kind == "VariableDeclaration":
            value = self._eval_expression(stmt.data["initializer"], scope) if stmt.data.get("initializer") else 0
            scope.define(stmt.data["name"], value)
            return
        if kind == "ExpressionStatement":
            self._eval_expression(stmt.data["expression"], scope)
            return
        if kind == "ReturnStatement":
            value = self._eval_expression(stmt.data["value"], scope) if stmt.data.get("value") else None
            raise RuntimeReturn(value)
        if kind == "BlockStatement":
            self._exec_block(stmt, scope)
            return
        if kind == "IfStatement":
            if self._eval_expression(stmt.data["condition"], scope):
                self._exec_statement(stmt.data["thenBranch"], scope)
            elif stmt.data.get("elseBranch"):
                self._exec_statement(stmt.data["elseBranch"], scope)
            return
        if kind == "WhileStatement":
            while self._eval_expression(stmt.data["condition"], scope):
                try:
                    self._exec_statement(stmt.data["body"], scope)
                except RuntimeContinue:
                    continue
                except RuntimeBreak:
                    break
            return
        if kind == "ForStatement":
            loop_scope = RuntimeScope(scope)
            if stmt.data.get("initializer"):
                self._exec_statement(stmt.data["initializer"], loop_scope)
            while True:
                condition = stmt.data.get("condition")
                if condition is not None and not self._eval_expression(condition, loop_scope):
                    break
                try:
                    self._exec_statement(stmt.data["body"], loop_scope)
                except RuntimeContinue:
                    pass
                except RuntimeBreak:
                    break
                if stmt.data.get("update"):
                    self._eval_expression(stmt.data["update"], loop_scope)
            return
        if kind == "BreakStatement":
            raise RuntimeBreak()
        if kind == "ContinueStatement":
            raise RuntimeContinue()

    def _eval_expression(self, expr: Optional[Node], scope: RuntimeScope) -> Any:
        if expr is None:
            return None
        if expr.kind == "Literal":
            return expr.data["value"]
        if expr.kind == "Identifier":
            return scope.get(expr.data["name"])
        if expr.kind == "AssignmentExpression":
            value = self._eval_expression(expr.data["value"], scope)
            scope.assign(expr.data["name"], value)
            return value
        if expr.kind == "UnaryExpression":
            right = self._eval_expression(expr.data["right"], scope)
            if expr.data["operator"] == "-":
                return -right
        if expr.kind == "BinaryExpression":
            left = self._eval_expression(expr.data["left"], scope)
            right = self._eval_expression(expr.data["right"], scope)
            op = expr.data["operator"]
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    raise RuntimeError("División entre cero en tiempo de ejecución")
                if isinstance(left, int) and isinstance(right, int):
                    return left // right
                return left / right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            if op == ">=":
                return left >= right
        if expr.kind == "FunctionCall":
            if expr.data["name"] == "console.log":
                values = [self._eval_expression(arg, scope) for arg in expr.data["arguments"]]
                self.outputs.append(" ".join(str(v) for v in values))
                return None
            args = [self._eval_expression(arg, scope) for arg in expr.data["arguments"]]
            return self._call_function(expr.data["name"], args, scope)
        return None

    def _call_function(self, name: str, args: List[Any], scope: RuntimeScope) -> Any:
        function = self.functions.get(name)
        if not function:
            raise RuntimeError(f"Función no declarada: {name}")
        params = function.data["params"]
        if len(params) != len(args):
            raise RuntimeError(f"La función '{name}' esperaba {len(params)} argumentos y recibió {len(args)}")
        fn_scope = RuntimeScope(scope)
        for idx, param in enumerate(params):
            fn_scope.define(param["name"], args[idx])
        try:
            self._exec_block(function.data["body"], fn_scope)
        except RuntimeReturn as result:
            return result.value
        return None


class CompilationPipeline:
    def run(self, source: str, stage: str = "compile") -> Dict[str, Any]:
        process_logs = ["Análisis léxico iniciado."]
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        diagnostics = list(lexer.diagnostics)
        process_logs.append("Análisis léxico completado.")

        token_payload = [t.to_dict() for t in tokens if t.type != "EOF"]

        def make_payload(ast_node: Optional[Node] = None, nasm: str = "", execution: Optional[List[str]] = None) -> Dict[str, Any]:
            return {
                "tokens": token_payload,
                "ast": ast_node.to_dict() if ast_node else None,
                "diagnostics": [d.to_dict() for d in diagnostics],
                "nasm": nasm,
                "execution": execution or [],
                "processLogs": process_logs,
            }

        if stage == "lexical":
            process_logs.append("Etapa léxica finalizada.")
            return make_payload()

        if any(d.stage == "lexical" for d in diagnostics):
            process_logs.append("Errores léxicos detectados. Se detiene el pipeline.")
            return make_payload()

        process_logs.append("Parsing iniciado.")
        parser = Parser(tokens)
        ast = parser.parse()
        diagnostics.extend(parser.diagnostics)
        process_logs.append("Parsing completado.")

        if stage == "syntax":
            process_logs.append("Etapa sintáctica finalizada.")
            return make_payload(ast_node=ast)

        syntax_errors = [d for d in diagnostics if d.stage == "syntax"]
        if syntax_errors:
            process_logs.append("Errores sintácticos detectados. Se omiten etapas posteriores.")
            return make_payload(ast_node=ast)

        process_logs.append("Análisis semántico iniciado.")
        semantic = SemanticAnalyzer()
        diagnostics.extend(semantic.analyze(ast))
        process_logs.append("Análisis semántico completado.")

        if stage == "semantic":
            process_logs.append("Etapa semántica finalizada.")
            return make_payload(ast_node=ast)

        semantic_errors = [d for d in diagnostics if d.stage == "semantic"]
        nasm = ""
        execution: List[str] = []
        if not semantic_errors:
            process_logs.append("Generación de ensamblador iniciada.")
            generator = NasmCodeGenerator()
            nasm = generator.generate(ast)
            process_logs.append("Generación de ensamblador completada.")

            process_logs.append("Ejecución del programa iniciada.")
            try:
                execution = ExecutionEngine().execute(ast)
                process_logs.append("Ejecución del programa completada.")
            except RuntimeError as exc:
                diagnostics.append(Diagnostic("execution", "RuntimeError", str(exc), 1, 1))
                process_logs.append("Ejecución del programa finalizada con error.")
        else:
            process_logs.append("Errores semánticos detectados. Se omiten ensamblador y ejecución.")

        return make_payload(ast_node=ast, nasm=nasm, execution=execution)


class BackendHandler(BaseHTTPRequestHandler):
    pipeline = CompilationPipeline()

    def _send_json(self, status: int, payload: Dict[str, Any]):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_POST(self):
        endpoint_map = {
            "/api/lexico": "lexical",
            "/api/sintactico": "syntax",
            "/api/semantico": "semantic",
            "/api/compile": "compile",
        }
        if self.path not in endpoint_map:
            self._send_json(404, {"error": "Ruta no encontrada"})
            return

        try:
            payload = self._read_json()
            source = str(payload.get("source") or payload.get("expression") or "")
            if not source.strip():
                self._send_json(
                    400,
                    {
                        "diagnostics": [
                            Diagnostic("input", "ValidationError", "El código fuente está vacío", 1, 1).to_dict()
                        ]
                    },
                )
                return
            result = self.pipeline.run(source, stage=endpoint_map[self.path])
            has_errors = any(d["type"].endswith("Error") for d in result.get("diagnostics", []))
            self._send_json(400 if has_errors else 200, result)
        except json.JSONDecodeError:
            self._send_json(
                400,
                {"diagnostics": [Diagnostic("input", "ValidationError", "JSON inválido", 1, 1).to_dict()]},
            )
        except (TypeError, ValueError, KeyError) as exc:
            self._send_json(
                400,
                {"diagnostics": [Diagnostic("input", "ValidationError", str(exc), 1, 1).to_dict()]},
            )
        except Exception as exc:  # pragma: no cover
            self._send_json(
                500,
                {
                    "diagnostics": [
                        Diagnostic("internal", "InternalError", f"Error interno: {exc}", 1, 1).to_dict()
                    ]
                },
            )


def start_backend_server(host: str = "127.0.0.1", port: int = 8000):
    server = ThreadingHTTPServer((host, port), BackendHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.thread = thread
    return server


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), BackendHandler)
    try:
        print("Backend escuchando en http://127.0.0.1:8000")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
