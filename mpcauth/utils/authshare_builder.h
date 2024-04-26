#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
using namespace std;
using namespace emp;

template <int nP>
class AuthShareBuilder
{
public:
	vector<bool> plaintext_shares;
	vector<AuthBitShare<nP>> auth_shares[nP+1];

    block* keys[nP+1][nP+1];
    block* macs[nP+1][nP+1];
    block Deltas[nP+1];

    PRG prg;

    int len;
	AuthShareBuilder(int len) {
		this->len = len;
        init_macs_and_keys();
        gen_deltas();
	}

    AuthShareBuilder(int len, block deltas[nP+1]) {
		this->len = len;
        init_macs_and_keys();
        std::copy(deltas, deltas + nP + 1, Deltas);
    }

	~AuthShareBuilder() {
        for (int i = 1; i <= nP; ++i) {
            for (int j = 1; j <= nP; ++j) {
                delete[] keys[i][j];
                delete[] macs[i][j];
            }
        }
    }

    void gen_deltas() {
        for (int i = 1; i <= nP; ++i) {
            prg.random_block(&Deltas[i], 1);
        }
    }

    void gen_auth_share(bool *plaintext_bits) {
        auto shares = to_xor_shares(plaintext_bits);
        
        for (int i = 1; i <= nP; ++i) {
            bool* share = shares[i-1];
            for (int j = 1; j <= nP; ++j) {
                for (int k = 0; k < len; ++k) {
                    macs[i][j][k] = keys[j][i][k] ^ (select_mask[share[k]? 1:0] & Deltas[j]);
                }
            }
        }

        for (int i = 1; i <= nP; ++i) {
            bool* share = shares[i-1];
            // party i should get a mac tag from every other parties that verifies the identity
            // party i should also store a key they used to generate mac tags for other parties.
            for (int k = 0; k < len; ++k) {
                AuthBitShare<nP> abit;
                abit.bit_share = share[k];
                for (int j = 1; j <= nP; ++j) {
                    abit.key[j] = keys[i][j][k];
                    abit.mac[j] = macs[i][j][k];
                }
                auth_shares[i].emplace_back(abit);
            }
        }
    }

    bool** to_xor_shares(bool* input) {
        bool **shares = new bool*[nP];
        for (int i = 0; i < nP; ++i) {
            shares[i] = new bool[len];
        }

        // Copy input to shares[0]
        for (int i = 0; i < len; ++i) {
            shares[0][i] = input[i];
        }

        for (int i = 1; i < nP; ++i) {
            prg.random_bool(shares[i], len);
            for (int j = 0; j < len; ++j) {
                shares[0][j] ^= shares[i][j];
            }
        }
        return shares;
    }

    static std::vector<uint8_t> serializeAuthBitShare(const AuthBitShare<nP>& obj)
    {
        std::vector<uint8_t> buffer;

        // Serialize bit_share
        buffer.push_back(static_cast<uint8_t>(obj.bit_share));

        // Serialize key array
        for (int i = 0; i < nP + 1; ++i)
        {
            const uint8_t* ptr = reinterpret_cast<const uint8_t*>(&obj.key[i]);
            buffer.insert(buffer.end(), ptr, ptr + sizeof(__m128i));
        }

        // Serialize mac array
        for (int i = 0; i < nP + 1; ++i)
        {
            const uint8_t* ptr = reinterpret_cast<const uint8_t*>(&obj.mac[i]);
            buffer.insert(buffer.end(), ptr, ptr + sizeof(__m128i));
        }

        return buffer;
    }

    static void deserializeAuthBitShare(AuthBitShare<nP>& obj, const std::vector<uint8_t>& buffer, size_t& offset)
    {
        // Deserialize bit_share
        obj.bit_share = static_cast<bool>(buffer[offset]);
        ++offset;

        // Deserialize key array
        for (int i = 0; i < nP + 1; ++i)
        {
            std::copy(buffer.begin() + offset, buffer.begin() + offset + sizeof(__m128i), reinterpret_cast<uint8_t*>(&obj.key[i]));
            offset += sizeof(__m128i);
        }

        // Deserialize mac array
        for (int i = 0; i < nP + 1; ++i)
        {
            std::copy(buffer.begin() + offset, buffer.begin() + offset + sizeof(__m128i), reinterpret_cast<uint8_t*>(&obj.mac[i]));
            offset += sizeof(__m128i);
        }
    }

    static std::vector<uint8_t> serialize(const std::vector<AuthBitShare<nP>>& vec)
    {
        std::vector<uint8_t> buffer;

        // Serialize the size of the vector first
        size_t size = vec.size();
        buffer.insert(buffer.end(), reinterpret_cast<uint8_t*>(&size), reinterpret_cast<uint8_t*>(&size) + sizeof(size_t));

        // Serialize each AuthBitShare object
        for (const auto& obj : vec)
        {
            std::vector<uint8_t> objBuffer = serializeAuthBitShare(obj);
            buffer.insert(buffer.end(), objBuffer.begin(), objBuffer.end());
        }

        return buffer;
    }

    static std::vector<AuthBitShare<nP>> deserialize(const std::vector<uint8_t>& buffer)
    {
        std::vector<AuthBitShare<nP>> vec;
        size_t offset = 0;

        // Deserialize the size of the vector first
        size_t size;
        std::copy(buffer.begin() + offset, buffer.begin() + offset + sizeof(size_t), reinterpret_cast<uint8_t*>(&size));
        offset += sizeof(size_t);

        // Deserialize each AuthBitShare object
        for (size_t i = 0; i < size; ++i)
        {
            AuthBitShare<nP> obj;
            deserializeAuthBitShare(obj, buffer, offset);
            vec.push_back(obj);
        }

        return vec;
    }

    static std::vector<uint8_t> serializeBlock(const block& data) {
        std::vector<uint8_t> buffer(sizeof(block));
        std::memcpy(buffer.data(), &data, sizeof(block));
        return buffer;
    }

    // Deserialize byte vector to __m128i
    static block deserializeBlock(const std::vector<uint8_t>& buffer) {
        if (buffer.size() != sizeof(block)) {
            throw std::runtime_error("Invalid buffer size for deserialization");
        }
        block result;
        std::memcpy(&result, buffer.data(), sizeof(block));
        return result;
    }

    static void copy_vec_to_bool_array(const std::vector<uint8_t>& vec, bool* arr) {
        for (size_t i = 0; i < vec.size(); ++i) {
            uint8_t byte = vec[i];
            for (size_t j = 0; j < 8; ++j) {
                arr[i * 8 + j] = (byte >> j) & 1;
            }
        }
    }


private:
    void init_macs_and_keys() {
        for (int i = 1; i <= nP; ++i) {
            for (int j = 1; j <= nP; ++j) {
                macs[i][j] = new block[len];
                keys[i][j] = new block[len];
                prg.random_block(keys[i][j], len);
            }
        }
    }
};