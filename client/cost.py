import statistics
import json
import matplotlib.pyplot as plt
import custom_style
from custom_style import remove_chart_junk
import numpy as np

# Constants
AWS_SERVER_MONTHLY_COST = 80.64
AZURE_SERVER_MONTHLY_COST = 85.16
GCP_SERVER_MONTHLY_COST = 80.64
RELAY_SERVER_MONTHLY_COST = 36
AWS_LAMBDA_COST_PER_SECOND = 0.0000575
GCP_CLOUD_RUN_COST_PER_SECOND = 0.00006895
SMALL_AWS_LAMBDA_COST_PER_SECOND = 0.0000144
SMALL_GCP_CLOUD_RUN_COST_PER_SECOND = 0.00002695
AWS_NETWORK_EGRESS_COST = 0.09  # per GB
AZURE_NETWORK_EGRESS_COST = 0.087  # per GB
GCP_NETWORK_EGRESS_COST = 0.085  # per GB
STORAGE_COST_AWS = 0.026  # per GB
STORAGE_COST_AZURE = 0.023  # per GB
STORAGE_COST_GCP = 0.021  # per GB

# Cryptographic primitives with their respective bandwidth, requests per minute, storage, and latency
CRYPTO_PRIMITIVES = {
    "secret_recovery": {"bandwidth": 25.83, "requests_per_min": 1384, "storage": 2**10, "latency": 0.3404827708378434},
    "signing": {"bandwidth": 67.38, "requests_per_min": 69, "storage": 2**10, "latency": 1.3603502629324793},
    "decryption": {"bandwidth": 59763, "requests_per_min": 5, "storage": 2**10 // 8, "latency": 21.97429116200656},
    "pir": {"bandwidth": 1.38, "requests_per_min": 1196, "storage": (2**10) * 128, "latency": 0.17021635957062245},
    "freshness": {"bandwidth": 2.89, "requests_per_min": 1169, "storage": 2**10, "latency": 0.21895868591964246}
}

# Function to calculate average costs across all cryptographic modules
def calculate_average_costs(t):
    baseline_costs = []
    flock_costs = []
    for primitive, data in CRYPTO_PRIMITIVES.items():
        bandwidth = data["bandwidth"]
        requests_per_min = data["requests_per_min"]
        storage = data["storage"]
        latency = data["latency"]

        baseline_cost_cents, _ = calculate_baseline_cost_in_cents(bandwidth, requests_per_min, storage)
        flock_cost_cents, _ = calculate_flock_cost_in_cents(primitive, bandwidth, requests_per_min, storage, latency)

        baseline_costs.append(baseline_cost_cents)
        flock_costs.append(flock_cost_cents)

    average_baseline = statistics.mean(baseline_costs)
    average_flock = statistics.mean(flock_costs)
    return average_baseline, average_flock

# Variable to be filled in by the user
t = 1  # percentage saturation of baseline throughput

# Function to calculate the average network egress cost
def avg_network_egress_cost():
    return (AWS_NETWORK_EGRESS_COST + AZURE_NETWORK_EGRESS_COST + GCP_NETWORK_EGRESS_COST) / 3

# Function to calculate the sum of storage costs
def sum_storage_costs():
    return STORAGE_COST_AWS + STORAGE_COST_AZURE + STORAGE_COST_GCP

# Function to calculate baseline cost in cents
def calculate_baseline_cost_in_cents(bandwidth, requests_per_min, storage):
    monthly_cost = (AWS_SERVER_MONTHLY_COST + AZURE_SERVER_MONTHLY_COST + GCP_SERVER_MONTHLY_COST) / (30 * 24 * 60 * (t * requests_per_min))
    print(t)
    network_cost = avg_network_egress_cost() * bandwidth / 1000000  # Convert KB to GB for cost calculation
    storage_cost = sum_storage_costs() * storage / 1000000000  # Convert bytes to GB for cost calculation
    total_cost = (monthly_cost + network_cost + storage_cost) * 100  # Convert to cents
    print("network_cost baseline", network_cost)
    print("storage_cost baseline", storage_cost)
    print("monthly_cost baseline", monthly_cost)
    return total_cost, monthly_cost*100

def format_cost(cost):
    return '{:.10f}'.format(cost)

# Function to calculate flock cost in cents
def calculate_flock_cost_in_cents(primitive, bandwidth, requests_per_min, storage, latency):
    monthly_cost = (AZURE_SERVER_MONTHLY_COST + RELAY_SERVER_MONTHLY_COST) / (30 * 24 * 60 * (t * requests_per_min))

    # Use smaller costs for specific primitives
    if primitive in ["freshness", "secret_recovery"]:
        compute_cost = (SMALL_AWS_LAMBDA_COST_PER_SECOND + SMALL_GCP_CLOUD_RUN_COST_PER_SECOND) * latency
    else:
        compute_cost = (AWS_LAMBDA_COST_PER_SECOND + GCP_CLOUD_RUN_COST_PER_SECOND) * latency

    network_cost = avg_network_egress_cost() * bandwidth / 1000000  # Convert KB to GB for cost calculation
    storage_cost = sum_storage_costs() * storage / 1000000000  # Convert bytes to GB for cost calculation
    total_cost = (monthly_cost + compute_cost + network_cost + storage_cost) * 100  # Convert to cents
    print("network_cost flock", network_cost)
    print("storage_cost flock", storage_cost)
    print("monthly_cost flock", monthly_cost)
    print("compute_cost flock", compute_cost)
    return total_cost, (monthly_cost+compute_cost)*100

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

# Main execution
if __name__ == "__main__":
    output = {}
    ratios = []
    for primitive, data in CRYPTO_PRIMITIVES.items():
        bandwidth = data["bandwidth"]  # in KB
        requests_per_min = data["requests_per_min"]
        storage = data["storage"]  # in bytes
        latency = data["latency"]

        # Calculate costs in cents
        baseline_cost_cents, baseline_compute_only = calculate_baseline_cost_in_cents(bandwidth, requests_per_min, storage)
        flock_cost_cents, flock_compute_only = calculate_flock_cost_in_cents(primitive, bandwidth, requests_per_min, storage, latency)
        ratio = flock_cost_cents / baseline_cost_cents if baseline_cost_cents != 0 else 0

        ratios.append(ratio)  # Storing the numerical value of the ratio for calculations

        # Organizing data in dictionary
        output[primitive] = {
            "storage_cost": format_cost(sum_storage_costs() * storage / 1000000000 * 100),  # Convert bytes to GB
            "network_cost": format_cost(avg_network_egress_cost() * bandwidth / 1000000 * 100),  # Convert KB to GB
            "baseline": {
                "compute_cost": format_cost(baseline_compute_only),
                "total_cost": format_cost(baseline_cost_cents)
            },
            "flock": {
                "compute_cost": format_cost(flock_compute_only),
                "total_cost": format_cost(flock_cost_cents)
            },
            "ratio": format_cost(ratio)
        }

    # Output the JSON file
    with open('crypto_module_costs.json', 'w') as f:
        json.dump(output, f, indent=4)

    # Calculate and print mean and median of the ratios
    mean_ratio = statistics.mean(ratios)
    median_ratio = statistics.median(ratios)
    print(f"Mean Ratio: {mean_ratio}")
    print(f"Median Ratio: {median_ratio}")
    
    # Main execution for plotting
    t_values = [i * 0.01 for i in range(5, 101)]
    average_baseline_costs = []
    average_flock_costs = []

    for t in t_values:
        average_baseline, average_flock = calculate_average_costs(t)
        average_baseline_costs.append(average_baseline)
        average_flock_costs.append(average_flock)
        
    # Specific t value to check
    t = 0.5
    average_baseline_at_specific_t, average_flock_at_specific_t = calculate_average_costs(t)
    print(f"Average cost at t={t}: {average_baseline_at_specific_t} for Baseline, {average_flock_at_specific_t} for Flock")

    # Plotting
    plt.rcParams['font.size'] = 16
    fig, ax = plt.subplots(figsize=(5,5))

    # Set the y-axis ticks
    plt.yticks(np.arange(0, 0.81, step=0.2))

    ax.plot(t_values, average_flock_costs, label='Flock', color=blend_with_white('#48D1CC'), linewidth=2)  # default linewidth * 2
    ax.plot(t_values, average_baseline_costs, label='Baseline', color=blend_with_white('#9370DB'), linewidth=2)  # default linewidth * 2

    ax.set_ylim(0, 0.6)
    ax.set_xlabel('Utilization of Baseline', fontsize=14)
    ax.set_ylabel('Cost (¢)', fontsize=14)

    remove_chart_junk(plt, ax, grid=True)

    ax.legend(loc='upper right', fontsize=12)

    custom_style.save_fig(fig, 'line_graph.png', [3.5, 2.5])
    plt.savefig('line_graph.png')
    plt.savefig('line_graph.pgf')
    plt.show()