# main.py
import json
import sys
from schedulers.fcfs import FCFSScheduler
from schedulers.round_robin import RRScheduler
from schedulers.sjf import SJFScheduler
from schedulers.srtf import SRTFScheduler
from pkg import Process
from visualizer import run_simulation_with_gantt

def load_processes_from_json(filename, limit=None):
    with open(filename) as f:
        data = json.load(f)
    processes = []
    for p in data[:limit]:
        bursts = []
        for b in p["bursts"]:
            if "cpu" in b:
                bursts.append({"cpu": b["cpu"]})
            elif "io" in b:
                bursts.append({"io": {"type": b["io"]["type"], "duration": b["io"]["duration"]}})
        proc = Process(
            pid=p["pid"],
            bursts=bursts,
            priority=p["priority"],
            arrival_time=p["arrival_time"],
            quantum=p.get("quantum", 4)
        )
        processes.append(proc)
    return processes

if __name__ == "__main__":
    #args = {k: v for arg in sys.argv[1:] for k, v in [arg.split("=", 1)]} if len(sys.argv) > 1 else {}
    args = {}
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            args[k] = v
    file_num = args.get("file_num", "1").zfill(4)
    limit = int(args["limit"]) if "limit" in args else None
    cpus = int(args.get("cpus", 1))
    ios = int(args.get("ios", 1))

    processes = load_processes_from_json(f"./job_jsons/processfile_{file_num}.json", limit)

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
        "SRTFScheduler": SRTFScheduler
    }
    
    SchedulerClass = scheduler_map.get(scheduler_class_name, RRScheduler)
    
    print(f"Running simulation with {SchedulerClass.__name__}")
    print(f"Processes loaded: {len(processes)}")
    print(f"CPUs: {cpus}, I/O devices: {ios}")
    
    scheduler = SchedulerClass(num_cpus=cpus, num_ios=ios, verbose=False)
    for p in processes:
        scheduler.add_process(p)

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
