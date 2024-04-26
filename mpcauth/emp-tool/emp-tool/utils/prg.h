#ifndef EMP_PRG_H__
#define EMP_PRG_H__
#include "emp-tool/utils/block.h"
#include "emp-tool/utils/aes.h"
#include "emp-tool/utils/utils.h"
#include "emp-tool/utils/constants.h"
#include <climits>
#include <memory>

#ifdef ENABLE_RDSEED
#include <x86intrin.h>
#else
#include <random>
#endif

namespace emp {

class PRG { public:
	uint64_t counter = 0;
	AES_KEY aes;
	block key;
	PRG(const void * seed = nullptr, int id = 0) {
		if (seed != nullptr) {
			reseed((const block *)seed, id);
		} else {
			block v;
#ifndef ENABLE_RDSEED
			uint32_t * data = (uint32_t *)(&v);
			std::random_device rand_div("/dev/urandom");
			for (size_t i = 0; i < sizeof(block) / sizeof(uint32_t); ++i)
				data[i] = rand_div();
#else
			unsigned long long r0, r1;
			int i = 0;
			// To prevent an AMD CPU bug. (PR #156)
			for(; i < 10; ++i)
				if((_rdseed64_step(&r0) == 1) && (r0 != ULLONG_MAX) && (r0 != 0)) break;
			if(i == 10)error("RDSEED FAILURE");

			for(i = 0; i < 10; ++i)
				if((_rdseed64_step(&r1) == 1) && (r1 != ULLONG_MAX) && (r1 != 0)) break;
			if(i == 10)error("RDSEED FAILURE");

			v = makeBlock(r0, r1);
#endif
			reseed(&v, id);
		}
	}
	void reseed(const block* seed, uint64_t id = 0) {
		block v = _mm_loadu_si128(seed);
		v ^= makeBlock(0LL, id);
		key = v;
		AES_set_encrypt_key(v, &aes);
		counter = 0;
	}

	void random_data(void *data, int nbytes) {
		random_block((block *)data, nbytes/16);
		if (nbytes % 16 != 0) {
			block extra;
			random_block(&extra, 1);
			memcpy((nbytes/16*16)+(char *) data, &extra, nbytes%16);
		}
	}

	void random_bool(bool * data, int length) {
		uint8_t * uint_data = (uint8_t*)data;
		random_data_unaligned(uint_data, length);
		for(int i = 0; i < length; ++i)
			data[i] = uint_data[i] & 1;
	}

	void random_data_unaligned(void *data, int nbytes) {
		size_t size = nbytes;
		void *aligned_data = data;
		if(std::align(sizeof(block), sizeof(block), aligned_data, size)) {
			int chopped = nbytes - size;
			random_data(aligned_data, nbytes - chopped);
			block tmp[1];
			random_block(tmp, 1);
			memcpy(data, tmp, chopped);
		} else {
			block tmp[2];
			random_block(tmp, 2);
			memcpy(data, tmp, nbytes);
		}
	}

	void random_block(block * data, int nblocks=1) {
		block tmp[AES_BATCH_SIZE];
		for(int i = 0; i < nblocks/AES_BATCH_SIZE; ++i) {
			for (int j = 0; j < AES_BATCH_SIZE; ++j)
				tmp[j] = makeBlock(0LL, counter++);
			AES_ecb_encrypt_blks<AES_BATCH_SIZE>(tmp, &aes);
			memcpy(data + i*AES_BATCH_SIZE, tmp, AES_BATCH_SIZE*sizeof(block));
		}
		int remain = nblocks % AES_BATCH_SIZE;
		for (int j = 0; j < remain; ++j)
			tmp[j] = makeBlock(0LL, counter++);
		AES_ecb_encrypt_blks(tmp, remain, &aes);
		memcpy(data + (nblocks/AES_BATCH_SIZE)*AES_BATCH_SIZE, tmp, remain*sizeof(block));
	}

	typedef uint64_t result_type;
	result_type buffer[32];
	size_t ptr = 32;
	static constexpr result_type min() {
		return 0;
	}
	static constexpr result_type max() {
		return 0xFFFFFFFFFFFFFFFFULL;
	}
	result_type operator()() {
		if(ptr == 32) {		
			random_block((block*)buffer, 16);
			ptr = 0;
		}
		return buffer[ptr++];
	}
};

}
#endif// PRP_H__
