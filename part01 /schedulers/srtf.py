# Shortest Remaining Time First (SRTF) Scheduling Algorithm Implementation
# schedulers/srtf.py
from pkg import Scheduler
from collections import deque
import json
import csv

class SRTFScheduler(Scheduler):
    """
    Shortest Remaining Time First (SRTF) Scheduling.
    - Preemptive version of SJF.
    - At each tick, chooses the ready job with the smallest remaining CPU burst.
    """

    def __init__(self, num_cpus=1, num_ios=1, verbose=False):
        # Initialize scheduler parameters
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.verbose = verbose
        
        # Queues
        # Ready processes
        self.ready_queue = deque()        
        # Processes waiting for I/O
        self.wait_queue = deque()   
        # Processes running on each CPU      
        self.cpu_queue = [None] * num_cpus  
        # Processes on I/O devices
        self.io_queue = [None] * num_ios    
        # Completed processes
        self.finished = []                
        
        #self.clock = 0
    
    def add_process(self, process):
        """Add a process to the ready queue"""
        # Initialize process state
        process.state = "ready"
        # Add to ready queue
        self.ready_queue.append(process)
    
    def step(self):
        """Execute one time step of the simulation"""
        # Increment clock
        self.clock += 1
        
        # Process currently running jobs on CPUs
        self._process_cpus()

        # Process currently running jobs on I/O devices
        self._process_io_devices()

        # Dispatch ready processes to available CPUs using SRTF selection
        self._dispatch_to_cpus()

        # Dispatch waiting processes to available I/O devices
        self._dispatch_to_io_devices()
    
    def _get_shortest_remaining_process(self):
        """Return the ready process with smallest remaining CPU burst"""
        # Initialize shortest process variables
        shortest_process = None
        shortest_remaining_time = float('inf')
        
        # Check each ready process
        for process in self.ready_queue:
            # Get current CPU burst
            burst = process.current_burst()
            # Check if burst exists and is a CPU burst
            if burst and "cpu" in burst:
                # Get remaining time
                remaining = burst["cpu"]
                # Compare to find shortest
                if remaining < shortest_remaining_time:
                    # Update shortest found
                    shortest_remaining_time = remaining
                    shortest_process = process
        
        # Returns the process with shortest remaining time
        return shortest_process
    
    def _preemption_check(self, cpu_index):
        """Check if a ready process has shorter remaining burst than CPU process"""
        # Get current process on the CPU
        current = self.cpu_queue[cpu_index]
        # If no current process, nothing to preempt
        if current is None:
            return
        
        # Find the ready process with shortest remaining time
        shortest_ready = self._get_shortest_remaining_process()
        # If no ready process, nothing to preempt
        if shortest_ready is None:
            return
        
        # Get current burst of the CPU process
        current_burst = current.current_burst()
        # If current burst is not CPU, cannot preempt
        if current_burst is None or "cpu" not in current_burst:
            return
        
        # Compare remaining times to decide on preemption
        if shortest_ready.current_burst()["cpu"] < current_burst["cpu"]:
            # Preempt!
            if self.verbose:
                # Debug output
                print(f"[Time {self.clock}] Preempting P{current.pid} with P{shortest_ready.pid}")

            # Move current CPU process back to ready queue
            current.state = "ready"
            self.ready_queue.append(current)

            # Put shortest ready process on this CPU
            self.ready_queue.remove(shortest_ready)
            shortest_ready.state = "running"
            self.cpu_queue[cpu_index] = shortest_ready

    def _process_cpus(self):
        """Process jobs currently running on CPUs and handle burst completion."""
        # Find an available CPU
        for cpu_index in range(self.num_cpus):
            # Get the current process on this CPU
            current_process = self.cpu_queue[cpu_index]
            if current_process is not None:
                # Advance the current CPU burst
                burst_done = current_process.advance_burst()

                # If the burst is complete
                if burst_done:
                    # Burst completed
                    self.cpu_queue[cpu_index] = None

                    # If process is complete
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
                else:
                    # Check for preemption
                    self._preemption_check(cpu_index)

    def _process_io_devices(self):
        """Process currently running jobs on all I/O devices"""
        # Find an available I/O device
        for io_index in range(self.num_ios):
            # Get the current process on this I/O device
            current_process = self.io_queue[io_index]
            # If there is a process on this I/O device
            if current_process is not None:
                # Advance the current I/O burst
                burst_done = current_process.advance_burst()
                # If the burst is complete
                if burst_done:
                    # I/O burst completed
                    self.io_queue[io_index] = None

                    # If process is complete
                    if current_process.is_complete():
                        # Process is completely finished
                        current_process.state = "finished"
                        current_process.end_time = self.clock
                        current_process.turnaround_time = self.clock - current_process.arrival_time
                        self.finished.append(current_process)
                    else:
                        # Next burst is CPU, move to ready queue
                        current_process.state = "ready"
                        self.ready_queue.append(current_process)
    
    def _dispatch_to_cpus(self):
        """Assign shortest remaining time process to any free CPU."""
        # Find an available CPU
        for cpu_index in range(self.num_cpus):
            # If CPU is free
            if self.cpu_queue[cpu_index] is None:
                # Get the ready process with shortest remaining time
                process = self._get_shortest_remaining_process()
                # If found, assign to CPU
                if process:
                    # Remove from ready queue and assign to CPU
                    self.ready_queue.remove(process)
                    # Change state and assign to CPU
                    process.state = "running"
                    self.cpu_queue[cpu_index] = process

    def _dispatch_to_io_devices(self):
        """Assign waiting processes to free I/O devices."""
        # Find an available I/O device
        for io_index in range(self.num_ios):
            # Assign next waiting process to I/O device
            if self.io_queue[io_index] is None and self.wait_queue:
                # Pop next waiting process
                process = self.wait_queue.popleft()
                process.state = "io"
                self.io_queue[io_index] = process

    def has_jobs(self):
        """Check if there are any jobs still being processed"""
        # Returns True if there are jobs in any queue or running on CPUs/IOs
        return (
            any(self.cpu_queue) or any(self.io_queue)
            or len(self.ready_queue) > 0 or len(self.wait_queue) > 0
        )
    
    def snapshot(self):
        """Return a snapshot of the current scheduler state"""
        # Returns a dictionary with the current state of the scheduler
        return {
            "clock": self.clock,
            "ready": [p.pid for p in self.ready_queue],
            "wait": [p.pid for p in self.wait_queue],
            "cpu": [p.pid if p else None for p in self.cpu_queue],
            "io": [p.pid if p else None for p in self.io_queue],
            "finished": [p.pid for p in self.finished],
        }

    def print_stats(self):
        """Print completion statistics"""
        # If no processes have finished, print a message and return
        if not self.finished:
            print("No processes have completed.")
            return
        
        # Print header
        print("\nSRTF Scheduler Statistics:")
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
        print(f"Total Context Switches: 0")
        print(f"Total Simulation Time: {self.clock}")

    def export_json(self, filename):
        """Export simulation results to JSON file"""
        # Prepare timeline data
        timeline_data = {
            "algorithm": "SRTF",
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
            json.dump(timeline_data, f, indent=4)

    def export_csv(self, filename):
        """Export simulation results to CSV file"""
        # Export simulation results to CSV file
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['pid', 'arrival_time', 'completion_time', 'turnaround_time', 'waiting_time', 'priority']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()

            # Write each finished process's data
            for process in self.finished:
                writer.writerow({
                    'pid': process.pid,
                    'arrival_time': process.arrival_time,
                    'completion_time': process.end_time,
                    'turnaround_time': process.turnaround_time,
                    'waiting_time': process.wait_time
                })