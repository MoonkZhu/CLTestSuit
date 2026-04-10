# CLTestSuit

## OpenCL Test Suite Rules

Adding a new test case to this framework is designed to be extremely simple. Just follow these rules:

### 1. Directory Structure
Every test case must live in its own subdirectory inside the `tests/` folder. The name of the directory will automatically be used as the name of the test.
Example: `tests/my_new_test/`

### 2. Required Files
The Python runner automatically discovers your test files based on the following conventions. Each test directory must contain exactly:
1. **C++ Host Source Code (`.cpp` files)**: You must have at least one `.cpp` file. If your test requires multiple `.cpp` files, one of them *must* be named `main.cpp`.
2. **OpenCL Kernel File (`.cl` file)**: You must provide exactly *one* `.cl` file. The runner will throw an error if multiple kernel files are found in a single test directory.
3. **Golden Reference File (`expected.txt`)**: *(Optional)* A text file containing the expected numerical output.

### 3. Verification Modes
The runner supports two modes of output verification depending on whether `expected.txt` is present.

#### Mode A: Golden File Verification (Default)
If you include an `expected.txt` file in your test directory, the runner will use it.
- **Output Format**: Print your numerical results to `stdout` (e.g., `std::cout << result << std::endl;`). The Python runner will extract all numbers from your output and compare them against `expected.txt` using a global floating-point tolerance (epsilon = `1e-5`).

#### Mode B: Host-Verified Verification
If you omit `expected.txt`, the runner relies on your C++ code to verify the results.
- **Output Format**: Your C++ code must perform the array comparison internally. It must print the word `PASS` to stdout if the test succeeds. If the test fails, it should print `FAIL` or `mismatch`. The runner will scan the output for these keywords (case-insensitive).

### 4. Writing the C++ Host Code
- **Success/Failure (CRITICAL)**: Regardless of the verification mode, your C++ program **MUST return `0` on success and a non-zero exit code on failure**. The Python runner heavily relies on the exit code to determine if the test passed or failed (alongside other output checks).
- **OpenCL Build Errors**: If your `clBuildProgram` fails at runtime, you MUST catch it and print the OpenCL build log to `stderr` with the prefix `[KERNEL_BUILD_ERROR]`. The Python runner will look for this prefix to identify compilation failures vs. execution failures.
  Example:
  ```cpp
  std::cerr << "[KERNEL_BUILD_ERROR]\n" << build_log << std::endl;
  return 1;
  ```

### 5. Building the Tests
The test cases are managed by a CMake auto-build system. Before running the tests, you must compile them.

From the root directory, create a build directory and run CMake:
```bash
mkdir build
cd build
cmake ..
make
cd ..
```
The CMake configuration automatically scans the `tests/` directory and creates executable targets for each test, placing a `test_bin` executable in the respective test directory.

### 6. Running the Tests
From the root directory, simply run:
```bash
python runner.py
```

The runner will automatically:
1. Discover your test in the `tests/` folder and name it based on the directory.
2. Validate the directory structure (e.g. exactly one `.cl` file, presence of `expected.txt`).
3. Ensure the test executable `test_bin` has been built.
4. Run the binary.
5. Verify the output using either the Golden File or Host-Verified mode.
6. Provide a clean `[PASS]` or `[FAIL]` summary in the terminal.
7. Save the test results (including execution time) to `results.csv`.