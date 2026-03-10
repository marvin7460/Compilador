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


if __name__ == "__main__":
    unittest.main()
