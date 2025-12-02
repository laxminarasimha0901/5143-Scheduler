# Shortest Job First (SJF) Scheduling Algorithm Implementation
# schedulers/sjf.py
from pkg import Scheduler
from collections import deque
import json
import csv

class SJFScheduler(Scheduler):
    def __init__(self, num_cpus=1, num_ios=1, verbose=False):
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.verbose = verbose
        
        # Queues
        self.ready_queue = deque()      # Ready processes
        self.wait_queue = deque()      # Processes waiting for I/O
        self.cpu_queue = [None] * num_cpus  # Currently running processes on each CPU
        self.io_queue = [None] * num_ios   # Currently running processes on each I/O device
        self.finished = []              # Completed processes
        
        #self.clock = 0
    
    def add_process(self, process):
        """Add a process to the ready queue"""
        self.ready_queue.append(process)
    
    def step(self):
        """Execute one time step of the simulation"""
        self.clock += 1
        
        # Process currently running jobs on CPUs
        self._process_cpus()
        
        # Process currently running jobs on I/O devices
        self._process_io_devices()
        
        # Dispatch ready processes to available CPUs using SJF selection
        self._dispatch_to_cpus()
        
        # Dispatch waiting processes to available I/O devices
        self._dispatch_to_io_devices()
    
    def _get_shortest_ready_process(self):
        """Select the ready process with the shortest remaining burst time"""
        if not self.ready_queue:
            return None
        
        # Find process with shortest remaining CPU burst time
        shortest_process = None
        shortest_burst_time = float('inf')
        
        for process in self.ready_queue:
            current_burst = process.current_burst()
            if current_burst and "cpu" in current_burst:
                burst_time = current_burst["cpu"]
                if burst_time < shortest_burst_time:
                    shortest_burst_time = burst_time
                    shortest_process = process
        
        return shortest_process
    
    def _process_cpus(self):
        """Process currently running jobs on all CPUs"""
        for cpu_index in range(self.num_cpus):
            current_process = self.cpu_queue[cpu_index]
            if current_process is not None:
                # Advance the current burst
                burst_completed = current_process.advance_burst()
                
                if burst_completed:
                    # Burst completed
                    self.cpu_queue[cpu_index] = None
                    
                    if current_process.is_complete():
                        # Process is completely finished
                        current_process.state = "finished"
                        current_process.end_time = self.clock
                        current_process.turnaround_time = self.clock - current_process.arrival_time
                        self.finished.append(current_process)
                    else:
                        # Next burst is I/O, move to wait queue
                        current_process.state = "waiting"
                        self.wait_queue.append(current_process)
    
    def _process_io_devices(self):
        """Process currently running jobs on all I/O devices"""
        for io_index in range(self.num_ios):
            current_process = self.io_queue[io_index]
            if current_process is not None:
                # Advance the current I/O burst
                burst_completed = current_process.advance_burst()
                
                if burst_completed:
                    # I/O burst completed
                    self.io_queue[io_index] = None
                    
                    if current_process.is_complete():
                        # Process is completely finished
                        current_process.state = "finished"
                        current_process.end_time = self.clock
                        current_process.turnaround_time = self.clock - current_process.arrival_time
                        self.finished.append(current_process)
                    else:
                        # Next burst is CPU, move back to ready queue
                        current_process.state = "ready"
                        self.ready_queue.append(current_process)
    
    def _dispatch_to_cpus(self):
        """Dispatch ready processes to available CPUs using SJF selection"""
        while len([p for p in self.cpu_queue if p is not None]) < self.num_cpus and self.ready_queue:
            # Select process with shortest remaining burst time
            shortest_process = self._get_shortest_ready_process()
            
            if shortest_process is None:
                break
            
            # Remove the selected process from ready queue
            self.ready_queue.remove(shortest_process)
            
            # Find an available CPU and dispatch the process
            for cpu_index in range(self.num_cpus):
                if self.cpu_queue[cpu_index] is None:
                    shortest_process.state = "running"
                    self.cpu_queue[cpu_index] = shortest_process
                    break
    
    def _dispatch_to_io_devices(self):
        """Dispatch waiting processes to available I/O devices"""
        # Fill available I/O devices with waiting processes
        while len([p for p in self.io_queue if p is not None]) < self.num_ios and self.wait_queue:
            # Get next waiting process
            process = self.wait_queue.popleft()
            if process.state == "waiting":
                # Find an available I/O device
                for io_index in range(self.num_ios):
                    # 
                    if self.io_queue[io_index] is None:
                        process.state = "io_waiting"
                        self.io_queue[io_index] = process
                        break
    
    def has_jobs(self):
        """Check if there are any jobs still being processed"""
        # Returns True if there are jobs in any queue or running on CPUs/IOs
        return (len(self.ready_queue) > 0 or 
                len(self.wait_queue) > 0 or 
                any(p is not None for p in self.cpu_queue) or 
                any(p is not None for p in self.io_queue))
    
    def snapshot(self):
        """Return current state of all queues for visualization"""
        # Returns a dictionary with the current state of the scheduler
        return {
            "clock": self.clock,
            "ready": [process.pid for process in self.ready_queue],
            "wait": [process.pid for process in self.wait_queue],
            "cpu": [process.pid if process is not None else None for process in self.cpu_queue],
            "io": [process.pid if process is not None else None for process in self.io_queue],
            "finished": [process.pid for process in self.finished]
        }
    
    def print_stats(self):
        """Print completion statistics"""
        # If no processes have finished, print a message and return
        if not self.finished:
            print("No processes have completed.")
            return
        
        # Print header
        print("\nSJF Scheduler Statistics:")
        print("-" * 60)
        
        # Calculate totals for averages
        total_turnaround = sum(p.turnaround_time for p in self.finished)
        total_waiting = sum(p.wait_time for p in self.finished)
        
        # Print table header
        print(f"{'Process':<8} {'Arrival':<8} {'Completion':<10} {'Turnaround':<10} {'Waiting':<10}")
        print("-" * 60)
        
        # Print each process's stats
        for process in self.finished:
            print(f"{process.pid:<8} {process.arrival_time:<8} {process.end_time:<10} "
                  f"{process.turnaround_time:<10} {process.wait_time:<10}")
        
        # Print averages
        print("-" * 60)
        print(f"Average Turnaround Time: {total_turnaround/len(self.finished):.2f}")
        print(f"Average Waiting Time:   {total_waiting/len(self.finished):.2f}")
        print(f"Total Simulation Time: {self.clock}")
    
    def export_json(self, filename):
        """Export simulation timeline to JSON file"""
        # Prepare timeline data
        timeline_data = {
            "algorithm": "SJF",
            "total_time": self.clock,
            "processes": []
        }
        
        # Add each finished process's data
        for process in self.finished:
            process_data = {
                "pid": process.pid,
                "arrival_time": process.arrival_time,
                "completion_time": process.end_time,
                "turnaround_time": process.turnaround_time,
                "waiting_time": process.wait_time
            }
            timeline_data["processes"].append(process_data)
        
        # Write to JSON file
        with open(filename, 'w') as f:
            json.dump(timeline_data, f, indent=2)
    
    def export_csv(self, filename):
        """Export simulation results to CSV file"""
        # Export simulation results to CSV file
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['pid', 'arrival_time', 'completion_time', 'turnaround_time', 'waiting_time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()

            # Write each finished process's data to CSV
            for process in self.finished:
                writer.writerow({
                    'pid': process.pid,
                    'arrival_time': process.arrival_time,
                    'completion_time': process.end_time,
                    'turnaround_time': process.turnaround_time,
                    'waiting_time': process.wait_time
                })