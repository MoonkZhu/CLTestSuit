#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>

#ifdef __APPLE__
#include <OpenCL/opencl.h>
#else
#include <CL/cl.h>
#endif

void checkError(cl_int err, const char* operation) {
    if (err != CL_SUCCESS) {
        std::cerr << "Error during operation '" << operation << "': " << err << std::endl;
        exit(1);
    }
}

int main() {
    // 1. Setup OpenCL Platform & Device
    cl_uint num_platforms;
    cl_int err = clGetPlatformIDs(0, nullptr, &num_platforms);
    checkError(err, "clGetPlatformIDs count");

    if (num_platforms == 0) {
        std::cerr << "No OpenCL platforms found." << std::endl;
        return 1;
    }

    std::vector<cl_platform_id> platforms(num_platforms);
    err = clGetPlatformIDs(num_platforms, platforms.data(), nullptr);
    checkError(err, "clGetPlatformIDs");

    cl_platform_id platform = platforms[0];

    cl_uint num_devices;
    err = clGetDeviceIDs(platform, CL_DEVICE_TYPE_ALL, 0, nullptr, &num_devices);
    checkError(err, "clGetDeviceIDs count");

    if (num_devices == 0) {
        std::cerr << "No OpenCL devices found." << std::endl;
        return 1;
    }

    std::vector<cl_device_id> devices(num_devices);
    err = clGetDeviceIDs(platform, CL_DEVICE_TYPE_ALL, num_devices, devices.data(), nullptr);
    checkError(err, "clGetDeviceIDs");

    cl_device_id device = devices[0];

    // 2. Create Context & Command Queue
    cl_context context = clCreateContext(nullptr, 1, &device, nullptr, nullptr, &err);
    checkError(err, "clCreateContext");

    cl_command_queue queue = clCreateCommandQueue(context, device, 0, &err);
    checkError(err, "clCreateCommandQueue");

    // 3. Load & Build Kernel
    std::ifstream kernelFile("kernel.cl");
    if (!kernelFile.is_open()) {
        std::cerr << "Failed to open kernel.cl" << std::endl;
        return 1;
    }

    std::stringstream buffer;
    buffer << kernelFile.rdbuf();
    std::string kernelSource = buffer.str();
    const char* sourcePtr = kernelSource.c_str();
    size_t sourceSize = kernelSource.length();

    cl_program program = clCreateProgramWithSource(context, 1, &sourcePtr, &sourceSize, &err);
    checkError(err, "clCreateProgramWithSource");

    err = clBuildProgram(program, 1, &device, nullptr, nullptr, nullptr);
    if (err != CL_SUCCESS) {
        // [IMPORTANT] Catch OpenCL build errors and print with special prefix
        size_t log_size;
        clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, 0, nullptr, &log_size);
        std::vector<char> build_log(log_size);
        clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, log_size, build_log.data(), nullptr);

        std::cerr << "[KERNEL_BUILD_ERROR]\n" << build_log.data() << std::endl;
        return 1;
    }

    cl_kernel kernel = clCreateKernel(program, "vector_add", &err);
    checkError(err, "clCreateKernel");

    // 4. Setup Data
    const int num_elements = 10;
    std::vector<float> A(num_elements, 1.5f);
    std::vector<float> B(num_elements, 2.5f);
    std::vector<float> C(num_elements, 0.0f);

    size_t buffer_size = sizeof(float) * num_elements;

    cl_mem d_A = clCreateBuffer(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, buffer_size, A.data(), &err);
    checkError(err, "clCreateBuffer A");

    cl_mem d_B = clCreateBuffer(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, buffer_size, B.data(), &err);
    checkError(err, "clCreateBuffer B");

    cl_mem d_C = clCreateBuffer(context, CL_MEM_WRITE_ONLY, buffer_size, nullptr, &err);
    checkError(err, "clCreateBuffer C");

    // 5. Run Kernel
    err = clSetKernelArg(kernel, 0, sizeof(cl_mem), &d_A);
    err |= clSetKernelArg(kernel, 1, sizeof(cl_mem), &d_B);
    err |= clSetKernelArg(kernel, 2, sizeof(cl_mem), &d_C);
    int num_elements_arg = num_elements;
    err |= clSetKernelArg(kernel, 3, sizeof(int), &num_elements_arg);
    checkError(err, "clSetKernelArg");

    size_t global_work_size = num_elements;
    err = clEnqueueNDRangeKernel(queue, kernel, 1, nullptr, &global_work_size, nullptr, 0, nullptr, nullptr);
    checkError(err, "clEnqueueNDRangeKernel");

    // 6. Read Results
    err = clEnqueueReadBuffer(queue, d_C, CL_TRUE, 0, buffer_size, C.data(), 0, nullptr, nullptr);
    checkError(err, "clEnqueueReadBuffer");

    // 7. Output Results
    // The Python runner will automatically parse these floating point numbers
    for (int i = 0; i < num_elements; ++i) {
        std::cout << C[i] << std::endl;
    }

    // 8. Cleanup
    clReleaseMemObject(d_A);
    clReleaseMemObject(d_B);
    clReleaseMemObject(d_C);
    clReleaseKernel(kernel);
    clReleaseProgram(program);
    clReleaseCommandQueue(queue);
    clReleaseContext(context);

    return 0; // Success
}