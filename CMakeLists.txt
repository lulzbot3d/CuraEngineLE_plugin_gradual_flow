cmake_minimum_required(VERSION 3.23)
project(curaenginele_plugin_gradual_flow)
find_package(standardprojectsettings REQUIRED)

find_package(Protobuf REQUIRED)
find_package(spdlog REQUIRED)
find_package(docopt REQUIRED)
find_package(asio-grpc REQUIRED)
find_package(range-v3 REQUIRED)
find_package(clipper REQUIRED)
find_package(ctre REQUIRED)
find_package(semver REQUIRED)
find_package(curaenginele_grpc_definitions REQUIRED)

set(HDRS include/gradual_flow/boost_tags.h
        include/gradual_flow/concepts.h
        include/gradual_flow/gcode_path.h
        include/gradual_flow/point_container.h
        include/gradual_flow/utils.h
        include/plugin/broadcast.h
        include/plugin/cmdline.h
        include/plugin/handshake.h
        include/plugin/metadata.h
        include/plugin/modify.h
        include/plugin/plugin.h
        include/plugin/settings.h)

add_library(curaenginele_plugin_gradual_flow_lib INTERFACE ${HDRS})
use_threads(curaenginele_plugin_gradual_flow_lib)

add_executable(curaenginele_plugin_gradual_flow src/main.cpp)
use_threads(curaenginele_plugin_gradual_flow)

target_include_directories(curaenginele_plugin_gradual_flow_lib
        INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
        )

set(DEPS curaenginele_grpc_definitions::curaenginele_grpc_definitions clipper::clipper ctre::ctre asio-grpc::asio-grpc protobuf::libprotobuf boost::boost spdlog::spdlog docopt_s range-v3::range-v3 semver::semver)

target_link_libraries(curaenginele_plugin_gradual_flow PUBLIC curaenginele_plugin_gradual_flow_lib ${DEPS})

option(ENABLE_TESTS "Build with unit test" ON)

if (ENABLE_TESTS)
        message(STATUS "curaenginele_plugin_gradual_flow: Compiling with Tests")
        enable_testing()
        add_subdirectory(tests)
endif ()