#include "json/json.h"

int test_json() {
    // Create a JSON string
    std::string jsonString = "{\"name\": \"John\", \"age\": 30}";

    // Parse the JSON string
    Json::Value root;
    Json::Reader reader;
    bool parsingSuccessful = reader.parse(jsonString, root);

    // Check if parsing was successful
    if (!parsingSuccessful) {
        std::cout << "Failed to parse JSON" << std::endl;
        return 1;
    }

    // Extract data from the JSON object
    std::string name = root["name"].asString();
    int age = root["age"].asInt();

    // Print the data
    std::cout << "Name: " << name << std::endl;
    std::cout << "Age: " << age << std::endl;
    return 0;
}

int main(int argc, char** argv) {
	test_json();
}