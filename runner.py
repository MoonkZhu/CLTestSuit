import os
import sys
import subprocess
import time
import csv
import re

# Global Epsilon for floating-point comparisons
EPSILON = 1e-5

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

def run_test(test_dir, test_name):
    # Determine test type and paths
    run_script = os.path.join(test_dir, 'run.sh')
    env_file = os.path.join(test_dir, 'env.txt')

    # Custom Script Case
    if os.path.exists(run_script):
        cmd = ["bash", "run.sh"]
        test_type = "Script"
        # Script tests run in source directory
        working_dir = test_dir
        has_golden = os.path.exists(os.path.join(test_dir, 'expected.txt'))
    else:
        cmd = ["./test_bin"]
        test_type = "Standard"
        # Standard tests run in build directory
        working_dir = os.path.join('build', 'tests', test_name)
        has_golden = os.path.exists(os.path.join(working_dir, 'expected.txt'))
        output_bin = os.path.join(working_dir, 'test_bin')

        if not os.path.exists(output_bin):
            return False, 0.0, f"Executable 'test_bin' not found in {working_dir}.", test_type, "No"

    # Environment Variables configuration
    run_env = os.environ.copy()
    has_env_flag = "No"

    if os.path.exists(env_file):
        has_env_flag = "Yes"
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, val = line.split('=', 1)
                        run_env[key.strip()] = val.strip()
        except Exception as e:
            return False, 0.0, f"Failed to parse env.txt: {str(e)}", test_type, has_env_flag

    start_time = time.time()

    try:
        result = subprocess.run(cmd,
                                cwd=working_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=run_env,
                                text=True)

        exec_time = time.time() - start_time

        # Check for OpenCL compilation errors logged by the C++ host
        if "[KERNEL_BUILD_ERROR]" in result.stderr:
            return False, exec_time, "OpenCL Kernel Build Error.", test_type, has_env_flag

        # Check execution success (exit code)
        if result.returncode != 0:
            return False, exec_time, f"Execution failed (exit code {result.returncode}).", test_type, has_env_flag

        if has_golden:
            # Verify Golden
            golden_path = os.path.join(working_dir, 'expected.txt')
            with open(golden_path, 'r') as f:
                golden_text = f.read()

            match, msg = compare_golden(result.stdout, golden_text)
            if not match:
                return False, exec_time, f"Verification failed: {msg}", test_type, has_env_flag
        else:
            # Host-Verified Mode
            output_lower = result.stdout.lower() + result.stderr.lower()
            if "fail" in output_lower or "mismatch" in output_lower:
                return False, exec_time, "Verification failed (Host reported failure).", test_type, has_env_flag

            if "pass" not in output_lower:
                return False, exec_time, "Verification failed (Host did not report 'PASS').", test_type, has_env_flag

        return True, exec_time, "", test_type, has_env_flag

    except Exception as e:
        return False, time.time() - start_time, f"Failed to execute test: {str(e)}", test_type, has_env_flag

def main():
    tests_dir = 'tests'

    if not os.path.exists(tests_dir):
        print(f"Directory {tests_dir} does not exist.")
        sys.exit(1)

    test_cases = []
    for item in os.listdir(tests_dir):
        test_path = os.path.join(tests_dir, item)
        if os.path.isdir(test_path):
            test_cases.append((item, test_path))

    if not test_cases:
        print(f"No test cases found in {tests_dir}.")
        sys.exit(0)

    print(f"Found {len(test_cases)} test case(s) in {tests_dir}.")
    print("=" * 60)

    results = []
    passed_count = 0

    for test_name, test_dir in test_cases:
        success, exec_time, err_msg, test_type, has_env = run_test(test_dir, test_name)

        status = "PASS" if success else "FAIL"
        results.append({
            "Test Name": test_name,
            "Execution Time (s)": f"{exec_time:.4f}",
            "Result": status,
            "Type": test_type,
            "Has Env": has_env
        })

        if success:
            print(f"Test '{test_name}' ({test_type}): [{status}] in {exec_time:.4f}s")
            passed_count += 1
        else:
            print(f"Test '{test_name}' ({test_type}): [{status}] in {exec_time:.4f}s - {err_msg}")

    print("=" * 60)
    print(f"Summary: {passed_count}/{len(test_cases)} tests passed.")

    # Write to CSV
    csv_file = 'results.csv'
    with open(csv_file, 'w', newline='') as csvfile:
        fieldnames = ['Test Name', 'Execution Time (s)', 'Result', 'Type', 'Has Env']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Results saved to {csv_file}")

    if passed_count != len(test_cases):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()