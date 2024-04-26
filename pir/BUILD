package(default_visibility = ["//visibility:public"])

load("@rules_cc//cc:defs.bzl", "cc_library")

licenses(["notice"]) # MIT license

cc_library(
    name = "json",
    hdrs = ["single_include/nlohmann/json.hpp"],
    strip_include_prefix = "single_include/",
)

cc_library(
    name = "base64_utils",
    srcs = ["base64_utils.cc"],
    hdrs = ["base64_utils.h"],
)

cc_binary(
    name = "dense_run_bin",
    srcs = ["dense_run.cc"],
    deps = [
        "@google_dpf//pir:pir_client",
        "@google_dpf//pir:pir_server",
        "@google_dpf//pir:private_information_retrieval_cc_proto",
        "@google_dpf//pir:dense_dpf_pir_database",
        "@google_dpf//pir:dense_dpf_pir_client",
        "@google_dpf//pir:dense_dpf_pir_server",
        "@google_dpf//pir/testing:request_generator",
        "@google_dpf//pir/testing:mock_pir_database",
        ":base64_utils"
    ],
    testonly = True
)

cc_binary(
    name = "client_gen_pir_requests_bin",
    srcs = ["client_gen_pir_requests.cc"],
    deps = [
        "@google_dpf//pir:pir_client",
        "@google_dpf//pir:pir_server",
        "@google_dpf//pir:private_information_retrieval_cc_proto",
        "@google_dpf//pir:dense_dpf_pir_database",
        "@google_dpf//pir:dense_dpf_pir_client",
        "@google_dpf//pir:dense_dpf_pir_server",
        "@google_dpf//pir/testing:request_generator",
        "@google_dpf//pir/testing:mock_pir_database",
        "@com_github_nlohmann_json//:json",
        ":base64_utils"
    ],
    testonly = True
)

cc_binary(
    name = "client_handle_pir_responses_bin",
    srcs = ["client_handle_pir_responses.cc"],
    deps = [
        "@google_dpf//pir:pir_client",
        "@google_dpf//pir:pir_server",
        "@google_dpf//pir:private_information_retrieval_cc_proto",
        "@google_dpf//pir:dense_dpf_pir_database",
        "@google_dpf//pir:dense_dpf_pir_client",
        "@google_dpf//pir:dense_dpf_pir_server",
        "@google_dpf//pir/testing:request_generator",
        "@google_dpf//pir/testing:mock_pir_database",
        "@com_github_nlohmann_json//:json",
        ":base64_utils",
    ],
    testonly = True
)

cc_binary(
    name = "server_handle_pir_requests_bin",
    srcs = ["server_handle_pir_requests.cc"],
    deps = [
        "@google_dpf//pir:pir_client",
        "@google_dpf//pir:pir_server",
        "@google_dpf//pir:private_information_retrieval_cc_proto",
        "@google_dpf//pir:dense_dpf_pir_database",
        "@google_dpf//pir:dense_dpf_pir_client",
        "@google_dpf//pir:dense_dpf_pir_server",
        "@google_dpf//pir/testing:request_generator",
        "@google_dpf//pir/testing:mock_pir_database",
        "@com_github_nlohmann_json//:json",
        ":base64_utils",
    ],
    testonly = True
)