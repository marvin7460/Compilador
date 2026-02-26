import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class TokenType:
    Numero = "Numero"
    Suma = "Suma"
    Resta = "Resta"
    Multiplica = "Multiplica"
    Divide = "Divide"
    Fin = "Fin"
    Invalido = "Invalido"


@dataclass
class Token:
    type: str
    value: str


class Lexer:
    def __init__(self, origen):
        self.origen = origen
        self.index = 0

    def next_token(self):
        while self.index < len(self.origen) and self.origen[self.index].isspace():
            self.index += 1

        if self.index >= len(self.origen):
            return Token(TokenType.Fin, "")

        entrada_actual = self.origen[self.index]
        if entrada_actual.isdigit():
            num = ""
            while self.index < len(self.origen) and self.origen[self.index].isdigit():
                num += self.origen[self.index]
                self.index += 1
            return Token(TokenType.Numero, num)

        self.index += 1
        if entrada_actual == "+":
            return Token(TokenType.Suma, "+")
        if entrada_actual == "-":
            return Token(TokenType.Resta, "-")
        if entrada_actual == "*":
            return Token(TokenType.Multiplica, "*")
        if entrada_actual == "/":
            return Token(TokenType.Divide, "/")
        return Token(TokenType.Invalido, entrada_actual)


class TreeNode:
    def __init__(self, token):
        self.token = token
        self.left = None
        self.right = None

    def to_lines(self, level=0):
        indent = " " * level
        line = f"{indent}{self.token.type}: {self.token.value}"
        lines = [line]
        if self.left:
            lines.extend(self.left.to_lines(level + 2))
        if self.right:
            lines.extend(self.right.to_lines(level + 2))
        return lines


class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.token_actual = lexer.next_token()

    def parse(self):
        node = self.expr()
        if self.token_actual.type != TokenType.Fin:
            raise ValueError(f"Token inesperado: {self.token_actual.value}")
        return node

    def expr(self):
        node = self.termino()
        while self.token_actual.type in (TokenType.Suma, TokenType.Resta):
            token = self.token_actual
            self.eat(token.type)
            new_node = TreeNode(token)
            new_node.left = node
            new_node.right = self.termino()
            node = new_node
        return node

    def termino(self):
        node = self.factor()
        while self.token_actual.type in (TokenType.Multiplica, TokenType.Divide):
            token = self.token_actual
            self.eat(token.type)
            new_node = TreeNode(token)
            new_node.left = node
            new_node.right = self.factor()
            node = new_node
        return node

    def factor(self):
        token = self.token_actual
        if token.type == TokenType.Numero:
            self.eat(TokenType.Numero)
            return TreeNode(token)
        if token.type == TokenType.Invalido:
            raise ValueError(f"Token inválido: {token.value}")
        raise ValueError(f"Se esperaba número y se recibió: {token.value}")

    def eat(self, token_type):
        if self.token_actual.type == token_type:
            self.token_actual = self.lexer.next_token()
            return
        raise ValueError(
            f"Se esperaba token {token_type} y se recibió {self.token_actual.type}"
        )


def parse_expression(expression: str) -> str:
    lexer = Lexer(expression)
    parser = Parser(lexer)
    tree = parser.parse()
    return "\n".join(tree.to_lines())


class BackendHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_POST(self):
        if self.path != "/api/sintactico":
            self._send_json(404, {"error": "Ruta no encontrada"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
            expression = str(payload.get("expression", "")).strip()
            if not expression:
                self._send_json(400, {"error": "La expresión está vacía"})
                return
            tree = parse_expression(expression)
            self._send_json(200, {"tree": tree})
        except json.JSONDecodeError:
            self._send_json(400, {"error": "JSON inválido"})
        except ValueError as e:
            self._send_json(400, {"error": str(e)})


def start_backend_server(host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), BackendHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.thread = thread
    return server
