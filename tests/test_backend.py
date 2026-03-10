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

    def test_var_declaration_without_explicit_type_is_valid(self):
        result = self.pipeline.run("var juan = 4;", stage="compile")
        self.assertFalse(result["diagnostics"], "var juan = 4; debe compilar sin errores")

    def test_var_string_and_reassignment(self):
        source = 'var nombre = "Juan"; var x = 1; x = 2;'
        result = self.pipeline.run(source, stage="compile")
        self.assertFalse(result["diagnostics"])

    def test_untyped_function_declaration_and_call(self):
        source = """
        function suma(a, b) { return a + b; }
        var r = suma(2, 3);
        """
        result = self.pipeline.run(source, stage="compile")
        self.assertFalse(result["diagnostics"])

    def test_function_arity_error_for_untyped_signature(self):
        source = """
        function suma(a, b) { return a + b; }
        var r = suma(2);
        """
        result = self.pipeline.run(source, stage="semantic")
        self.assertTrue(any("esperaba 2 argumentos" in d["message"] for d in result["diagnostics"]))

    def test_undeclared_variable_inside_function(self):
        source = """
        function test() {
            return z + 1;
        }
        """
        result = self.pipeline.run(source, stage="semantic")
        self.assertTrue(any("Variable no declarada: z" in d["message"] for d in result["diagnostics"]))

    def test_bubble_sort_like_flow_runs_without_semantic_errors(self):
        source = """
        var a = 3;
        var b = 1;
        var c = 2;
        var i = 0;
        while (i < 2) {
            if (a > b) { var t1 = a; a = b; b = t1; }
            if (b > c) { var t2 = b; b = c; c = t2; }
            i = i + 1;
        }
        """
        result = self.pipeline.run(source, stage="semantic")
        self.assertFalse(result["diagnostics"])

    def test_console_log_tokenizes_and_executes(self):
        source = 'console.log("hola");'
        lexical = self.pipeline.run(source, stage="lexical")
        lexemes = [t["lexeme"] for t in lexical["tokens"]]
        self.assertIn(".", lexemes)
        self.assertIn("console", lexemes)
        self.assertIn("log", lexemes)

        compiled = self.pipeline.run(source, stage="compile")
        self.assertFalse(compiled["diagnostics"])
        self.assertEqual(compiled["execution"], ["hola"])

    def test_array_loop_execution_with_inferred_types(self):
        source = """
        var nums = [1, 2, 3];
        var total = 0;
        for (var i = 0; i < nums.length; i = i + 1) {
            total = total + nums[i];
        }
        console.log(total);
        """
        result = self.pipeline.run(source, stage="compile")
        self.assertFalse(result["diagnostics"])
        self.assertEqual(result["execution"], ["6"])

    def test_array_typing_with_ts_number_annotation(self):
        source = """
        let nums: number[] = [1, 2, 3];
        let first: number = nums[0];
        """
        result = self.pipeline.run(source, stage="semantic")
        self.assertFalse(result["diagnostics"])


if __name__ == "__main__":
    unittest.main()
