cmake_minimum_required (VERSION 2.8.11)
project (emp-agmpc)
set(NAME "emp-agmpc")

# find_path(CMAKE_FOLDER NAMES cmake/emp-tool-config.cmake)
# include(${CMAKE_FOLDER}/cmake/emp-base.cmake)
include(${CMAKE_SOURCE_DIR}/emp-tool/cmake/emp-base.cmake)

# FIND_PACKAGE(emp-ot REQUIRED)
# INCLUDE_DIRECTORIES(${EMP-OT_INCLUDE_DIRS})

find_package(OpenSSL REQUIRED)
include_directories(${OPENSSL_INCLUDE_DIR})
link_libraries(OpenSSL::Crypto)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../emp-tool/)
link_directories(${CMAKE_CURRENT_SOURCE_DIR}/../emp-tool/build)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../emp-ot/)

install(FILES cmake/emp-agmpc-config.cmake DESTINATION cmake/)
install(DIRECTORY emp-agmpc DESTINATION include/)

ENABLE_TESTING()
# ADD_SUBDIRECTORY(test)