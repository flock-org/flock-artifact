cmake_minimum_required (VERSION 3.0)
project (emp-ot)
set(NAME "emp-ot")

# find_path(CMAKE_FOLDER NAMES cmake/emp-tool-config.cmake)
# include(${CMAKE_FOLDER}/cmake/emp-base.cmake)
include(${CMAKE_SOURCE_DIR}/emp-tool/cmake/emp-base.cmake)

find_package(OpenSSL REQUIRED)
include_directories(${OPENSSL_INCLUDE_DIR})
link_libraries(OpenSSL::Crypto)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../emp-tool/)
link_directories(${CMAKE_CURRENT_SOURCE_DIR}/../emp-tool/build)

# Installation
install(FILES cmake/emp-ot-config.cmake DESTINATION cmake/)
install(DIRECTORY emp-ot DESTINATION include/)

ENABLE_TESTING()
# ADD_SUBDIRECTORY(test)