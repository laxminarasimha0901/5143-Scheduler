
# Adaptive Scheduling Algorithm Implementation
# schedulers/adaptive.py

from pkg import Scheduler
from collections import deque
import json
import csv

class AdaptiveScheduler(Scheduler):
    """
    Adaptive Scheduling.
    - Dynamically adjusts scheduling strategy based on system state
    - Uses Round Robin for interactive processes
    - Uses SJF for batch processes
    - Adjusts quantum based on load
    """
    
    def __init__(self, num_cpus=1, num_ios=1, base_quantum=4, verbose=False):
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.base_quantum = base_quantum
        self.verbose = verbose
        
        # Queues
        self.not_arrived = []
        self.ready_queue = []
        self.wait_queue = deque()
        self.cpu_queue = [None] * num_cpus
        self.io_queue = [None] * num_ios
        self.finished = []
        
        # Track quantum for each CPU
        self.quantum_remaining = {}
        
        # Adaptive parameters
        self.current_quantum = base_quantum
        self.load_history = []
        
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
            if self.verbose:
                print(f"[Clock {self.clock}] Process {process.pid} arrived")
    
    def _adapt_quantum(self):
        """Adjust quantum based on system load"""
        load = len(self.ready_queue) + len([p for p in self.cpu_queue if p is not None])
        self.load_history.append(load)
        
        # Keep last 10 measurements
        if len(self.load_history) > 10:
            self.load_history.pop(0)
        
        avg_load = sum(self.load_history) / len(self.load_history)
        
        # Adjust quantum: lower quantum for high load, higher for low load
        if avg_load > 5:
            self.current_quantum = max(2, self.base_quantum - 2)
        elif avg_load < 2:
            self.current_quantum = self.base_quantum + 2
        else:
            self.current_quantum = self.base_quantum
    
    def _classify_process(self, process):
        """Classify process as CPU-bound or I/O-bound"""
        if not hasattr(process, 'burst_history'):
            return 'unknown'
        
        cpu_time = sum(t for t, type in process.burst_history if type == 'cpu')
        io_time = sum(t for t, type in process.burst_history if type == 'io')
        
        if cpu_time > io_time * 2:
            return 'cpu_bound'
        elif io_time > cpu_time * 2:
            return 'io_bound'
        return 'balanced'
    
    def _sort_ready_queue(self):
        """Sort ready queue adaptively based on process characteristics"""
        # Prioritize I/O-bound processes (better for responsiveness)
        # Then use burst time for CPU-bound processes
        def priority_key(p):
            classification = self._classify_process(p)
            burst_time = p.get_current_burst_time() if hasattr(p, 'get_current_burst_time') else 0
            
            if classification == 'io_bound':
                return (0, burst_time)  # Highest priority
            elif classification == 'balanced':
                return (1, burst_time)
            else:  # cpu_bound
                return (2, burst_time)  # Lowest priority
        
        self.ready_queue.sort(key=priority_key)
    
    def step(self):
        """Execute one time step of the simulation"""
        self._check_arrivals()
        self._adapt_quantum()
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
                # Decrement quantum
                if cpu_index in self.quantum_remaining:
                    self.quantum_remaining[cpu_index] -= 1
                
                # Track burst history
                if not hasattr(current_process, 'burst_history'):
                    current_process.burst_history = []
                
                burst_completed = current_process.advance_burst()
                quantum_expired = cpu_index in self.quantum_remaining and self.quantum_remaining[cpu_index] <= 0
                
                if burst_completed:
                    self.cpu_queue[cpu_index] = None
                    if cpu_index in self.quantum_remaining:
                        del self.quantum_remaining[cpu_index]
                    
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
                
                elif quantum_expired:
                    # Quantum expired - preempt
                    self.cpu_queue[cpu_index] = None
                    del self.quantum_remaining[cpu_index]
                    current_process.state = "ready"
                    self.ready_queue.append(current_process)
                    if self.verbose:
                        print(f"[Clock {self.clock}] Process {current_process.pid} preempted")
    
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
    
    def _dispatch_to_cpus(self):
        """Dispatch ready processes to available CPUs adaptively"""
        self._sort_ready_queue()
    
        while len([p for p in self.cpu_queue if p is not None]) < self.num_cpus and self.ready_queue:
            process = self.ready_queue.pop(0)
            if process.state == "ready":
                for cpu_index in range(self.num_cpus):
                    if self.cpu_queue[cpu_index] is None:
                        process.state = "running"
                        # Track first time process gets CPU (for wait time calculation)
                        if not hasattr(process, 'first_dispatch_time'):
                            process.first_dispatch_time = self.clock
                            print(f"DEBUG DISPATCH: Process {process.pid} first dispatch at clock={self.clock}, arrival={process.arrival_time}, wait={self.clock - process.arrival_time}")
                        self.cpu_queue[cpu_index] = process
                        self.quantum_remaining[cpu_index] = self.current_quantum
                        if self.verbose:
                            print(f"[Clock {self.clock}] Process {process.pid} dispatched to CPU {cpu_index} (quantum: {self.current_quantum})")
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
            "finished": [process.pid for process in self.finished],
            "current_quantum": self.current_quantum
        }
    
    def print_stats(self):
        """Print completion statistics"""
        if not self.finished:
            print("No processes have completed.")
            return
    
        print("\n" + "="*80)
        print("DEBUG: Checking all finished processes")
        print("="*80)
    
        for process in self.finished:
            print(f"Process {process.pid}:")
            print(f"  arrival_time = {process.arrival_time}")
            print(f"  end_time = {process.end_time}")
            print(f"  hasattr first_dispatch_time? {hasattr(process, 'first_dispatch_time')}")
            if hasattr(process, 'first_dispatch_time'):
                print(f"  first_dispatch_time = {process.first_dispatch_time}")
                print(f"  Calculated wait time = {process.first_dispatch_time - process.arrival_time}")
            print(f"  process.wait_time (accumulated) = {process.wait_time}")
            print()
    
        print("\nAdaptive Scheduler Statistics:")
        print(f"Base Quantum: {self.base_quantum}, Final Quantum: {self.current_quantum}")
        print("-" * 70)
    
        total_turnaround = 0
        total_waiting = 0
    
        print(f"{'Process':<8} {'Arrival':<8} {'1st CPU':<10} {'Completion':<12} {'Turnaround':<12} {'Waiting':<10}")
        print("-" * 70)
    
        for process in self.finished:
            # Calculate actual wait time: first dispatch time - arrival time
            if hasattr(process, 'first_dispatch_time'):
                actual_wait_time = process.first_dispatch_time - process.arrival_time
            else:
                # Fallback to accumulated wait_time if first_dispatch_time wasn't tracked
                actual_wait_time = process.wait_time
        
            turnaround_time = process.end_time - process.arrival_time
            first_cpu = getattr(process, 'first_dispatch_time', '?')
        
            total_turnaround += turnaround_time
            total_waiting += actual_wait_time
        
            print(f"{process.pid:<8} {process.arrival_time:<8} {first_cpu:<10} {process.end_time:<12} "
              f"{turnaround_time:<12} {actual_wait_time:<10}")
    
        print("-" * 70)
        print(f"Average Turnaround Time: {total_turnaround/len(self.finished):.2f}")
        print(f"Average Waiting Time:    {total_waiting/len(self.finished):.2f}")
        print(f"Total Simulation Time:   {self.clock}")
    
    def export_json(self, filename):
        """Export simulation timeline to JSON file"""
        timeline_data = {
            "algorithm": "Adaptive",
            "base_quantum": self.base_quantum,
            "total_time": self.clock,
            "processes": []
        }
        
        for process in self.finished:
            # Calculate actual wait time
            if hasattr(process, 'first_dispatch_time'):
                actual_wait_time = process.first_dispatch_time - process.arrival_time
            else:
                actual_wait_time = process.wait_time
                
            process_data = {
                "pid": process.pid,
                "arrival_time": process.arrival_time,
                "first_dispatch_time": getattr(process, 'first_dispatch_time', None),
                "completion_time": process.end_time,
                "turnaround_time": process.end_time - process.arrival_time,
                "waiting_time": actual_wait_time
            }
            timeline_data["processes"].append(process_data)
        
        with open(filename, 'w') as f:
            json.dump(timeline_data, f, indent=2)
    
    def export_csv(self, filename):
        """Export simulation results to CSV file"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['pid', 'arrival_time', 'first_dispatch_time', 'completion_time', 'turnaround_time', 'waiting_time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for process in self.finished:
                # Calculate actual wait time
                if hasattr(process, 'first_dispatch_time'):
                    actual_wait_time = process.first_dispatch_time - process.arrival_time
                else:
                    actual_wait_time = process.wait_time
                    
                writer.writerow({
                    'pid': process.pid,
                    'arrival_time': process.arrival_time,
                    'first_dispatch_time': getattr(process, 'first_dispatch_time', None),
                    'completion_time': process.end_time,
                    'turnaround_time': process.end_time - process.arrival_time,
                    'waiting_time': actual_wait_time
                })
