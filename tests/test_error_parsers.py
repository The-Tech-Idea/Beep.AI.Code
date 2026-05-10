"""Tests for error parsers."""

from __future__ import annotations

import pytest

from beep.errors.parsers.python import parse_python_errors
from beep.errors.parsers.csharp import parse_csharp_errors
from beep.errors.parsers.javascript import parse_javascript_errors
from beep.errors.parsers.typescript import parse_typescript_errors
from beep.errors.parsers.java import parse_java_errors
from beep.errors.parsers.go import parse_go_errors
from beep.errors.parsers.rust import parse_rust_errors
from beep.errors.parsers.ruby import parse_ruby_errors
from beep.errors.parsers.ccpp import parse_ccpp_errors
from beep.errors.parsers.php import parse_php_errors
from beep.errors.parsers import ParsedError
from beep.errors.classifier import classify_error, _try_language_parsers
from beep.errors.models import ErrorCategory


class TestPythonErrorParser:
    def test_traceback_error(self):
        text = """Traceback (most recent call last):
  File "/app/main.py", line 10, in <module>
    result = divide(10, 0)
  File "/app/utils.py", line 5, in divide
    return a / b
ZeroDivisionError: division by zero"""
        results = parse_python_errors(text)
        assert len(results) >= 1
        assert any(r.file and "main.py" in r.file for r in results)
        assert any(r.line == 10 for r in results)

    def test_syntax_error(self):
        text = """  File "test.py", line 3
    def foo(
           ^
SyntaxError: invalid syntax"""
        results = parse_python_errors(text)
        assert len(results) >= 1
        assert any(r.code == "SyntaxError" for r in results)

    def test_import_error(self):
        text = """Traceback (most recent call last):
  File "app.py", line 1, in <module>
    import nonexistent
ModuleNotFoundError: No module named 'nonexistent'"""
        results = parse_python_errors(text)
        assert len(results) >= 1
        assert any(r.code == "ModuleNotFoundError" for r in results)

    def test_no_errors(self):
        text = "All tests passed."
        results = parse_python_errors(text)
        assert len(results) == 0

    def test_deduplication(self):
        text = """Traceback (most recent call last):
  File "app.py", line 5, in <module>
    foo()
  File "app.py", line 5, in <module>
    foo()
ValueError: test"""
        results = parse_python_errors(text)
        files_lines = [(r.file, r.line) for r in results]
        assert len(files_lines) == len(set(files_lines))


class TestCSharpErrorParser:
    def test_compiler_error(self):
        text = """Program.cs(10,20): error CS0103: The name 'foo' does not exist in the current context"""
        results = parse_csharp_errors(text)
        assert len(results) >= 1
        assert results[0].file == "Program.cs"
        assert results[0].line == 10
        assert results[0].column == 20
        assert results[0].code == "CS0103"

    def test_warning(self):
        text = """Utils.cs(25,13): warning CS0219: The variable 'x' is assigned but its value is never used"""
        results = parse_csharp_errors(text)
        assert len(results) >= 1
        assert results[0].code == "CS0219"

    def test_no_errors(self):
        text = "Build succeeded."
        results = parse_csharp_errors(text)
        assert len(results) == 0


class TestJavaScriptErrorParser:
    def test_reference_error(self):
        text = """ReferenceError: foo is not defined
    at Object.<anonymous> (/app/index.js:5:1)"""
        results = parse_javascript_errors(text)
        assert len(results) >= 1
        assert any(r.file and "index.js" in r.file for r in results)

    def test_syntax_error(self):
        text = """SyntaxError: Unexpected token '}'
    at Module._compile (internal/modules/cjs/loader.js:100:1)"""
        results = parse_javascript_errors(text)
        assert len(results) >= 1

    def test_type_error(self):
        text = """TypeError: Cannot read property 'name' of undefined
    at process (/app/utils.js:15:10)"""
        results = parse_javascript_errors(text)
        assert len(results) >= 1

    def test_npm_error(self):
        text = "npm ERR! code ERESOLVE\nnpm ERR! ERESOLVE unable to resolve dependency tree"
        results = parse_javascript_errors(text)
        assert len(results) >= 1
        assert any(r.code == "NPM" for r in results)

    def test_no_errors(self):
        text = "All tests passed."
        results = parse_javascript_errors(text)
        assert len(results) == 0


class TestTypeErrorParser:
    def test_tsc_error(self):
        text = """src/main.ts(10,5): error TS2304: Cannot find name 'foo'."""
        results = parse_typescript_errors(text)
        assert len(results) >= 1
        assert results[0].file == "src/main.ts"
        assert results[0].line == 10
        assert results[0].code == "TS2304"

    def test_module_not_found(self):
        text = """src/app.ts(1,23): error TS2307: Cannot find module '@scope/pkg'."""
        results = parse_typescript_errors(text)
        assert len(results) >= 1
        assert results[0].code == "TS2307"

    def test_property_not_exist(self):
        text = """src/component.tsx(15,10): error TS2339: Property 'foo' does not exist on type 'Bar'."""
        results = parse_typescript_errors(text)
        assert len(results) >= 1

    def test_no_errors(self):
        text = "No errors found."
        results = parse_typescript_errors(text)
        assert len(results) == 0


class TestJavaErrorParser:
    def test_compile_error(self):
        text = """Error: Unable to initialize main class Main
Caused by: java.lang.NoClassDefFoundError: Main (wrong name: example/Main)"""
        results = parse_java_errors(text)
        assert len(results) == 0

    def test_javac_error(self):
        text = """Main.java:10: error: cannot find symbol
        System.ouprintln("hello");
              ^
  symbol:   method ouprintln(String)
  location: variable out of type PrintStream"""
        results = parse_java_errors(text)
        assert len(results) >= 1
        assert results[0].file == "Main.java"
        assert results[0].line == 10

    def test_stack_trace(self):
        text = """Exception in thread "main" java.lang.NullPointerException
    at com.example.MyClass.doSomething(MyClass.java:42)
    at com.example.MyClass.main(MyClass.java:10)"""
        results = parse_java_errors(text)
        files = [r.file for r in results if r.file]
        assert any("MyClass.java" in f for f in files)


class TestGoErrorParser:
    def test_compile_error(self):
        text = """# example.com/mypackage
./main.go:15:5: undefined: foobar"""
        results = parse_go_errors(text)
        assert len(results) >= 1
        assert results[0].file == "./main.go"
        assert results[0].line == 15

    def test_test_failure(self):
        text = """--- FAIL: TestSomething (0.00s)
    /path/to/test/main_test.go:25: expected 42, got 0"""
        results = parse_go_errors(text)
        assert len(results) >= 1

    def test_no_errors(self):
        text = """?    example.com/mypackage    [no test files]"""
        results = parse_go_errors(text)
        assert len(results) == 0


class TestRustErrorParser:
    def test_compile_error(self):
        text = """error[E0425]: cannot find value `foo` in this scope
  --> src/main.rs:10:5
   |
10 |     foo
   |     ^^^ not found in this scope"""
        results = parse_rust_errors(text)
        assert len(results) >= 1
        assert any(r.file == "src/main.rs" for r in results)

    def test_test_failure(self):
        text = """running 1 test
test tests::it_works ... FAILED

failures:

---- tests::it_works stdout ----
thread 'tests::it_works' panicked at src/lib.rs:5:5:
assertion failed"""
        results = parse_rust_errors(text)
        assert len(results) >= 1

    def test_no_errors(self):
        text = """Compiling myproject v0.1.0
    Finished dev [unoptimized + debuginfo] target(s) in 2.50s"""
        results = parse_rust_errors(text)
        assert len(results) == 0


class TestRubyErrorParser:
    def test_syntax_error(self):
        text = """SyntaxError: /path/to/app.rb:10: syntax error, unexpected end-of-input
    def hello
             ^"""
        results = parse_ruby_errors(text)
        assert len(results) >= 1
        assert any("app.rb" in (r.file or "") for r in results)

    def test_runtime_error(self):
        text = """NoMethodError: undefined method `foo' for nil:NilClass
    from /path/to/app.rb:15:in `do_something'
    from /path/to/app.rb:5:in `<main>'"""
        results = parse_ruby_errors(text)
        assert len(results) >= 1

    def test_rspec_failure(self):
        text = """Failures:

  1) MyClass does something
     Failure/Error: expect(result).to eq(42)

       expected: 42
            got: 0
     # ./spec/my_class_spec.rb:10:in `block (2 levels) in <top (required)>'"""
        results = parse_ruby_errors(text)
        assert len(results) >= 1
        assert any("my_class_spec.rb" in (r.file or "") for r in results)


class TestCCppErrorParser:
    def test_gcc_error(self):
        text = """main.c:10:5: error: unknown type name 'foo_t'
   10 |     foo_t x;
      |     ^~~~~"""
        results = parse_ccpp_errors(text)
        assert len(results) >= 1
        assert results[0].file == "main.c"
        assert results[0].line == 10

    def test_clang_error(self):
        text = """src/utils.cpp:25:10: fatal error: 'nonexistent.h' file not found
#include "nonexistent.h"
         ^~~~~~~~~~~~~~~
1 error generated."""
        results = parse_ccpp_errors(text)
        assert len(results) >= 1
        assert results[0].file == "src/utils.cpp"
        assert results[0].line == 25

    def test_warning(self):
        text = """main.c:15:9: warning: unused variable 'x' [-Wunused-variable]
    int x = 0;
        ^"""
        results = parse_ccpp_errors(text)
        assert len(results) >= 1

    def test_no_errors(self):
        text = """gcc -o myprogram main.c
[100%] Built target myprogram"""
        results = parse_ccpp_errors(text)
        assert len(results) == 0


class TestPHPErrorParser:
    def test_parse_error(self):
        text = (
            """Parse error: syntax error, unexpected end of file in /var/www/index.php on line 25"""
        )
        results = parse_php_errors(text)
        assert len(results) >= 1
        assert any("index.php" in (r.file or "") for r in results)

    def test_fatal_error(self):
        text = """Fatal error: Uncaught Error: Call to undefined function foo() in /var/www/app.php:10
Stack trace:
#0 /var/www/index.php(5): require()
#1 {main}
  thrown in /var/www/app.php on line 10"""
        results = parse_php_errors(text)
        assert len(results) >= 1
        assert any("app.php" in (r.file or "") for r in results)

    def test_phpunit_failure(self):
        text = """There was 1 failure:

1) App\Tests\MyTest::testSomething
Failed asserting that 0 matches expected 42.

/var/www/tests/MyTest.php:15"""
        results = parse_php_errors(text)
        assert len(results) >= 1

    def test_no_errors(self):
        text = """OK (5 tests, 10 assertions)"""
        results = parse_php_errors(text)
        assert len(results) == 0


class TestErrorClassifierIntegration:
    def test_classify_java_error(self):
        error_text = """Main.java:10: error: cannot find symbol
        System.ouprintln("hello");"""
        error = classify_error("shell", error_text, command="mvn compile")
        assert error.error_type == ErrorCategory.BUILD_ERROR

    def test_classify_go_error(self):
        error_text = """./main.go:15:5: undefined: foobar"""
        error = classify_error("shell", error_text, command="go build")
        assert error.error_type == ErrorCategory.BUILD_ERROR

    def test_classify_rust_error(self):
        error_text = """error[E0425]: cannot find value `foo` in this scope
  --> src/main.rs:10:5"""
        error = classify_error("shell", error_text, command="cargo build")
        assert error.error_type == ErrorCategory.BUILD_ERROR

    def test_classify_ccpp_error(self):
        error_text = """main.c:10:5: error: unknown type name 'foo_t'"""
        error = classify_error("shell", error_text, command="make")
        assert error.error_type == ErrorCategory.BUILD_ERROR

    def test_classify_php_error(self):
        error_text = (
            """Parse error: syntax error, unexpected end of file in /var/www/index.php on line 25"""
        )
        error = classify_error("shell", error_text)
        assert error.error_type == ErrorCategory.SYNTAX_ERROR

    def test_try_language_parsers_priority(self):
        text = """./main.go:15:5: undefined: foobar"""
        results = _try_language_parsers(text)
        assert len(results) >= 1

    def test_test_failure_detection(self):
        error_text = """FAIL: TestSomething (0.00s)
    /path/to/test/main_test.go:25: expected 42, got 0"""
        error = classify_error("shell", error_text, command="go test")
        assert error.error_type == ErrorCategory.TEST_FAILURE
