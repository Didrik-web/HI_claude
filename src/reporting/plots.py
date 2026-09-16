from pathlib import Path
import matplotlib.pyplot as plt


def save_schedule_plot(schedule, path, title):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    p = schedule.pivot(index="time", columns="depot", values="charging_MW")
    ax = p.plot(figsize=(12, 5)); ax.set_title(title); ax.set_ylabel("Charging power [MW]"); ax.set_xlabel("Time")
    plt.tight_layout(); plt.savefig(path, dpi=160); plt.close()


def save_network_plot(results, path, title):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(results.time, results.max_line_loading_percent, label="Max line loading [%]")
    ax.plot(results.time, results.max_trafo_loading_percent, label="Max transformer loading [%]")
    ax.set_title(title); ax.set_ylabel("Loading [%]"); ax.set_xlabel("Time"); ax.legend()
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)
