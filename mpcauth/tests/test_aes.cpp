#include <iostream>
#include <cstring>
#include <openssl/aes.h>
#include <openssl/rand.h>
#include <sstream>
#include <iomanip>

using namespace std;

std::string encrypt_AES_256(std::string plaintext, std::string key) {
    // Create a new AES key object
    AES_KEY aes_key;
    AES_set_encrypt_key((const unsigned char*) key.c_str(), 256, &aes_key);

    // Calculate the number of blocks in the plaintext
    size_t num_blocks = plaintext.length() / AES_BLOCK_SIZE + 1;

    // Add padding to the plaintext so that its length is a multiple of the block size
    size_t padded_len = num_blocks * AES_BLOCK_SIZE;
    std::string padded_text = plaintext;
    padded_text.resize(padded_len, '\0');

    // Allocate memory for the ciphertext
    unsigned char* ciphertext = new unsigned char[padded_len];

    // Encrypt the data using AES-256
    for (size_t i = 0; i < num_blocks; i++) {
        AES_encrypt((const unsigned char*) (padded_text.c_str() + i*AES_BLOCK_SIZE), ciphertext + i*AES_BLOCK_SIZE, &aes_key);
    }

    // Convert the ciphertext to a string
    std::string encrypted_data((char*) ciphertext, padded_len);

    // Free the memory used for the ciphertext
    delete[] ciphertext;

    return encrypted_data;
}


std::string decrypt_AES_256(std::string ciphertext, std::string key) {
    // Create a new AES key object
    AES_KEY aes_key;
    AES_set_decrypt_key((const unsigned char*) key.c_str(), 256, &aes_key);

    // Calculate the number of blocks in the ciphertext
    size_t num_blocks = ciphertext.length() / AES_BLOCK_SIZE;

    // Allocate memory for the plaintext
    unsigned char* plaintext = new unsigned char[num_blocks * AES_BLOCK_SIZE];

    // Decrypt the data using AES-256
    for (size_t i = 0; i < num_blocks; i++) {
        AES_decrypt((const unsigned char*) (ciphertext.c_str() + i*AES_BLOCK_SIZE), plaintext + i*AES_BLOCK_SIZE, &aes_key);
    }

    // Strip off any padding that was added during encryption
    size_t unpadded_len = num_blocks * AES_BLOCK_SIZE;
    while (plaintext[unpadded_len - 1] == '\0') {
        unpadded_len--;
    }

    // Convert the plaintext to a string
    std::string decrypted_data((char*) plaintext, unpadded_len);

    // Free the memory used for the plaintext
    delete[] plaintext;

    return decrypted_data;
}


std::string generate_AES_256_key() {
    const int key_len = 32; // 256 bits
    unsigned char key[key_len];

    // Generate a random key
    if (RAND_bytes(key, key_len) != 1) {
        // Handle error
        throw std::runtime_error("Error generating random key");
    }

    // Convert the key bytes to a hex string
    std::stringstream ss;
    for (int i = 0; i < key_len; i++) {
        ss << std::hex << std::setw(2) << std::setfill('0') << (int) key[i];
    }

    return ss.str();
}


// // Example usage
int main() {
    std::string plaintext = "Hell00";
    std::string key = generate_AES_256_key(); // 256-bit key

    std::cout << "key" << key << std::endl;

    std::string ciphertext = encrypt_AES_256(plaintext, key);

    std::cout << "Plaintext: " << plaintext << " " << plaintext.length() << std::endl;
    std::cout << "Ciphertext: " << ciphertext << " " << ciphertext.length() << std::endl;

    auto dec = decrypt_AES_256(ciphertext, key);
    std::cout << "Decrypted plaintext: " << dec << " " << dec.length() << std::endl; 
    return 0;
}