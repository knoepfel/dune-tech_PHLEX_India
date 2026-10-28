cmake_minimum_required(VERSION 3.31)

# Compile for the GPU(s) on this machine unless told otherwise, for example
#   cmake -DCMAKE_CUDA_ARCHITECTURES="80;90" ...
# 'native' needs a GPU visible when you run cmake. Must be set before project().
if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
  set(CMAKE_CUDA_ARCHITECTURES native)
endif()

project(phlex_gpu_hello VERSION 0.0.1 LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 23) # the Phlex plugins
set(CMAKE_CUDA_STANDARD 17) # the .cu file; nvcc never sees a Phlex header

find_package(Boost REQUIRED json)
find_package(TBB REQUIRED)
find_package(spdlog REQUIRED)
find_package(phlex REQUIRED)
find_package(CUDAToolkit REQUIRED)

# The same strict warnings as phlex-examples, for C++ only: nvcc rejects -Wpedantic and the
# -Wno-* flags, so every option is wrapped in a COMPILE_LANGUAGE:CXX generator expression.
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  if(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "14.1")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "15")
      add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wno-stringop-overflow>)
    endif()
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "16")
      add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wno-array-bounds>)
    endif()
  endif()
endif()
add_compile_options("$<$<COMPILE_LANGUAGE:CXX>:-Wall;-Wpedantic;-Werror>")

# Framework-agnostic experiment library, written in CUDA (like my_add, but on a GPU).
# N.B. The library type should be SHARED.
add_library(my_gpu_hello SHARED my_gpu_hello.cu)
# Link the shared CUDA runtime, and record where it is (RUNPATH): CMake counts the CUDA library
# directory as one of nvcc's own, so it would leave it out, and neither the linker nor phlex
# could then find libcudart.so when a program or plugin uses this library.
set_target_properties(my_gpu_hello PROPERTIES CUDA_RUNTIME_LIBRARY Shared BUILD_RPATH "${CUDAToolkit_LIBRARY_DIR}")
target_link_libraries(my_gpu_hello PRIVATE CUDA::cudart)

# The same library without Phlex: a plain program
add_executable(hello_standalone hello_standalone.cpp)
target_link_libraries(hello_standalone PRIVATE my_gpu_hello)

# Phlex plugins (MODULE libraries, loaded by phlex at run time)
add_library(n_threads_source MODULE n_threads_source.cpp)
target_link_libraries(n_threads_source PRIVATE phlex::module)

add_library(gpu_hello_and_verify MODULE gpu_hello_and_verify.cpp)
target_link_libraries(gpu_hello_and_verify PRIVATE phlex::module my_gpu_hello)
# Keep assert() active in a Release build: the observer checks with assert
target_compile_options(gpu_hello_and_verify PRIVATE -UNDEBUG)
