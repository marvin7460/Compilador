import unittest

from backend import CompilationPipeline


class CompilationPipelineTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = CompilationPipeline()

    def test_lexical_reports_positions(self):
        result = self.pipeline.run("let x: int = 10;", stage="lexical")
        self.assertTrue(result["tokens"])
        self.assertEqual(result["tokens"][0]["line"], 1)
        self.assertEqual(result["tokens"][0]["column"], 1)

    def test_semantic_reports_break_outside_loop(self):
        source = "break;"
        result = self.pipeline.run(source, stage="semantic")
        self.assertTrue(any("break" in d["message"] for d in result["diagnostics"]))

    def test_function_argument_validation(self):
        source = """
        function suma(a: int, b: int): int { return a + b; }
        let x: int = suma(1);
        """
        result = self.pipeline.run(source, stage="compile")
        self.assertTrue(any("esperaba 2 argumentos" in d["message"] for d in result["diagnostics"]))

    def test_compile_generates_global_and_main_flow(self):
        source = """
        let x: int = 1;
        function main(): void { let y: int = 2; }
        """
        result = self.pipeline.run(source, stage="compile")
        self.assertIn("_start:", result["nasm"])
        self.assertIn("call fn_main", result["nasm"])

    def test_var_declaration_without_type_is_valid(self):
        result = self.pipeline.run("var juan = 4;", stage="compile")
        self.assertEqual([], result["diagnostics"])

    def test_var_string_declaration_is_valid(self):
        result = self.pipeline.run('var nombre = "Juan";', stage="compile")
        self.assertEqual([], result["diagnostics"])

    def test_var_reassignment_is_valid(self):
        result = self.pipeline.run("var x = 1; x = 2;", stage="compile")
        self.assertEqual([], result["diagnostics"])

    def test_untyped_function_declaration_and_call(self):
        source = """
        function suma(a, b) { return a + b; }
        var r = suma(2, 3);
        """
        result = self.pipeline.run(source, stage="compile")
        self.assertEqual([], result["diagnostics"])

    def test_untyped_function_wrong_argument_count(self):
        source = """
        function suma(a, b) { return a + b; }
        var r = suma(2);
        """
        result = self.pipeline.run(source, stage="compile")
        self.assertTrue(any("esperaba 2 argumentos" in d["message"] for d in result["diagnostics"]))

    def test_reports_undefined_variable_inside_function(self):
        source = """
        function demo() { return x + 1; }
        var r = demo();
        """
        result = self.pipeline.run(source, stage="semantic")
        self.assertTrue(any("Variable no declarada: x" in d["message"] for d in result["diagnostics"]))

    def test_bubble_sort_program_compiles_without_errors(self):
        source = """
        var a = 5;
        var b = 1;
        var c = 3;

        function bubble3(): void {
            var i = 0;
            while (i < 2) {
                if (a > b) {
                    var t = a;
                    a = b;
                    b = t;
                }
                if (b > c) {
                    var t2 = b;
                    b = c;
                    c = t2;
                }
                i = i + 1;
            }
        }

        bubble3();
        """
        result = self.pipeline.run(source, stage="compile")
        self.assertEqual([], result["diagnostics"])
        self.assertIn("fn_bubble3", result["nasm"])
        self.assertIn("call fn_bubble3", result["nasm"])


if __name__ == "__main__":
    unittest.main()
