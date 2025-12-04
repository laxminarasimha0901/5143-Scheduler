# Shortest Job First (SJF) Scheduling Algorithm Implementation
# schedulers/sjf.py

from pkg import Scheduler
from collections import deque
import json
import csv

class SJFScheduler(Scheduler):
    """
    Shortest Job First (SJF) Scheduling.
    - Non-preemptive: selects the process with the shortest burst time
    - Processes are selected from ready queue based on shortest CPU burst
    """
    
    def __init__(self, num_cpus=1, num_ios=1, verbose=False):
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.verbose = verbose
        
        # Queues
        self.not_arrived = []
        self.ready_queue = []  # Use list instead of deque for sorting
        self.wait_queue = deque()
        self.cpu_queue = [None] * num_cpus
        self.io_queue = [None] * num_ios
        self.finished = []
        
        self.clock = 0
    
    def add_process(self, process):
        """Add a process to the not-arrived queue"""
        self.not_arrived.append(process)
        self.not_arrived.sort(key=lambda p: p.arrival_time)
    
    def _check_arrivals(self):
        """Check for processes that have arrived and move them to ready queue"""
        while self.not_arrived and self.not_arrived[0].arrival_time <= self.clock:
            process = self.not_arrived.pop(0)
            process.state = "ready"
            self.ready_queue.append(process)
            # Sort ready queue by burst time (SJF policy)
            self._sort_ready_queue()
            if self.verbose:
                print(f"[Clock {self.clock}] Process {process.pid} arrived")
    
    def _sort_ready_queue(self):
        """Sort ready queue by shortest burst time first"""
        def get_burst_time(p):
            burst = p.current_burst()
            if burst and isinstance(burst, dict) and 'cpu' in burst:
                return burst['cpu']
            return float('inf')
        
        self.ready_queue.sort(key=get_burst_time)
    
    def step(self):
        """Execute one time step of the simulation"""
        self._check_arrivals()
        self._process_cpus()
        self._process_io_devices()
        self._dispatch_to_cpus()
        self._dispatch_to_io_devices()
        self.clock += 1
        for p in self.ready_queue:
            p.wait_time += 1  # Increment wait time for everyone waiting
    
    def _process_cpus(self):
        """Process currently running jobs on all CPUs"""
        for cpu_index in range(self.num_cpus):
            current_process = self.cpu_queue[cpu_index]
            if current_process is not None:
                burst_completed = current_process.advance_burst()
                
                if burst_completed:
                    self.cpu_queue[cpu_index] = None
                    
                    if current_process.is_complete():
                        current_process.state = "finished"
                        current_process.end_time = self.clock
                        current_process.turnaround_time = self.clock - current_process.arrival_time
                        self.finished.append(current_process)
                        if self.verbose:
                            print(f"[Clock {self.clock}] Process {current_process.pid} finished")
                    else:
                        current_process.state = "waiting"
                        self.wait_queue.append(current_process)
    
    def _process_io_devices(self):
        """Process currently running jobs on all I/O devices"""
        for io_index in range(self.num_ios):
            current_process = self.io_queue[io_index]
            if current_process is not None:
                burst_completed = current_process.advance_burst()
                
                if burst_completed:
                    self.io_queue[io_index] = None
                    
                    if current_process.is_complete():
                        current_process.state = "finished"
                        current_process.end_time = self.clock
                        current_process.turnaround_time = self.clock - current_process.arrival_time
                        self.finished.append(current_process)
                        if self.verbose:
                            print(f"[Clock {self.clock}] Process {current_process.pid} finished")
                    else:
                        current_process.state = "ready"
                        self.ready_queue.append(current_process)
                        self._sort_ready_queue()  # Re-sort when process returns from I/O
    
    def _dispatch_to_cpus(self):
        """Dispatch ready processes to available CPUs (shortest job first)"""
        while len([p for p in self.cpu_queue if p is not None]) < self.num_cpus and self.ready_queue:
            # Already sorted by burst time, so take first process
            process = self.ready_queue.pop(0)
            if process.state == "ready":
                for cpu_index in range(self.num_cpus):
                    if self.cpu_queue[cpu_index] is None:
                        process.state = "running"
                        if not hasattr(process, 'first_run_time'):
                            process.first_run_time = self.clock
                        self.cpu_queue[cpu_index] = process
                        if self.verbose:
                            burst = process.current_burst()
                            burst_time = burst['cpu'] if burst and 'cpu' in burst else 0
                            print(f"[Clock {self.clock}] Process {process.pid} dispatched to CPU {cpu_index} (burst: {burst_time})")
                        break
    
    def _dispatch_to_io_devices(self):
        """Dispatch waiting processes to available I/O devices"""
        while len([p for p in self.io_queue if p is not None]) < self.num_ios and self.wait_queue:
            process = self.wait_queue.popleft()
            if process.state == "waiting":
                for io_index in range(self.num_ios):
                    if self.io_queue[io_index] is None:
                        process.state = "io_waiting"
                        self.io_queue[io_index] = process
                        if self.verbose:
                            print(f"[Clock {self.clock}] Process {process.pid} dispatched to I/O {io_index}")
                        break
    
    def has_jobs(self):
        """Check if there are any jobs still being processed"""
        return (len(self.not_arrived) > 0 or
                len(self.ready_queue) > 0 or 
                len(self.wait_queue) > 0 or 
                any(p is not None for p in self.cpu_queue) or 
                any(p is not None for p in self.io_queue))
    
    def snapshot(self):
        """Return current state of all queues for visualization"""
        return {
            "clock": self.clock,
            "not_arrived": [process.pid for process in self.not_arrived],
            "ready": [process.pid for process in self.ready_queue],
            "wait": [process.pid for process in self.wait_queue],
            "cpu": [process.pid if process is not None else None for process in self.cpu_queue],
            "io": [process.pid if process is not None else None for process in self.io_queue],
            "finished": [process.pid for process in self.finished]
        }
    
    def print_stats(self):
        """Print completion statistics"""
        if not self.finished:
            print("No processes have completed.")
            return
        
        print("\nSJF Scheduler Statistics:")
        print("-" * 60)
        
        total_turnaround = sum(p.turnaround_time for p in self.finished)
        total_waiting = sum(p.wait_time for p in self.finished)
        
        print(f"{'Process':<8} {'Arrival':<8} {'Completion':<10} {'Turnaround':<10} {'Waiting':<10}")
        print("-" * 60)
        
        for process in self.finished:
            print(f"{process.pid:<8} {process.arrival_time:<8} {process.end_time:<10} "
                  f"{process.turnaround_time:<10} {process.wait_time:<10}")
        
        print("-" * 60)
        print(f"Average Turnaround Time: {total_turnaround/len(self.finished):.2f}")
        print(f"Average Waiting Time:   {total_waiting/len(self.finished):.2f}")
        print(f"Total Simulation Time: {self.clock}")
    
    def export_json(self, filename):
        """Export simulation timeline to JSON file"""
        timeline_data = {
            "algorithm": "SJF",
            "total_time": self.clock,
            "processes": []
        }
        
        for process in self.finished:
            process_data = {
                "pid": process.pid,
                "arrival_time": process.arrival_time,
                "completion_time": process.end_time,
                "turnaround_time": process.turnaround_time,
                "waiting_time": process.wait_time
            }
            timeline_data["processes"].append(process_data)
        
        with open(filename, 'w') as f:
            json.dump(timeline_data, f, indent=2)
    
    def export_csv(self, filename):
        """Export simulation results to CSV file"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['pid', 'arrival_time', 'completion_time', 'turnaround_time', 'waiting_time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for process in self.finished:
                writer.writerow({
                    'pid': process.pid,
                    'arrival_time': process.arrival_time,
                    'completion_time': process.end_time,
                    'turnaround_time': process.turnaround_time,
                    'waiting_time': process.wait_time
                })
                