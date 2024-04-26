import os
import json
import re
import sys
import matplotlib.pyplot as plt
import custom_style
from custom_style import remove_chart_junk


op_titles = {
    "sharding_setup": "Secret Recovery setup_module",
    "aes_setup": "Decryption setup_module",
    "signing_keygen": "Signing setup_module",
    "freshness_store_file": "Freshness setup_module",
    "pir_setup": "PIR setup_module",

    "sharding_recover": "Secret Recovery execute",
    "aes_encrypt": "Decryption execute",
    "signing_sign": "Signing execute",
    "freshness_retrieve_file": "Freshness execute",
    "pir": "PIR execute"
}


def blend_with_white(hex_color):
    """
    Blend the given color with white in a 50:50 ratio.
    :param hex_color: A hex color string.
    :return: A hex color string of the blended color.
    """
    # Convert the hex color string to RGB
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    
    # Blend with white (255, 255, 255) in a 50:50 ratio
    r = (r + 255) // 2
    g = (g + 255) // 2
    b = (b + 255) // 2
    
    # Convert the RGB values back to a hex color string
    return f'#{r:02x}{g:02x}{b:02x}'


def format_to_latex(s):
    match = re.match(r"2\^(\d+)", s)
    if match:
        return r"$2^{" + match.group(1) + r"}$"
    else:
        return s


def print_table(folder_path):
    for op in ["sharding_setup", "sharding_recover", "signing_keygen", "signing_sign", "signing_sign", "pir_setup", "pir", "aes_setup", "aes_encrypt"]:

        log_input_size = 7 if op in ["aes_setup", "aes_encrypt"] else 10

        try:
            for mode in ["baseline", "flock"]:
                file = f"{op}_{log_input_size}_{mode}.json"
                with open(os.path.join(folder_path, file), "r") as file:
                    runtime_dict = json.load(file)

                    server_time = runtime_dict["server_time"]
                    client_time = runtime_dict["client_time"]
                    e2e_time = runtime_dict["e2e_time"]
                    in_mem_time = runtime_dict["inmem_time"]

                    title = op_titles[op]
                    print(title, mode)
                    print("Server time mean and std:", server_time["mean"], server_time["std"])
                    print("Client time mean and std:", client_time["mean"], client_time["std"])
                    print("E2E time mean and std:", e2e_time["mean"], e2e_time["std"])
                    print("\n")
        except Exception as e:
            print(e)


if __name__ == "__main__":
    folder_path = "../results"
    print_table(folder_path)
    
    files = os.listdir(folder_path)
    
    for op in ["sharding_recover", "signing_sign", "pir", "freshness_retrieve_file", "aes_encrypt"]:
        print(f"Generating figure for {op}...")

        latency_files = [file for file in files if file.startswith(op) and file.endswith(".json") and not file.startswith("pir_setup")]
        
        latency_dict_baseline = {}
        latency_dict_flock = {}
        latency_dict_inmem = {}
        for file in latency_files:
            parts = file[len(op)+1:-5].split("_")
            log_input_size, mode = parts[-2], parts[-1]

            if op == "aes_encrypt":
                log_input_size = str(int(log_input_size)+3)
            
            with open(os.path.join(folder_path, file), "r") as file:
                runtime_dict = json.load(file)

                server_time = runtime_dict["server_time"]["mean"]
                client_time = runtime_dict["client_time"]["mean"]
                e2e_time = runtime_dict["e2e_time"]["mean"]
                in_mem_time = runtime_dict["inmem_time"]["mean"]

            if mode == "baseline":
                latency_dict_baseline[f"2^{log_input_size}"] = e2e_time
            elif mode == "flock":
                latency_dict_flock[f"2^{log_input_size}"] = e2e_time
            
            if op == "pir":
                latency_dict_inmem[f"2^{log_input_size}"] = in_mem_time

        if op == "sharding_recover":
            title = "Secret Recovery"
        elif op == "aes_encrypt":
            title = "Decryption"
        elif op == "signing_sign":
            title = "Signing"
        elif op == "freshness_retrieve_file":
            title = "Freshness"
        else:
            title = "PIR"

        units = {
            'pir': 'Entries',
            'decryption': 'b',
            'signing': 'B',
        }

        fig, ax = plt.subplots(figsize=(8, 8))

        ax.set_title(title)
        max_y_val = 0

        latency_dict_baseline = dict(sorted(latency_dict_baseline.items(), key=lambda x: int(x[0][2:])))
        latency_dict_flock = dict(sorted(latency_dict_flock.items(), key=lambda x: int(x[0][2:])))
        latency_dict_inmem = dict(sorted(latency_dict_inmem.items(), key=lambda x: int(x[0][2:])))

        data_list = [latency_dict_baseline, latency_dict_flock]
        colors = ['mediumpurple', 'mediumturquoise', 'indigo']
        markers = ['o', '^', 'o']

        if op == "pir":
            data_list.append(latency_dict_inmem)

        for idx, latency_data in enumerate(data_list):
            input_sizes = [format_to_latex(size) for size in latency_data.keys()]
            latencies = [data * 1000 for data in latency_data.values()]
            marker_sizes = [6 if colors[idx] == 'mediumpurple' else 4 for _ in latencies]
            ax.plot(input_sizes, latencies, color=colors[idx], marker=markers[idx], markersize=marker_sizes[idx])

        # Setting y-limits and ticks
        if op == "signing_sign":
            max_y_val = 1600
        elif op == "aes_encrypt":
            max_y_val = 80000
        elif op == "pir":
            max_y_val = 700
        elif op == "sharding_recover":
            max_y_val = 1000
        else:
            max_y_val = 300
        ax.set_ylim(0, max_y_val)
        tick_interval = max_y_val / 4
        ax.set_yticks([i for i in range(0, int(max_y_val) + 1, int(tick_interval))])

        ax.set_xlabel(f'Input Size ({units.get(op, "B")})')
        ax.set_ylabel('Latency (ms)')
        remove_chart_junk(plt, ax, xticks=True, ticks=True, grid=True)
        custom_style.save_fig(fig, f'../figures/latency_{op}.png', [2.2, 1.7])
        plt.savefig(f'../figures/latency_{op}.pgf')

    # Reintegrated Legend Generation
    colors = ['mediumpurple', 'mediumturquoise', 'indigo']
    markers = ['o', '^', 'o']
    labels = ['Baseline', 'Flock', 'In-Memory Baseline']

    fig_legend = plt.figure(figsize=(2, 2))
    ax_legend = fig_legend.add_subplot(111)

    for i in range(3):
        ax_legend.plot([], [], color=colors[i], marker=markers[i], markersize=8, label=labels[i])

    ax_legend.axis('off')
    handles, labels = ax_legend.get_legend_handles_labels()

    leg = fig_legend.legend(handles, labels, loc='center', frameon=True, ncol=1, handletextpad=0.5, edgecolor='gray', fontsize='large')

    fig_legend.canvas.draw()

    fig_legend.savefig('../figures/latency_legend.png', dpi=300)
    fig_legend.savefig('../figures/latency_legend.pgf', dpi=300)

    plt.show()