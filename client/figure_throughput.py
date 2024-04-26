import json
import matplotlib.pyplot as plt
import custom_style
from custom_style import remove_chart_junk

def blend_with_white(hex_color):
    """
    Blend the given color with white in a 30:70 ratio.
    """
    # Convert the hex color string to RGB
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    
    # Blend with white (255, 255, 255) in a 70:30 ratio
    r = int((r * 0.7) + (255 * 0.3))
    g = int((g * 0.7) + (255 * 0.3))
    b = int((b * 0.7) + (255 * 0.3))
    
    return f'#{r:02x}{g:02x}{b:02x}'

# This is the data shown in Flock's paper
flock_data = {
    "Secret Recovery": {"Flock": 1376, "Baseline": 1384},
    "Signing": {"Flock": 66, "Baseline": 69},
    "Decryption": {"Flock": 5, "Baseline": 5},
    "PIR": {"Flock": 1195, "Baseline": 1196},
    "Freshness": {"Flock": 1162, "Baseline": 1169}
}


flock_data = []
baseline_data = []
for mode in ["baseline", "flock"]:
    for op in ["sharding_recover", "signing_sign", "aes_encrypt", "pir", "freshness_retrieve_file"]:
        try:
            with open(f"../results/tp_{mode}_{op}.json") as f:
                tp_data = json.load(f)
        except Exception as e:
            print(e)

        max_tp = 0
        for key, value in tp_data.items(): 
            max_tp = max(max_tp, value)

        if mode == "baseline":
            baseline_data.append(max_tp)
        else:
            flock_data.append(max_tp)
        print(f"Maximum throughput for {mode} {op}:", max_tp)
    print("\n")

categories = ["Secret Recovery", "Signing", "Decryption", "PIR", "Freshness"]
# flock_data = [data[category]["Flock"] for category in categories]
# baseline_data = [data[category]["Baseline"] for category in categories]

normalized_flock_data = [flock / baseline if baseline != 0 else 0 for flock, baseline in zip(flock_data, baseline_data)]

plt.rcParams['font.size'] = 16

bar_width = 0.35
index = range(len(categories))

fig, ax = plt.subplots(figsize=(7, 5))

darker_turquoise = blend_with_white('#48D1CC')
darker_purple = blend_with_white('#9370DB')

colors_flock = [darker_turquoise for _ in categories]
colors_baseline = [darker_purple for _ in categories]

baseline_normalized = [1] * len(categories)

bar1 = ax.bar(index, normalized_flock_data, bar_width, label='Flock', color=colors_flock)
bar2 = ax.bar([i + bar_width for i in index], baseline_normalized, bar_width, label='Baseline', color=colors_baseline)

ax.set_ylim(0.0, 1.1)

ax.set_xlabel('Module', fontsize=14)
ax.set_ylabel('Req./Min. (Normalized)', fontsize=14)  # Changed "Maximum" to "Max"

categories[0] = "Secret\nRecovery"  # Break "Secret Recovery" into two lines
ax.set_xticks([i + bar_width/2 for i in index])
ax.set_xticklabels(categories, rotation=45, ha="right", fontsize=12)  # Slanted x-axis labels

# Using custom_style
remove_chart_junk(plt, ax, grid=True)

# Legend modification
handles = [bar1[0], bar2[0]]
labels = ['Flock', 'Baseline']
ax.legend(handles, labels, loc='upper right', fontsize=12)

# plt.tight_layout()
custom_style.save_fig(fig, '../figures/throughput.png', [4, 3])
plt.savefig('../figures/throughput.png')
plt.savefig('../figures/throughput.pgf')
plt.show()
