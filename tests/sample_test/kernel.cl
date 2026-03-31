__kernel void vector_add(__global const float *A, __global const float *B, __global float *C, int num_elements) {
    int i = get_global_id(0);
    if (i < num_elements) {
        C[i] = A[i] + B[i];
    }
}