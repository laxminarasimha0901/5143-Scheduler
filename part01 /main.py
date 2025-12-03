# main.py
import json
import sys
import random
from schedulers.fcfs import FCFSScheduler
from schedulers.round_robin import RRScheduler
from schedulers.sjf import SJFScheduler
from schedulers.srtf import SRTFScheduler
from schedulers.priority import PriorityScheduler
from schedulers.adaptive import AdaptiveScheduler
from pkg import Process
from visualizer import run_simulation_with_gantt

def load_processes_from_json(filename, limit=None, heavy=None, arrival_strategy="staggered"):
    with open(filename) as f:
        data = json.load(f)
    processes = []
    current_time = 0
    
    for idx, p in enumerate(data[:limit]):
        bursts = []
        for b in p["bursts"]:
            if "cpu" in b:
                bursts.append({"cpu": b["cpu"]})
            elif "io" in b:
                bursts.append({"io": {"type": b["io"]["type"], "duration": b["io"]["duration"]}})
        
        # Determine arrival time based on strategy
        if arrival_strategy == "staggered":
            # Processes arrive at regular intervals (every 2-5 time units)
            arrival_time = current_time
            current_time += random.randint(2, 5)
        elif arrival_strategy == "random":
            # Processes arrive at random times within a range
            arrival_time = random.randint(0, 50)
        elif arrival_strategy == "burst":
            # Processes arrive in bursts (groups arrive together, then gap)
            if idx % 5 == 0:
                current_time += random.randint(10, 20)
            arrival_time = current_time + random.randint(0, 2)
        elif arrival_strategy == "original":
            # Use the arrival time from JSON file if present
            arrival_time = p.get("arrival_time", 0)
        else:
            # Default: staggered
            arrival_time = current_time
            current_time += random.randint(2, 5)
        
        proc = Process(
            pid=p["pid"],
            bursts=bursts,
            priority=p["priority"],
            arrival_time=arrival_time,
            quantum=p.get("quantum", 4)
        )
        
        # Filter processes based on heavy parameter
        if heavy:
            if heavy == "cpu" and not is_cpu_heavy(proc):
                continue
            elif heavy == "io" and not is_io_heavy(proc):
                continue
            elif heavy == "mixed" and not is_mixed_heavy(proc):
                continue
        
        processes.append(proc)
    
    # Sort by arrival time to ensure proper ordering
    processes.sort(key=lambda p: p.arrival_time)
    return processes

def is_cpu_heavy(process):
    """Check if process is CPU-heavy (more CPU bursts than I/O bursts)"""
    cpu_count = sum(1 for b in process.bursts if "cpu" in b)
    io_count = sum(1 for b in process.bursts if "io" in b)
    return cpu_count > io_count

def is_io_heavy(process):
    """Check if process is I/O-heavy (more I/O bursts than CPU bursts)"""
    cpu_count = sum(1 for b in process.bursts if "cpu" in b)
    io_count = sum(1 for b in process.bursts if "io" in b)
    return io_count > cpu_count

def is_mixed_heavy(process):
    """Check if process is mixed (roughly equal CPU and I/O bursts)"""
    cpu_count = sum(1 for b in process.bursts if "cpu" in b)
    io_count = sum(1 for b in process.bursts if "io" in b)
    return cpu_count == io_count or abs(cpu_count - io_count) == 1

if __name__ == "__main__":
    args = {}
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            args[k] = v
    
    file_num = args.get("file_num", "1").zfill(4)
    limit = int(args["limit"]) if "limit" in args else None
    cpus = int(args.get("cpus", 1))
    ios = int(args.get("ios", 1))
    heavy = args.get("heavy")  # Get the heavy parameter
    arrival_strategy = args.get("arrival", "staggered")  # Get arrival time strategy
    seed = args.get("seed")  # Optional random seed for reproducibility
    
    # Set random seed if provided
    if seed:
        random.seed(int(seed))
    
    # Validate heavy parameter
    if heavy and heavy not in ["cpu", "io", "mixed"]:
        print(f"Error: Invalid heavy parameter '{heavy}'. Must be one of: cpu, io, mixed")
        sys.exit(1)
    
    # Validate arrival strategy
    valid_strategies = ["staggered", "random", "burst", "original"]
    if arrival_strategy not in valid_strategies:
        print(f"Error: Invalid arrival strategy '{arrival_strategy}'. Must be one of: {', '.join(valid_strategies)}")
        sys.exit(1)
    
    processes = load_processes_from_json(
        f"./job_jsons/processfile_{file_num}.json", 
        limit=limit,
        heavy=heavy,
        arrival_strategy=arrival_strategy
    )
    
    # Default scheduler (can be overridden by command line argument)
    scheduler_class_name = args.get("scheduler", "RRScheduler")
    
    # Map scheduler name to class
    scheduler_map = {
        "FCFS": FCFSScheduler,
        "FCFSScheduler": FCFSScheduler,
        "RR": RRScheduler,
        "RRScheduler": RRScheduler,
        "SJF": SJFScheduler,
        "SJFScheduler": SJFScheduler,
        "SRTF": SRTFScheduler,
        "SRTFScheduler": SRTFScheduler,
        "Priority": PriorityScheduler,
        "PriorityScheduler": PriorityScheduler,
        "Adaptive": AdaptiveScheduler,
        "AdaptiveScheduler": AdaptiveScheduler
    }
    
    SchedulerClass = scheduler_map.get(scheduler_class_name, RRScheduler)
    
    print(f"Running simulation with {SchedulerClass.__name__}")
    if heavy:
        print(f"Process filter: {heavy}-heavy processes only")
    print(f"Arrival strategy: {arrival_strategy}")
    print(f"Processes loaded: {len(processes)}")
    print(f"CPUs: {cpus}, I/O devices: {ios}")
    
    # Check if any processes were loaded
    if len(processes) == 0:
        print("\nError: No processes loaded!")
        if heavy:
            print(f"No processes matched the '{heavy}-heavy' filter.")
            print("Try running without the heavy parameter or with a different filter (cpu/io/mixed).")
        sys.exit(1)
    
    print(f"Arrival time range: {min(p.arrival_time for p in processes)} - {max(p.arrival_time for p in processes)}")
    
    scheduler = SchedulerClass(num_cpus=cpus, num_ios=ios, verbose=False)
    for p in processes:
        scheduler.add_process(p)
    
    # used for debugging
    #print(f"\nDebug info:")
    #print(f"Ready queue size: {len(scheduler.ready_queue)}")
    #print(f"Processes in ready queue: {[p.pid for p in scheduler.ready_queue]}")
    #print(f"Has jobs: {scheduler.has_jobs()}")
    #print(f"First few processes arrival times: {[p.arrival_time for p in list(scheduler.ready_queue)[:3]]}")
    
    # Run simulation with Gantt chart visualization and timeline export
    output_filename = f"./timelines/timeline{file_num}.csv"
    visualizer = run_simulation_with_gantt(scheduler, output_filename)
    
    # Print final statistics
    print("\n" + "="*60)
    print("SIMULATION COMPLETE")
    print("="*60)
    scheduler.print_stats()
    
    # Export timeline data
    scheduler.export_json(f"./timelines/timeline{file_num}.json")
    
    print(f"Timeline data exported to:")
    print(f"  CSV: {output_filename}")
    print(f"  JSON: ./timelines/timeline{file_num}.json")