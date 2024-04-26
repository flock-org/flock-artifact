#include "external/google_dpf/pir/private_information_retrieval.pb.h"
#include "external/google_dpf/pir/prng/aes_128_ctr_seeded_prng.h"
#include "external/google_dpf/pir/testing/request_generator.h"
#include "external/google_dpf/pir/testing/mock_pir_database.h"
#include "external/google_dpf/pir/dense_dpf_pir_database.h"
#include "external/google_dpf/pir/dense_dpf_pir_client.h"
#include "external/google_dpf/pir/dense_dpf_pir_server.h"

#include <memory>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
#include <iostream>
#include <algorithm>

namespace distributed_point_functions {

using Database = DenseDpfPirServer::Database;
using ::testing::Contains;
using ::testing::StartsWith;

constexpr int kTestDatabaseElements = 1234;
constexpr int kBitsPerBlock = 128;

PirConfig config_;
std::unique_ptr<DenseDpfPirServer> server_;
std::unique_ptr<Database> database_;
std::vector<std::string> content_;
std::vector<absl::string_view> content_views_;
std::unique_ptr<DistributedPointFunction> dpf_;
DpfParameters params_;
std::vector<std::string> elements_;

void SetUpConfig() {
    config_.mutable_dense_dpf_pir_config()->set_num_elements(
        kTestDatabaseElements);
}

void SetUpDpf() {
    // Create a DPF instance.
    params_.mutable_value_type()->mutable_xor_wrapper()->set_bitsize(
        kBitsPerBlock);
    params_.set_log_domain_size(
        static_cast<int>(std::ceil(std::log2(kTestDatabaseElements))));
    auto status_or_dpf = DistributedPointFunction::Create(params_);
    if (!status_or_dpf.ok()) {
        std::cerr << "Failed to create DistributedPointFunction: " << status_or_dpf.status() << '\n';
        exit(EXIT_FAILURE);
    }
    dpf_ = std::move(status_or_dpf.value());
}

void GenerateElements() {
    auto status_or_elements = pir_testing::GenerateCountingStrings(kTestDatabaseElements, "Element ");
    if (!status_or_elements.ok()) {
        std::cerr << "Failed to generate elements: " << status_or_elements.status() << '\n';
        exit(EXIT_FAILURE);
    }
    elements_ = std::move(status_or_elements.value());
}

void SetUpDatabase() {
    SetUpConfig();

    if (elements_.empty()) {
        GenerateElements();
    }

    SetUpDpf();

    auto status_or_database = pir_testing::CreateFakeDatabase<DenseDpfPirDatabase>(elements_);
    if (!status_or_database.ok()) {
        std::cerr << "Failed to create database: " << status_or_database.status() << '\n';
        exit(EXIT_FAILURE);        
    }
    database_ = std::move(status_or_database.value());
}

void ExecuteQueries(const std::vector<int>& indices) {
    // Create two servers.
    SetUpDatabase();

    auto status_or_server1 = DenseDpfPirServer::CreatePlain(config_, std::move(database_));
    if (!status_or_server1.ok()) {
        std::cerr << "Failed to create server 1: " << status_or_server1.status() << '\n';
        exit(EXIT_FAILURE);        
    }
    auto server1 = std::move(status_or_server1.value());

    SetUpDatabase();
    auto status_or_server2 = DenseDpfPirServer::CreatePlain(config_, std::move(database_));
    if (!status_or_server2.ok()) {
        std::cerr << "Failed to create server 2: " << status_or_server1.status() << '\n';
        exit(EXIT_FAILURE);        
    }
    auto server2 = std::move(status_or_server2.value());

    // Generate plain requests for `indices`.
    auto status_or_request_generator = pir_testing::RequestGenerator::Create(
        kTestDatabaseElements, DenseDpfPirServer::kEncryptionContextInfo);
    if (!status_or_request_generator.ok()) {
        std::cerr << "Failed to create request generator: " << status_or_request_generator.status() << '\n';
        exit(EXIT_FAILURE);
    }
    auto request_generator = std::move(status_or_request_generator.value());

    PirRequest request1, request2;

    auto status_or_plain_requests = request_generator->CreateDpfPirPlainRequests(indices);
    if (!status_or_plain_requests.ok()) {
        std::cerr << "Failed to create DPF PIR plain requests: " << status_or_plain_requests.status() << '\n';
        exit(EXIT_FAILURE);
    }
    std::tie(*request1.mutable_dpf_pir_request()->mutable_plain_request(),
            *request2.mutable_dpf_pir_request()->mutable_plain_request()) = std::move(status_or_plain_requests.value());


    // Serialize requests
    std::string serialized_request1, serialized_request2;
    request1.SerializeToString(&serialized_request1);
    request2.SerializeToString(&serialized_request2);

    // Deserialize requests
    PirRequest deserialized_request1, deserialized_request2;
    deserialized_request1.ParseFromString(serialized_request1);
    deserialized_request2.ParseFromString(serialized_request2);

    // Obtain a response from each server and add them up.
    auto status_or_response1 = server1->HandleRequest(deserialized_request1);
    if (!status_or_response1.ok()) {
        std::cerr << "Failed to handle request 1: " << status_or_response1.status() << '\n';
        exit(EXIT_FAILURE);
    }
    PirResponse response1 = std::move(status_or_response1.value());

    auto status_or_response2 = server2->HandleRequest(deserialized_request2);
    if (!status_or_response2.ok()) {
        std::cerr << "Failed to handle request 2: " << status_or_response2.status() << '\n';
        exit(EXIT_FAILURE);
    }
    PirResponse response2 = std::move(status_or_response2.value());

    // Serialize responses
    std::string serialized_response1, serialized_response2;
    response1.SerializeToString(&serialized_response1);
    response2.SerializeToString(&serialized_response2);

    // Deserialize responses
    PirResponse deserialized_response1, deserialized_response2;
    deserialized_response1.ParseFromString(serialized_response1);
    deserialized_response2.ParseFromString(serialized_response2);
   
    ASSERT_EQ(deserialized_response1.dpf_pir_response().masked_response_size(),
              deserialized_response2.dpf_pir_response().masked_response_size());

    std::vector<std::string> result;
    for (int i = 0; i < deserialized_response1.dpf_pir_response().masked_response_size();
        i++) {
        ASSERT_EQ(deserialized_response1.dpf_pir_response().masked_response(i).size(),
                  deserialized_response2.dpf_pir_response().masked_response(i).size());

        result.emplace_back(
            deserialized_response1.dpf_pir_response().masked_response(i).size(), '\0');
        for (int j = 0;
            j < deserialized_response1.dpf_pir_response().masked_response(i).size(); ++j) {
            result.back()[j] =
            deserialized_response1.dpf_pir_response().masked_response(i)[j] ^
            deserialized_response2.dpf_pir_response().masked_response(i)[j];
        }
    }

    // Generate expected values
    auto generate_expected = [](const std::vector<int>& indices) {
        std::vector<testing::Matcher<std::string>> expected;
        for (int index : indices) {
            expected.push_back(StartsWith("Element " + std::to_string(index)));
        }
        return expected;
    };

    EXPECT_THAT(result, testing::ElementsAreArray(generate_expected(indices)));

    // Print the indices we are querying for
    std::cout << "Querying for indices: ";
    for (int index : indices) {
        std::cout << index << " ";
    }
    std::cout << std::endl;

    // Print the ultimate results
    std::cout << "Query results: \n";
    for (const auto& res : result) {
        std::cout << res << '\n';
    }
}

}  // namespace 

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <indices (e.g., '2,3')>" << std::endl;
        return 1;
    }

    std::string indices_str(argv[1]);
    std::vector<int> indices;
    size_t pos = 0;
    while ((pos = indices_str.find(',')) != std::string::npos) {
        indices.push_back(std::stoi(indices_str.substr(0, pos)));
        indices_str.erase(0, pos + 1);
    }
    indices.push_back(std::stoi(indices_str));

    distributed_point_functions::ExecuteQueries(indices);
    return 0;
}
