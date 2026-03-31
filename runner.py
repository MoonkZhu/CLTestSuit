import os
import sys
import json
import subprocess
import argparse
import re

# Global Epsilon for floating-point comparisons
EPSILON = 1e-5

def setup_directories():
    os.makedirs('logs/build', exist_ok=True)
    os.makedirs('logs/run', exist_ok=True)

def find_tests(tests_dir='tests'):
    if not os.path.exists(tests_dir):
        return []

    test_cases = []
    for item in os.listdir(tests_dir):
        test_path = os.path.join(tests_dir, item)
        if os.path.isdir(test_path):
            manifest_path = os.path.join(test_path, 'manifest.json')
            if os.path.exists(manifest_path):
                test_cases.append(test_path)
    return test_cases

def extract_numbers(text):
    # Extracts all integers and floating-point numbers from a string
    return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', text)]

def compare_golden(output_text, golden_text):
    output_nums = extract_numbers(output_text)
    golden_nums = extract_numbers(golden_text)

    if len(output_nums) != len(golden_nums):
        return False, f"Count mismatch: Expected {len(golden_nums)} numbers, got {len(output_nums)}."

    for i, (out_val, gold_val) in enumerate(zip(output_nums, golden_nums)):
        if abs(out_val - gold_val) > EPSILON:
            return False, f"Mismatch at index {i}: Expected {gold_val}, got {out_val} (diff: {abs(out_val - gold_val)})"

    return True, ""

def build_test(test_dir, manifest, test_name):
    # Extract build config
    host_sources = manifest.get('host_sources', [])
    compiler_flags = manifest.get('compiler_flags', [])

    # Resolve absolute paths
    src_paths = [os.path.join(test_dir, src) for src in host_sources]
    output_bin = os.path.join(test_dir, 'test_bin')

    # Construct compiler command
    # Prefer clang++, fallback to g++ if needed, but let's just use g++ as standard default if not specified
    compiler = os.environ.get('CXX', 'g++')

    cmd = [compiler] + src_paths + ['-o', output_bin] + compiler_flags

    build_log_path = os.path.join('logs', 'build', f'{test_name}_build.log')

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        with open(build_log_path, 'w') as f:
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(result.stdout)

        if result.returncode != 0:
            return False, output_bin, f"Compilation failed (exit code {result.returncode}). See {build_log_path}"

        return True, output_bin, ""
    except Exception as e:
        return False, output_bin, f"Failed to run compiler: {str(e)}"

def run_test(test_dir, manifest, test_name, output_bin):
    run_log_path = os.path.join('logs', 'run', f'{test_name}_run.log')

    try:
        # Run binary in the test directory so it can find local kernels
        result = subprocess.run([f"./{os.path.basename(output_bin)}"],
                                cwd=test_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)

        with open(run_log_path, 'w') as f:
            f.write("--- STDOUT ---\n")
            f.write(result.stdout)
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)

        # Check for OpenCL compilation errors logged by the C++ host
        if "[KERNEL_BUILD_ERROR]" in result.stderr:
            return False, f"OpenCL Kernel Build Error. See {run_log_path}"

        # Check execution success
        if result.returncode != 0:
            return False, f"Execution failed (exit code {result.returncode}). See {run_log_path}"

        # Verify Golden
        golden_file = manifest.get('golden_file')
        if golden_file:
            golden_path = os.path.join(test_dir, golden_file)
            if not os.path.exists(golden_path):
                return False, f"Golden file '{golden_file}' not found."

            with open(golden_path, 'r') as f:
                golden_text = f.read()

            match, msg = compare_golden(result.stdout, golden_text)
            if not match:
                return False, f"Verification failed: {msg}"

        return True, ""

    except Exception as e:
        return False, f"Failed to execute binary: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="OpenCL Test Suite Runner")
    parser.add_argument("--keep-binaries", action="store_true", help="Do not delete compiled binaries after testing")
    args = parser.parse_args()

    setup_directories()

    test_cases = find_tests()
    if not test_cases:
        print("No test cases found in tests/ directory.")
        return

    print(f"Found {len(test_cases)} test case(s).")
    print("=" * 40)

    passed_count = 0

    for test_dir in test_cases:
        test_name = os.path.basename(test_dir)
        manifest_path = os.path.join(test_dir, 'manifest.json')

        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"Test {test_name}: [FAIL] - Invalid manifest.json: {e}")
            continue

        display_name = manifest.get('name', test_name)

        # 1. Build
        build_ok, output_bin, build_err = build_test(test_dir, manifest, test_name)
        if not build_ok:
            print(f"Test '{display_name}': [FAIL] - {build_err}")
            continue

        # 2. Run & Verify
        run_ok, run_err = run_test(test_dir, manifest, test_name, output_bin)

        # 3. Cleanup
        if not args.keep_binaries and os.path.exists(output_bin):
            os.remove(output_bin)

        # 4. Report
        if run_ok:
            print(f"Test '{display_name}': [PASS]")
            passed_count += 1
        else:
            print(f"Test '{display_name}': [FAIL] - {run_err}")

    print("=" * 40)
    print(f"Summary: {passed_count}/{len(test_cases)} tests passed.")

    if passed_count != len(test_cases):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
